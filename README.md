# Izis Smart Go Board - Third-Party Development Kit & Reverse Engineering Specs

> **⚠️ DISCLAIMER**
> This repository is the result of personal reverse engineering research through the decompilation of genuine Izis applications and serial packet inspection. The author makes no guarantees regarding its accuracy, safety, or whether it aligns with Izis's original design intentions. Incorrect usage of these commands may potentially cause damage to the hardware. The author is in no way affiliated with Izis. Furthermore, there is no guarantee that Izis will not update their system in the future to block or restrict third-party development. Use this information entirely at your own risk.

## Overview
This repository contains essential tools, specifications, and bridging software to facilitate third-party application development for the **Izis (隱智) Smart Go Board**. Due to the proprietary nature of the board's embedded hardware, these tools bridge standard application runtimes (Android, PC, or Web) to the internal microcontroller unit (MCU) over UART `/dev/ttyS1` at 115200 baud (8-N-1).

### Note on PC-Based & Web-Based Applications
While this guide supports native Android app development (to run directly on the board's internal screen), it is equally suited for building PC-based or Web-based clients (such as KataGo bridges or custom GUIs) using the networked architectures below.

---

## Development Architectures

Depending on hardware availability and your workflow, this repository supports three primary development setups:

### Architecture A: Full Simulation (Emulator / PC App + Bridge + Web Simulator)
Ideal for local development without the physical board. Your app communicates with the HTML simulator via a Python routing bridge.

```text
[ PC Local Environment ]

+-----------------------+           +------------------------+           +-----------------------+
|   Android Emulator    |           |izis_simulator_bridge.py|           |    Web Browser        |
|   or Local PC App     |    TCP    |  (TCP <-> WS Bridge)   | WebSocket | (izis_simulator.html) |
|                       | <-------> |                        | <-------> |                       |
| Connects to:          | Port 5000 | TCP Listen: 5000       | Port 8080 | Connects to:          |
| 127.0.0.1:5000        |           | WS  Listen: 8080       |           | ws://127.0.0.1:8080   |
+-----------------------+           +------------------------+           +-----------------------+
```

### Architecture B: Hardware-in-the-Loop (Local App / PC over Wi-Fi)
Ideal for testing PC-based or Web-based applications directly against the physical hardware over your local network.

#### Method 1: The IzisBridge Android App (Recommended)
[IZISBridge](https://github.com/wjchen-vlsi/IZISBridge) includes a pre-built Android application in the releases section (`app-debug.apk`). Sideloading this app onto the board provides a UI-driven way to expose `/dev/ttyS1` over TCP without needing shell access.

1. Install `app-debug.apk` via USB flash drive or Wireless ADB.
2. Open the app on the Izis Smart Go Board.
3. Configure the **Serial Device Path** (defaults to `/dev/ttyS1`) and the **TCP Port** (defaults to `5000`).
4. (Optional) Check **APP > BRD** and **BRD > APP** to inspect command traffic in real time.
5. Tap **Start Forwarding**.
6. Connect your PC/Web app, test script, or local emulator to `<BOARD_IP>:5000`.

> **⚠️ Stock Launcher Visibility:** The board's default launcher hides third-party APKs unless their package name contains `cn.izis`. `IZISBridge` uses `cn.izis.izisbridge` to remain visible on the home screen. Any custom app intended to run on the board should adopt this naming convention or use a third-party launcher.

```text
[ PC Local Environment ]                                     [ Physical Izis Smart Go Board ]
                                       Wi-Fi (TCP)
+-----------------------+                                    +----------------------------------+
|   Android Emulator    |                                    | Android OS (IZISBridge)          |
|   or Local PC/Web App |          192.168.X.X:5000          |                                  |
|                       | <--------------------------------> | Listens on Port: 5000            |
| Connects to:          |                                    | Forwards to: /dev/ttyS1          |
| <BOARD_IP>:5000       |                                    |                                  |
+-----------------------+                                    +---------|------------------------+
                                                                       | UART (/dev/ttyS1, 115200)
                                                                       v
                                                             +----------------------------------+
                                                             | Go Board Hardware MCU            |
                                                             | (LED Matrix, Sensors, Buttons)   |
                                                             +----------------------------------+
```

#### Method 2: Command-Line Forwarding via socat (Alternative)
For developers with an active root ADB shell connection to the board, you can forward serial data directly via terminal:
```bash
socat tcp-l:5000,reuseaddr,fork file:/dev/ttyS1,b115200,raw,echo=0
```

### Architecture C: Direct Sideloading (On-Device Development)
Compile your app and sideload it directly onto the physical board to interact with `/dev/ttyS1` locally.

```text
[ PC Local Environment ]                             [ Physical Izis Smart Go Board ]

+-----------------------+                            +----------------------------------+
|   Android Studio      |        ADB over Wi-Fi      | Android OS (Rooted)              |
|   (Write Code &       |        or USB Drive        |                                  |
|    Build APK)         | -------------------------> | Install APK & Run App            |
|                       |                            | (Direct UART /dev/ttyS1 access)  |
+-----------------------+                            +----------------------------------+
```

---

## Repository Contents

### 1. [`izis_protocol_spec.md`](izis_protocol_spec.md)
The **Third-Party Developer Guide & Protocol Specification**. This is the primary reference manual. It thoroughly documents:
*   Android system setup (Wi-Fi ADB pairing, launcher workarounds, permissions, native app endpoints).
*   Coordinate system rules (1-based, right-to-left, top-to-bottom) and dynamic board sizing (`~BOD19#`, `~BOD13#`, `~BOD09#`).
*   Complete UART command reference with expected ACKs and timing requirements.
*   Empirical 5-color visual mapping under `~SAR`, matrix brightness scaling (`SAR` > `SAL` > `SAM` > `SAW`), and the 50-LED hardware current limit.

### 2. [`izis_simulator.html`](izis_simulator.html)
An **Izis Smart Go Board Simulator** written in HTML, CSS, and JavaScript.
*   **Purpose:** Replicates the physical board's 19x19 LED matrix, boundary boxes, dual turn indicators, clock buttons, and Hall sensor stone placements in a web browser.
*   **Features:** Accurate empirical color palette emulation, stone placement toggles (Left-click to place, Right-click to clear), interactive command console with Tab autocomplete, and delay violation warnings.

### 3. [`izis_simulator_bridge.py`](izis_simulator_bridge.py)
An asynchronous **TCP-to-WebSocket Bridge Script** written in Python.
*   **Purpose:** Bridges communication between a TCP client (Android app, test script, or AI engine) and the HTML simulator via WebSockets.
*   **Usage:** Run with `python izis_simulator_bridge.py`. Listens on TCP port `5000` (for apps/scripts) and WebSocket port `8080` (for the browser simulator). Handles frame delimitation (`~...#`) and stream fragmentation automatically.

### 4. [`IZISBridge`](https://github.com/wjchen-vlsi/IZISBridge)
A lightweight **Android Serial-to-TCP Forwarder App** (`cn.izis.izisbridge`).
*   Runs directly on the Izis board to expose `/dev/ttyS1` over a local TCP socket.
*   Features thread-safe single-client handling, automated local IPv4 resolution, and real-time rolling traffic monitors for inbound and outbound packets.

### 5. [`izis_cmd_test.py`](izis_cmd_test.py)
An **Interactive Command Testing CLI Tool** written in Python.
*   **Purpose:** Rapid interactive debugging tool to verify commands against the simulator or physical hardware before writing client code.
*   **Key Features:**
    *   Pre-loaded command presets (`STA`, `BODxx`, `HOT`, `SAR` palette test, `LEDxx`, `ADJ`).
    *   Background listener thread that parses asynchronous events (`~SDA...#`, button events `~BKY#` / `~WKY#`) without desynchronizing active command responses.
    *   Automatic timing compliance (240 ms extended delay for `~RGC#`, `~RGF#`, `~FLL#`; 80 ms baseline pacing for standard commands).
    *   Manual entry mode for custom protocol strings.

---

## Getting Started

1. **Review the Specification:** Read [`izis_protocol_spec.md`](izis_protocol_spec.md) to understand packet framing, ACK handling, and timing constraints.
2. **Install Dependencies:**
   ```bash
   pip install websockets
   ```
3. **Run the Simulation Environment:**
   * Terminal 1: Start the bridge server:
     ```bash
     python izis_simulator_bridge.py
     ```
   * Browser: Open `izis_simulator.html` and click **Connect**.
4. **Smoke-Test the Pipeline:**
   * Terminal 2: Run the interactive test CLI:
     ```bash
     python izis_cmd_test.py
     ```
   * Send test commands (e.g., `[19] SAR Palette Test` or `[16] Batch 4 Corners`) and observe real-time rendering in `izis_simulator.html`.
5. **Develop Your Application:** Direct your client socket logic to connect to `127.0.0.1:5000` during development, or point it to `<BOARD_IP>:5000` when running against the physical board via `IZISBridge`.
