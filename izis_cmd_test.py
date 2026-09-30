import socket
import time
import sys
import threading

# Configuration
HOST = '127.0.0.1'  # Use the board's IP if connecting via IZISBridge/socat over Wi-Fi
PORT = 5000

# Threading sync primitives
target_event = threading.Event()
target_prefix = None
is_waiting = False
menu_active = False

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
    ("Matrix Write Demo (SAR)", "~SAR" + "1"*361 + "#", True, 1.0, "ALS"),
    ("Draw OK Graphic (RLO)", "~RLO#", True, 1.0, "DSC"), 
    ("Draw V Graphic (RLT)", "~RLT#", True, 1.0, "DSC"),
    ("Draw X Graphic (RLW)", "~RLW#", True, 1.0, "DSC"),
    ("Fill Dim White (FLL)", "~FLL#", False, 1.0, None),    # No response expected
    ("Audio Beep (AWO)", "~AWO#", False, 1.0, None),        # No response expected
    ("Calibrate Sensors (ADJ)", "~ADJ#", True, 90.0, "AEN"),# VERY LONG TIMEOUT
]

def print_async(msg):
    """Safely prints async messages without completely breaking the input prompt."""
    if menu_active:
        sys.stdout.write(f"\r\033[K{msg}\nSelect an option: ")
        sys.stdout.flush()
    else:
        print(msg)

def listener_thread(sock):
    """Background thread to continuously read, buffer, and parse packets."""
    global target_prefix, is_waiting
    buffer = ""
    
    try:
        while True:
            data = sock.recv(1024).decode('ascii', errors='ignore')
            if not data:
                print_async("\n[ERROR] Connection closed by the remote host.")
                break
                
            buffer += data
            
            # Packet Extraction Loop
            while True:
                start_idx = buffer.find('~')
                if start_idx == -1:
                    buffer = "" # No start character, flush garbage
                    break
                    
                end_idx = buffer.find('#', start_idx)
                if end_idx == -1:
                    # Partial Packet Check / Packet Loss Protection
                    # If we find ANOTHER '~' before a '#', the first packet was corrupted/truncated.
                    next_start = buffer.find('~', start_idx + 1)
                    if next_start != -1:
                        print_async("[WARNING] Packet loss detected. Dropping corrupted fragment.")
                        buffer = buffer[next_start:] # Discard everything before the new '~'
                        continue
                    break # Wait for more data to complete the packet
                    
                # Complete valid packet found!
                packet = buffer[start_idx:end_idx+1]
                buffer = buffer[end_idx+1:] # Remove processed packet from buffer
                
                # Check if this packet is the one the main thread is waiting for
                if is_waiting and target_prefix and packet.startswith(f"~{target_prefix}"):
                    print_async(f"[RX - MATCH] {packet}")
                    is_waiting = False
                    target_event.set() # Unblock the main thread
                else:
                    # It's a background event (e.g. SDA report, BKY button press, or unexpected)
                    print_async(f"[RX - ASYNC EVENT] {packet}")
                    
    except Exception as e:
        print_async(f"\n[LISTENER ERROR] {e}")

def execute_command(sock, cmd_str, expect_resp, timeout_sec, target_resp):
    """Sends a command and coordinates with the listener thread to await the response."""
    global target_prefix, is_waiting, menu_active
    
    menu_active = False # Disable prompt redraws during active execution
    target_prefix = target_resp
    target_event.clear()
    is_waiting = expect_resp

    print(f"\n[TX - SEND] {cmd_str}")
    if cmd_str.startswith("~ADJ"):
        print(">> WARNING: ADJ Calibration takes > 30 seconds. Do NOT interrupt. Listening...")

    try:
        sock.sendall(cmd_str.encode('ascii'))
    except Exception as e:
        print(f"[ERROR] Failed to send: {e}")
        is_waiting = False
        return

    if expect_resp:
        # Block the main thread until the listener thread signals the event OR timeout expires
        success = target_event.wait(timeout_sec)
        if not success:
            print(f"[TIMEOUT] Failed to receive '{target_resp}' within {timeout_sec}s.")
        else:
            # Enforce the 240ms mandatory render delay for heavy commands
            heavy_cmds = ["~RGC#", "~RGF#", "~FLL#"]
            if any(cmd_str.startswith(hc.replace('#', '')) for hc in heavy_cmds) or cmd_str.startswith("~SA"):
                print(">> Delaying 240ms to prevent MCU crash...")
                time.sleep(0.24)
    else:
        # Wait a short duration to prove no response was sent
        time.sleep(timeout_sec)
        print(f"[OK] Execution complete. No response expected.")
        
    is_waiting = False

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

    # Start the background listener thread
    listener = threading.Thread(target=listener_thread, args=(sock,), daemon=True)
    listener.start()

    while True:
        menu_active = False
        print("\n" + "="*50)
        print("Command Menu")
        print("="*50)
        for i, cmd in enumerate(COMMANDS):
            print(f"[{i:02d}] {cmd[0]}")
        print("[M]  Manual Command Entry")
        print("[Q]  Quit")
        print("="*50)
        
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
                if not target_resp: target_resp = None
                
                timeout_input = input("Timeout in seconds (Default 2.0): ").strip()
                if timeout_input: timeout_sec = float(timeout_input)
            else:
                timeout_sec = 1.0
                
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