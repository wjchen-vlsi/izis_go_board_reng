import socket
import time
import sys
import threading

# Configuration
HOST = '127.0.0.1'  # Board IP if connecting via IzisBridge over Wi-Fi
PORT = 5000

# Threading sync primitives
target_event = threading.Event()
target_prefix = None
is_waiting = False
menu_active = False

# Palette test payload: row 1 tests colors 1-9 separated by 0, remaining rows 0
PALETTE_TEST_PAYLOAD = "0102030405060708090" + ("0" * 342)

# Command Dictionary Format:
# (Label, Command String, Expects_Response, Timeout_Seconds, Target_Response_Prefix)
COMMANDS = [
    ("Query State (STA)", "~STA#", True, 2.0, "SDA"),
    ("Enable Auto-Report (CTS1)", "~CTS1#", True, 1.0, "UDS"),
    ("Disable Auto-Report (CTS0)", "~CTS0#", True, 1.0, "UDS"),
    ("Get Firmware Version (GVE)", "~GVE#", True, 1.0, "VER"),
    ("Get Separator Config (GSV)", "~GSV#", True, 1.0, "FJX"),
    ("Set Separator 0.32 (SEP32)", "~SEP32#", True, 1.0, "SSS"),
    ("Set Separator 0.15 (SEP15)", "~SEP15#", True, 1.0, "SSS"),
    ("Board 19x19 Mode (BOD19)", "~BOD19#", True, 1.0, "GBS"),
    ("Board 13x13 Mode (BOD13)", "~BOD13#", True, 1.0, "GBS"),
    ("Board 9x9 Mode (BOD09)", "~BOD09#", True, 1.0, "GBS"),
    ("Top Green LED ON (LED11)", "~LED11#", True, 1.0, "LOS"),
    ("Bottom White LED ON (LED21)", "~LED21#", True, 1.0, "LOS"),
    ("Both Indicators OFF (LED10)", "~LED10#", True, 1.0, "LOS"),
    ("Both Indicators OFF (LED20)", "~LED20#", True, 1.0, "LOS"),
    ("Single Light Tengen (SHP)", "~SHP181,r000g255b000,1#", True, 1.0, "HCS"),
    ("Sync Light Tengen (TLO)", "~TLO181,r000g255b000,1#", True, 1.0, "TLS"),
    ("Batch 4 Corners (HOT)", "~HOTA001r255g000b000B019r000g255b000C343r000g000b255D361r255g255b255N4#", True, 1.0, "HSM"),
    ("Clear All LEDs (RGC)", "~RGC#", True, 1.0, "ALC"),
    ("Clear Inner LEDs (RGF)", "~RGF#", True, 1.0, "SIC"),
    ("Matrix SAR Palette Test (Row 1)", f"~SAR{PALETTE_TEST_PAYLOAD}#", True, 1.0, "ALS"),
    ("Matrix SAL All Green (SAL)", "~SAL" + ("1" * 361) + "#", True, 1.0, "ALS"),
    ("Matrix SAM All Green (SAM)", "~SAM" + ("1" * 361) + "#", True, 1.0, "ALS"),
    ("Matrix SAW All Green (SAW)", "~SAW" + ("1" * 361) + "#", True, 1.0, "ALS"),
    ("Matrix SAR All Green (SAR)", "~SAR" + ("1" * 361) + "#", True, 1.0, "ALS"),
    ("Draw OK Graphic (RLO)", "~RLO#", True, 1.0, "DSC"), 
    ("Draw V Graphic (RLT)", "~RLT#", True, 1.0, "DSC"),
    ("Draw X Graphic (RLW)", "~RLW#", True, 1.0, "DSC"),
    ("Fill Dim White (FLL)", "~FLL#", False, 0.0, None),     # No response, 240ms mandatory delay
    ("Audio Beep (AWO)", "~AWO#", False, 0.0, None),         # No response, 80ms baseline delay
    ("Calibrate Sensors (ADJ)", "~ADJ#", True, 90.0, "AEN"), # Blocks MCU for > 30s
]

def print_async(msg):
    """Safely prints async messages without breaking the active menu prompt."""
    if menu_active:
        sys.stdout.write(f"\r\033[K{msg}\nSelect an option: ")
        sys.stdout.flush()
    else:
        print(msg)

