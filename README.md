# Izis Smart Go Board - Third-Party Development Kit & Reverse Engineering Specs

> **⚠️ DISCLAIMER**
> This repository is the result of independent, personal reverse-engineering research on genuine Izis software and on the behaviour of the board, written to let third-party software work with the board. The author is in no way affiliated with Izis, and this repository is not endorsed or supported by Izis. The author makes no guarantees regarding its accuracy, completeness, safety, or whether it aligns with Izis's original design intentions. Some commands change the board permanently or could make it unusable (see the specification, section 3.8); incorrect usage may damage the hardware. Furthermore, there is no guarantee that Izis will not update their system in the future to block or restrict third-party development. Use this information entirely at your own risk.

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

> **⚠️ Stock Launcher Visibility:** The board's default launcher hides third-party APKs unless their package name contains the substring `cn.izis` (anywhere in the name; only `cn.izis.yzutil` and `cn.izis.yzbrowser` are sent to the "System Tools" folder instead). `IZISBridge` uses `cn.izis.izisbridge` to remain visible on the home screen. Any custom app intended to run on the board should adopt this naming convention or use a third-party launcher.

> **⚠️ One Reader at a Time:** Close the Izis Go apps before forwarding `/dev/ttyS1`. While an Izis app is connected to the launcher's serial service, the launcher holds the port too, and two processes reading one port each get part of the byte stream, so replies and events can go missing (see section 1.1 of the specification).

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
For developers with an active root ADB shell connection to the board, you can forward serial data directly via terminal (the same one-reader caveat applies):
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

An on-board app can either open `/dev/ttyS1` directly or share the board with running Izis apps through the launcher's serial service (Binder IPC, described in section 1.5 of the specification; not yet tested by a third-party app).

---

## Repository Contents

### 1. [`izis_protocol_spec.md`](izis_protocol_spec.md)
The **Third-Party Developer Guide & Protocol Specification**. This is the primary reference manual. It thoroughly documents:
*   Android system setup (Wi-Fi ADB pairing, launcher workarounds, permissions, native app endpoints) and the launcher's shared serial service (Binder IPC).
*   Coordinate system rules (1-based, right-to-left, top-to-bottom, zero-padded) and dynamic board sizing (`~BOD19#`, `~BOD13#`, `~BOD09#`, further sizes and custom frame colours).
*   Complete UART command reference with expected ACKs and timing requirements, including the RGB turn indicators (`~GLC`) and the sensor readout (`~REQ#`).
*   The 9-color `~SAR` palette (RGB values and appearance on the board), the two-color `~SAL`/`~SAM`/`~SAW` tiers, and the power rule genuine Izis apps apply to dense frames.
*   Warnings for commands that change the board permanently (calibration, separator, firmware update) and codes in Izis apps that firmware 121 ignores.
*   Pacing rules explained by the board's own timing (when a frame can be lost, why waiting for the reply is safe), and how long calibration and a restart take.
*   A basis tag on every claim: `[verified]` (tested on the board), `[RE]` (reverse engineered, not board-tested) or `[inferred]` (educated guess or estimate).

### 2. The simulator: [`izis_simulator.html`](izis_simulator.html), [`izis_board_model.js`](izis_board_model.js), [`izis_simulator_tests.html`](izis_simulator_tests.html)
An **Izis Smart Go Board Simulator** written in HTML, CSS, and JavaScript, in three files that belong together. Open `izis_simulator.html` in a browser (no server needed; it loads `izis_board_model.js` from its own folder).
*   **Purpose:** Replicates the physical board in a web browser: the 19x19 LED matrix, the frames around smaller boards, the two turn indicators, the clock buttons, the stone sensors, and the board's timing, so that an app can be developed and its error handling tried without the hardware. It follows the protocol specification (sections 2 and 3.1 to 3.9); the differences that remain are listed below.
*   **The files:**
    *   [`izis_simulator.html`](izis_simulator.html): the page: the board drawing, the console, the controls and the WebSocket link to the bridge.
    *   [`izis_board_model.js`](izis_board_model.js): the board itself (class `BoardModel`): frames in, replies and unsolicited frames out, LED, stone and button state, with no drawing and no network code. The page only draws what the model holds and sends what it says; another tool can load the model alone.
    *   [`izis_simulator_tests.html`](izis_simulator_tests.html): the model's tests. Open it in a browser: it prints `RESULT: PASS <n>/<n>`, or one `FAIL` line per failed test. Run it after every change to the model.
*   **What it does:**
    *   Every board size of section 2.1 (`~BOD<nn>#` for 04 to 13, 15 and 19, and `~BSC`) with its frame; any other `~BOD` value selects 19x19 without a reply and leaves the old frame lit.
    *   The turn indicators (`~LED`, `~GLC`), the `~SHP`/`~TLO` current point and `~TLO`'s indicator modes, `~HOTA` (complete frames only; a short one draws the last complete one again), the four matrix tiers (`~SAR`, `~SAL`, `~SAM`, `~SAW`) with their palettes, `~FLL#`, `~RGC#`, `~RGF#`, the pictures (`~RLO#`, `~RLT#`, `~RLW#`), `~AWO#`.
    *   Fields read at fixed character positions, no range check on positions, and the frames the board drops without a reply: more than 370 characters, an unknown code, the codes of section 3.9.
    *   The queries `~STA#`, `~GVE#`, `~GSV#`, `~GBS#` and `~REQ#`, and auto-report (`~CTS`), including its pause after `~BOD`, `~BSC`, `~SA*`, `~RL*` and `~AWO#`.
    *   Reply latency of 20 to 50 ms (140 ms after a full `~SA*` frame), every frame sent in the order it was produced, as on the board's one line; pacing warnings in the console (80 ms between frames, 240 ms after `~RGC#`, `~RGF#` and `~FLL#`; the warning allows 10 ms for the WebSocket's timing), and the buttons' timing: a hold of 1.2 s or more is a long press, two presses of the same button less than 200 ms apart give one event, on the release of the second.
    *   Stone placement by mouse (left-click places, right-click clears), the two clock buttons, and an interactive command console with Tab autocomplete, command templates and senders for `~GLC` and `~SHP`; drag the console's title bar to make it taller or shorter.
