# Izis Smart Go Board - Third-Party Development Kit & Reverse Engineering Specs

> **⚠️ DISCLAIMER**
> This repository is the result of personal reverse engineering research. The author makes no guarantees regarding its accuracy, safety, or whether it aligns with Izis's original design intentions. Incorrect usage of these commands may potentially cause damage to the hardware. The author is in no way affiliated with Izis. Furthermore, there is no guarantee that Izis will not update their system in the future to block or restrict third-party development. Use this information entirely at your own risk.

## Overview
This repository contains essential tools and documentation to facilitate third-party Android application development for the **Izis (隱智) Smart Go Board**. Due to the proprietary nature of the hardware, these tools have been designed to bridge the gap between standard Android app development and the specialized UART hardware on the physical board.

### Note on PC-Based & Web-Based Applications
While this guide primarily targets native Android app development (to run directly on the board's internal screen), it is entirely possible to develop a PC-based or Web-based application using either of the networked development architectures below. 

---

## Development Architectures

Depending on whether you have the physical board on hand and your preferred workflow, this repository supports three primary development architectures:

### Architecture A: Full Simulation (Emulator + Bridge + Simulator)
Ideal for local development when you do not have access to the physical board or when you do not want to connect to the physical board all the time. Your app communicates with the HTML simulator via a Python routing bridge.

```text
[ PC Local Environment ]

+-----------------------+           +------------------------+           +-----------------------+
|   Android Emulator    |           |izis_simulator_bridge.py|           |    Web Browser        |
|   or Local PC App     |   TCP     |  (TCP <-> WS Bridge)   | WebSocket | (izis_simulator.html) |
|                       | <-------> |                        | <-------> |                       |
| Connects to:          | Port 5000 | TCP Listen: 5000       | Port 8080 | Connects to:          |
| 127.0.0.1:5000        |           | WS  Listen: 8080       |           | ws://127.0.0.1:8080   |
+-----------------------+           +------------------------+           +-----------------------+
```

### Architecture B: Hardware-in-the-Loop (Local App or socat Forwarding)
Ideal for testing PC-based or Web-based applications directly against the physical hardware over your local network.

#### Method 1: The Izis Bridge Android App (Recommended)
[IZISBridge](https://github.com/wjchen-vlsi/IZISBridge) includes a pre-built Android application in the release section (`app-debug.apk`).
Sideloading this app onto the board provides an UI-driven way to expose the serial port over TCP without requiring terminal commands.
Full source code is under [`IZISbridge`](IZISBridge). 

1. Install `app-debug.apk` via USB flash drive or ADB.
2. Open the app on the Izis Smart Go Board.
3. Configure the **Serial Device Path** (defaults to `/dev/ttyS1`) and the **TCP Port** (defaults to `5000`).
4. Tap **Start Forwarding**.
5. Connect your PC/Web based app or local emulator to `<BOARD_IP>:<PORT>`.

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
                                                                       | UART (/dev/ttyS1)
                                                                       v
                                                             +----------------------------------+
                                                             | Go Board Hardware MCU            |
                                                             | (LEDs, Sensors, Buttons)         |
                                                             +----------------------------------+
```
#### Method 2: Command-Line Forwarding via socat (Alternative)
For developers who prefer terminal tools and already have an active ADB shell connection to the rooted board, you can achieve the same result using socat.

Run the following command directly on the board via adb shell:
```text
socat tcp-l:5000,reuseaddr,fork file:/dev/ttyS1,b115200,raw,echo=0
```

### Architecture C: Direct Sideloading (Blind Development)
If you do not wish to use the simulator or `socat` networking, you can develop "blindly" on your PC, compile the APK, and sideload it directly to the physical board for every single test.

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
The **Third-Party Developer Guide & Protocol Specification**. This markdown file acts as the primary reference manual. It thoroughly documents:
*   How to prepare the Izis Smart Go Board's Android environment (ADB over Wi-Fi, custom launchers, etc.).
*   Hardware physical layouts and dynamic coordinate system mappings (19x19, 13x13, 9x9).
*   A list of known UART instructions (commands), including usage, examples and important notes.

### 2. [`izis_simulator.html`](izis_simulator.html)
An **Izis Smart Go Board Simulator** written in HTML, CSS, and JS. 
*   **Purpose:** Since the physical board operates via `/dev/ttyS1`, testing applications without a physical board (e.g., using an Android emulator) is difficult. This visual simulator replicates the board's LED arrays, button presses, and allow stone placements.
*   **Usage:** Open it in any modern browser. It connects via WebSocket to the Python bridge to display real-time hardware status and emit simulated events and command responses to your app. Left-click to place and right-click to remove stones.

### 3. [`izis_simulator_bridge.py`](izis_simulator_bridge.py)
A **TCP to WebSocket Bridge Script** written in Python.
*   **Purpose:** To bridge communication between your Android application running in an emulator and the HTML visual simulator.
*   **Usage:** Run the script using Python 3 (`python izis_simulator_bridge.py`). 
    *   It opens a **TCP socket on port 5000**. Configure your Android App's custom serial wrapper (e.g., `TcpConnectDirect`) to connect to `<IP>:5000`.
    *   It simultaneously opens a **WebSocket on port 8080**. Click "Connect" on the `izis_simulator.html` UI to bind them together. Data is seamlessly shuttled back and forth.

### 4. [`IZISBridge`](IZISBridge)
A demo **Android application to forward IZIS Smart Go Board serial device over TCP** and its full source code for third-party development.
*   Provide an UI-driven way to expose the Go Board hardware serial device over TCP without requiring terminal commands.
*   If developers are creating a PC or Web-based front-end applications for the smart Go Board, this can be used as (or as the template of) the companion board-side app that allows front-end application connecting to the board.

### 5. [`izis_cmd_test.py`](izis_cmd_test.py)
An **Interactive Command Testing Tool** written in Python.
*   **Purpose:** Before writing a full Android or PC/Web application, developers can use this CLI tool to directly interact with the Go board simulator or the physical hardware, fire specific commands, and monitor how the hardware reacts. It connects directly to the TCP port exposed by `izis_simulator_bridge.py`, `IZISBridge` or `socat`.
*   **Key Features:**
    *   **Interactive Menu:** Comes pre-loaded with known commands (e.g., `BOD19`, `SHP`, `HOT`, `LED11`) so you don't have to memorize the syntax.
    *   **Asynchronous Event Handling:** The MCU often emits passive events (like `~BKY#` button presses or `~SDA...#` auto-reports). This script filters these background events without breaking the wait cycle for your command's specific ACK response.
    *   **Smart Timeouts:** It inherently understands the protocol's quirks, such as commands that return nothing (e.g., `~FLL#`, `~AWO#`), and commands that require extremely long wait times (e.g., the `~ADJ#` calibration).
    *   **Safety Constraints:** Automatically enforces the mandatory 240ms delay after heavy matrix-rendering commands like the genuine Izis applications.
    *   **Manual Mode:** Allows developers to input raw `~...#` strings.

## Getting Started

1. **Review the Specifications:** Read `izis_protocol_spec.md` fully to understand how the hardware operates and its limitations.
2. **Install Dependencies:** Make sure Python 3 is installed along with the websockets library (`pip install websockets`).
3. **Start the Bridge:** Execute `izis_simulator_bridge.py`.
4. **Launch the Simulator:** Open `izis_simulator.html` in your browser and click "Connect".
5. **Develop your App:** Direct your Android application's serial logic to connect to the Python TCP socket rather than the physical `/dev/ttyS1` port while in debug mode. Watch your logic trigger lights and states in the HTML simulator in real-time.