def listener_thread(sock):
    """Background thread to continuously read, buffer, and unpack packets."""
    global target_prefix, is_waiting
    buffer = ""
    
    try:
        while True:
            data = sock.recv(1024).decode('ascii', errors='ignore')
            if not data:
                print_async("\n[ERROR] Connection closed by the remote host.")
                break
                
            buffer += data
            
            # Packet Extraction Loop: handles concatenated responses (~ALC#~BKY#)
            while True:
                start_idx = buffer.find('~')
                if start_idx == -1:
                    buffer = ""  # No start delimiter, flush noise
                    break
                    
                end_idx = buffer.find('#', start_idx)
                if end_idx == -1:
                    # Drop corrupted fragments if a second '~' arrived before '#'
                    next_start = buffer.find('~', start_idx + 1)
                    if next_start != -1:
                        print_async("[WARNING] Dropping corrupted fragment before new '~'.")
                        buffer = buffer[next_start:]
                        continue
                    break  # Incomplete packet, wait for next socket read
                    
                packet = buffer[start_idx:end_idx + 1]
                buffer = buffer[end_idx + 1:]  # Advance buffer past extracted packet
                
                # Check for expected ACK
                if is_waiting and target_prefix and packet.startswith(f"~{target_prefix}"):
                    print_async(f"[RX - MATCH] {packet}")
                    is_waiting = False
                    target_event.set()
                else:
                    print_async(f"[RX - ASYNC EVENT] {packet}")
                    
    except Exception as e:
        print_async(f"\n[LISTENER ERROR] {e}")

def execute_command(sock, cmd_str, expect_resp, timeout_sec, target_resp):
    """Sends a command, handles response synchronization, and applies pacing."""
    global target_prefix, is_waiting, menu_active
    
    menu_active = False
    target_prefix = target_resp
    target_event.clear()
    is_waiting = expect_resp

    print(f"\n[TX - SEND] {cmd_str}")
    if cmd_str.startswith("~ADJ"):
        print(">> WARNING: ADJ Calibration blocks MCU > 30 seconds. Do not interrupt.")

    try:
        sock.sendall(cmd_str.encode('ascii'))
    except Exception as e:
        print(f"[ERROR] Failed to send: {e}")
        is_waiting = False
        return

    if expect_resp:
        success = target_event.wait(timeout_sec)
        if not success:
            print(f"[TIMEOUT] Failed to receive '{target_resp}' within {timeout_sec}s.")
    else:
        print("[OK] Dispatched (fire-and-forget).")

    is_waiting = False

    # Hardware Pacing Delays:
    # Heavy render/clear commands require 240ms extended delay
    heavy_cmds = ("~RGC", "~RGF", "~FLL")
    if any(cmd_str.startswith(hc) for hc in heavy_cmds):
        print(">> Delaying 240ms (extended render delay)...")
        time.sleep(0.24)
    else:
        # Standard commands (including ~SA* matrix writes) use 80ms baseline delay
        time.sleep(0.08)

def interactive_loop():
    global menu_active
    print(f"Connecting to {HOST}:{PORT}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
        print("Connected successfully!\n")
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    listener = threading.Thread(target=listener_thread, args=(sock,), daemon=True)
    listener.start()

    while True:
        menu_active = False
        print("\n" + "=" * 55)
        print("Izis Protocol Command Menu")
        print("=" * 55)
        for i, cmd in enumerate(COMMANDS):
            print(f"[{i:02d}] {cmd[0]}")
        print("[M]  Manual Command Entry")
        print("[Q]  Quit")
        print("=" * 55)
        
        menu_active = True
        choice = input("Select an option: ").strip().upper()
        menu_active = False
        
        if choice == 'Q':
            print("Exiting...")
            break
        elif choice == 'M':
            cmd_str = input("Enter command string (e.g., ~RGC#): ").strip()
            if not cmd_str.startswith("~") or not cmd_str.endswith("#"):
                print("Invalid format. Commands must start with '~' and end with '#'.")
                continue
                
            expect_input = input("Does this command respond? (Y/n): ").strip().upper()
            expect_resp = expect_input != 'N'
            
            timeout_sec = 2.0
            target_resp = None
            
            if expect_resp:
                target_resp = input("Expected response prefix (e.g., SDA, leave blank for any): ").strip()
                if not target_resp:
                    target_resp = None
                
                timeout_input = input("Timeout in seconds (Default 2.0): ").strip()
                if timeout_input:
                    timeout_sec = float(timeout_input)
                
            execute_command(sock, cmd_str, expect_resp, timeout_sec, target_resp)
            
        elif choice.isdigit():
            idx = int(choice)
            if 0 <= idx < len(COMMANDS):
                label, cmd_str, expect, timeout, target = COMMANDS[idx]
                execute_command(sock, cmd_str, expect, timeout, target)
            else:
                print("Invalid selection.")

    sock.close()

if __name__ == "__main__":
    interactive_loop()