*   **Restart and faults** (side panel "Board Restart & Faults"):
    *   **Power cycle:** the board restarts while the bridge stays connected. It is in 19x19 with auto-report on and every LED and indicator off; the stones on the board stay. It ignores everything for the calibration load (setting **Calibration load (s)**, 16 s by default), then sends `~GBS19#` and a full `~SDA...#` without being asked (specification, sections 2.1 and 3.1). Use it to check how an app handles the board's restart.
    *   **Lose frames sent too fast:** a frame that arrives too soon after the previous one is lost, with the probabilities of section 3.1: after a short frame 100 % at 0 ms, 80 % at 10 ms, 50 % at 20 ms, 10 % at 30 ms, none from 40 ms; after a full `~SA*` frame 100 % up to 30 ms, 90 % at 40 and 50 ms, 80 % at 60 ms, 50 % at 70 ms, 30 % at 80 ms, none from 90 ms (linear in between). The console notes each lost frame.
    *   **Garble the next report:** the next `~SDA...#` frame the simulator sends ends in `?` instead of its last digit; the switch then clears itself. Use it to check how an app handles a report that does not parse.
*   **Dangerous commands:** `~UPD#`, `~ADJ#`, `~SEP<nn>#`, `~WBS<d>#` and the update replies `~CRCYES#`, `~CRCERR#`, `~CRY#`, `~CRE#` (specification, section 3.8) are not simulated. The console shows a red warning; there is no reply and no effect. `~GSV#` always answers `~FJX0.32#`.
*   **Known differences from firmware 121:**
    *   A button event comes about 200 ms after the release, where the board sends it 45 to 90 ms after (section 3.7): the simulator waits that long to see whether a second press follows, because two presses less than 200 ms apart give one event. Where the specification gives no value, the simulator uses a stated estimate: the calibration load is 16 s, the auto-report pause is 135 ms, a position beyond the 19x19 matrix after a small `~BOD` is not drawn, and where 19 minus the size is odd the extra line lies after the playing area in the matrix's own order (the specification does not say which side).
    *   A `~SA*` frame is accepted only with exactly 361 digits, and `~BOD` only with exactly two; the board's format checks are not fully known. A `~HOTA` count of 5 to 9 draws four segments. `~RGF#` also clears lit LEDs outside the frame (the specification only says that the frame stays).
    *   Frame loss follows the probabilities of section 3.1 by the time between two frames; the board's timer tick, its main loop and the time it takes no input while writing LEDs are not modelled. The pacing warning does not add 87 microseconds per character.
    *   The stone sensors are not simulated: `~REQ#` reads 1.5 V for an empty point, 0.4 V for black and 2.5 V for white without jitter, and `~GBS#` always reads 255. There is no separator, no calibration and no stored byte to change; the board's crash and settings-memory frames (`~ILL#`, `~24C32 Check Failed!#`) are never sent.
    *   The page does not reproduce brightness: the LED values are exact in the model, but the page draws them brightened, and the two indicators with a minimum brightness so that a dim colour is visible. An LED set to 0, 0, 0 is drawn off. The page draws an LED over a stone, where on the board the stone hides the light under it (section 3.4). The beep is the browser's own tone, not the board's.
    *   Letting the mouse leave a button, or the page lose the focus, counts as releasing it.

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
    *   Pre-loaded command presets (`STA`, `BODxx`, `HOT`, `SAR` palette test, `LEDxx`, `SEPxx`, `ADJ`; `ADJ` waits up to 90 s, enough for the calibration, which takes about 40 s).
    *   Background listener thread that parses asynchronous events (`~SDA...#`, button events `~BKY#` / `~WKY#`) without desynchronizing active command responses.
    *   Automatic timing compliance (240 ms extended delay for `~RGC#`, `~RGF#`, `~FLL#`; 80 ms baseline pacing for standard commands).
    *   Manual entry mode for custom protocol strings.
*   **⚠️ Permanent presets:** `SEP32`, `SEP15` and `ADJ` write the board's non-volatile memory; their effect survives power cuts. Run `ADJ` only on a completely empty board.
*   **Limitations:**
    *   In manual mode, a blank "expected response prefix" never matches, so the command always ends in a timeout. Enter the prefix (e.g. `DAT` for `~REQ#`), or answer `n` to "Does this command respond?".
    *   Received text outside a `~...#` frame is discarded without a message.
    *   Replies are matched by prefix only: with auto-report on, an unsolicited `~SDA...#` can be taken as the reply to `~STA#`.

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
   * Browser: Open `izis_simulator.html` (keep `izis_board_model.js` beside it) and click **Connect**.
4. **Smoke-Test the Pipeline:**
   * Terminal 2: Run the interactive test CLI:
     ```bash
     python izis_cmd_test.py
     ```
   * Send test commands (e.g., `[19] SAR Palette Test` or `[16] Batch 4 Corners`) and observe real-time rendering in `izis_simulator.html`.
5. **Develop Your Application:** Direct your client socket logic to connect to `127.0.0.1:5000` during development, or point it to `<BOARD_IP>:5000` when running against the physical board via `IZISBridge`.
