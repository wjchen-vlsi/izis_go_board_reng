# Izis Smart Go Board - Third-Party Developer Guide & Protocol Specification

> **⚠️ DISCLAIMER**
> This document is the result of personal reverse engineering research. The author makes no guarantees regarding its accuracy, safety, or whether it aligns with Izis's original design intentions. Incorrect usage of these commands may potentially cause damage to the hardware. The author is in no way affiliated with Izis. Furthermore, there is no guarantee that Izis will not update their system in the future to block or restrict third-party development. Use this information entirely at your own risk.

## 1. Android Environment & System Setup

The Izis Smart Go Board contains an Android embedded board and a microcontroller-based (MCU) Go board hardware with RGB LED matrix. It runs a highly customized Android operating system and communicates with the Go board hardware through a serial interface. Preparing it for third-party development requires specific steps.

### 1.1 Go Board Hardware Communication Endpoint
*   **Port:** UART mapped to `/dev/ttyS1`
*   **Configuration:** 115200, 8, N, 1
*   **Permissions:** The port is accessible to user-space applications (Read/Write). Standard Android Serial APIs can interact with it directly without root access.

### 1.2 USB OTG, ADB & Sideloading
*   **USB Port Limitation:** The physical USB port functions **strictly as a USB OTG host** (e.g., for mice, keyboards, or USB flash drives). It **cannot** be used for a direct PC-to-Board ADB connection via cable (At least I can't get it to work through USB port, please let me know if you manage to do it).
*   **Sideloading APKs:** You can place your APKs on a USB flash drive, plug it to the board, and install them using the Android native file manager (`Settings -> Storage -> Documents & other`).
*   **ADB over Wi-Fi:** To connect via ADB, you must use ADB over Wi-Fi.
    1. Connect the board and PC to the same Wi-Fi.
    2. Enable Wireless Debugging pairing in Android Developer Options.
    3. Pair and connect from your PC: `adb pair <BOARD_IP>:<PORT>`
    3. *Alternative:* If Developer Options are locked, use a USB flash drive to sideload a Terminal Emulator app, open it, and force-enable ADB over TCP/IP.
    4. Connect from your PC: `adb connect <BOARD_IP>:<PORT>`. 
    5. The board is pre-rooted (`su` is available in `adb shell`).

### 1.3 The App Launcher Workaround
The proprietary default launcher hides sideloaded third-party applications, so you only get to launch the sideloaded application when offered by Android upon installation.
*   **Solution:** Sideload a lightweight third-party launcher (like Lawnchair) via USB flash drive or ADB. Go to Android Settings and set it as the default "Home" application. You will then see all installed APKs and Izis applications.

### 1.4 Extracting Native Izis Apps
To inspect official Izis apps, list third-party packages via ADB (`adb shell pm list packages -3`) and extract them.
Additionally, Izis' latest APK endpoints (including integrations with various online go platforms) can be found at: 
`http://121.40.208.40:8080/GoWebService/every_chess_config.json`

---

## 2. Go Board Hardware Layout & Coordinate System

The board features a 19x19 physical LED/sensor grid, two status LEDs, and two physical buttons for the Go timer (Go clock). 
*   **Coordinate Rules:** The protocol uses a **1-based index**, numbered from **Right-to-Left, Top-to-Bottom**. 
*   **Format:** Coordinate values must **always be zero-padded to 3 digits** in commands (e.g., `001`, `009`, `015`, `361`).

### 2.1 Dynamic Board Sizing (`BOD` Commands)
The board dynamically shrinks its logical coordinate system and `SDA` payload for smaller games. A bounding box of Green LEDs is drawn exactly **one line outside** the valid playing area.

#### `~BOD19#` (19x19 Full Board)
*   **Valid Range:** `001` to `361`
*   **SDA Payload:** 361 chars. No bounding box is drawn.
```text
=========================================================
|                 [Top Indicator: Green LED]            |
|                                                       |
|    +---------------------------------------------+    |
|    |  19  18  17  16 . . . . . . . 4   3   2   1 |   (Top Button)
|    |  38  37  36  35 . . . . . . .23  22  21  20 |    [ BTN 1 ]
|    |  .                                      .   |        |
|    |  .               19 x 19                .   |   [ LCD Screen]
|    |  .               Grid Area              .   |        |
|    | 361 360 359 358 . . . . . . 346 345 344 343 |        |
|    +---------------------------------------------+   (Bottom Button)
|                                                       [ BTN 2 ]
|                 [Bottom Indicator: White LED]         |
=========================================================
```

#### `~BOD13#` (13x13 Mode)
*   **Valid Range:** `001` to `169`
*   **SDA Payload:** 169 chars.
*   **Physical Mapping:** Centered on the board. The bounding box is drawn on the 3rd and 17th lines of the physical 19x19 grid.
```text
       [ Top Indicator: Green LED ]
    <-- Left                 Right -->
    13  12  11  10 . . . 4   3   2   1
    26  25  24  23 . . .17  16  15  14
   ... ... ... ... ... ... ... ... ...
   169 168 167 166 . . 160 159 158 157
      [ Bottom Indicator: White LED ]
```

#### `~BOD09#` (09x09 Mode)
*   **Valid Range:** `001` to `081`
*   **SDA Payload:** 81 chars.
*   **Physical Mapping:** Centered on the board. The bounding box is drawn on the 5th and 15th lines of the physical 19x19 grid.
```text
       [ Top Indicator: Green LED ]
    <-- Left                 Right -->
     9   8   7   6   5   4   3   2   1
    18  17  16  15  14  13  12  11  10
   ... ... ... ... ... ... ... ... ...
    81  80  79  78  77  76  75  74  73
      [ Bottom Indicator: White LED ]
```

---

## 3. Protocol Instruction Set

### 3.1 Hardware Constraints & Rules
1. **Command Syntax:** All commands start with `~` and terminate with `#`.
2. **Heavy Render Delay (Anti-Crash):** While not all commands strictly require a delay in-between, commands that modify the entire RGB LED array (`~RGC#`, `~RGF#`, `~FLL#`, `~SA*#`) consume significant MCU processing time. Izis native applications impose **additional delay of 240ms** after sending these commands presumably to prevent buffer overflows and hardware crashes.
3. **Color Gamut:** The physical RGB LEDs have a limited color gamut. Exact RGB values (especially mixed dim colors) may display inaccurately or wash out to white. Developers must experiment to find visually distinct colors.

### 3.2 System & Sensor Config

| Command | Response | Description |
| :--- | :--- | :--- |
| `~STA#` | `~SDA<data>#` | Query board state. `<data>` length matches BOD mode. `0`=Empty, `1`=Black, `2`=White. |
| `~CTS1#` | `~UDS1#` | Enable auto-reporting (board emits `~SDA...#` on stone placement). |
| `~CTS0#` | `~UDS0#` | Disable auto-reporting. |
| `~GVE#` | `~VERxxx#` | Get firmware version (e.g., `~VER121#`). |
| `~GSV#` | `~FJX0.xx#` | Get boundary separator line config. **It is not known what this 'boundary seperator line' is referring to.**|
| `~SEP32#` | `~SSS#` | Set the boundary separator line to 0.32. |
| `~SEP15#` | `~SSS#` | Set the boundary separator line to 0.15. |
| `~ADJ#` | `~AEN#` | Calibrate Hall sensors. **Board must be empty. DO NOT power off, you must wait for the `AEN` response. It will takes > 30 seconds to receive an `AEN` response** |

### 3.3 Hardware Indicator LEDs
The Top (Green) and Bottom (White) LEDs are mutually exclusive.

| Command | Response | Description |
| :--- | :--- | :--- |
| `~LED11#` | `~LOS#` | Turn **ON Top Green**, Turn OFF Bottom White. |
| `~LED21#` | `~LOS#` | Turn **ON Bottom White**, Turn OFF Top Green. |
| `~LED10#` or `~LED20#`| `~LOS#` | Turn OFF both indicators. |

### 3.4 Single & Batch LED Target Commands
**Target positions must be zero-padded to 3 digits (e.g., `001`, `081`).**

| Command Format | Response | Description |
| :--- | :--- | :--- |
| `~SHP<pos>,r<R>g<G>b<B>,1#` | `~HCS#` | **Single Light:** Lights up coordinate. *Sending a new SHP automatically extinguishes the previous SHP light.* |
| `~TLO<pos>,r<R>g<G>b<B>,<m>#` | `~TLS#` | **Sync Light:** Lights up `<pos>` and syncs indicators. `m`: `0`=Both indicators off, `1`=Top On, `2`=Bottom On, `3`=Both indicators on. *Sending a new TLO automatically extinguishes the previous TLO light.*|
| `~HOTA<p1>r<R>g<G>b<B>B<p2>...C<p3>...D<p4>...N<c>#` | `~HSM#` | **Batch Light (Non-Destructive):** Unlike `SHP` and `TLO`, `HOT` lights up new LEDs *without* turning off previously active lights. **You MUST provide all 4 points (A, B, C, D) in the string**, but `<c>` (1-4) dictates how many are actually rendered. Response does not echo payload. |

*Example:* `~HOTA001r255g000b000B019r000g255b000C343r000g000b255D361r255g255b255N2#` (Provides 4 points, but only writes A and B).

### 3.5 Full Matrix LED Render Commands (Requires 240ms Delay)

| Command | Response | Description |
| :--- | :--- | :--- |
| `~RGC#` | `~ALC#` | **Clear All:** Extinguishes ALL LEDs, including boundaries. |
| `~RGF#` | `~SIC#` | **Clear Inner:** Extinguishes grid LEDs but *preserves* the BOD bounding box. |
| `~FLL#` | (None) | **Fill:** Lights up the entire board with a dim white color. |
| `~SA[L\|M\|W\|U\|N\|R]<361_chars>#`| `~ALS#` | **Matrix Write:** 361-char array (`0`=Off, `1` ~ `9`= Firmware pre-defined palette). Prefixes indicate brightness levels (often indistinguishable in practice). **NOT all prefixes are implmented in the firmware, `SAL` and `SAR` are confirmed to works** |

### 3.6 Graphic & Audio Feedback

| Command | Response | Description |
| :--- | :--- | :--- |
| `~RLO#` | `~DSC#` | Draws Green **"OK"** graphic. |
| `~RLT#` | `~DSC#` | Draws Green **"Tick / V"** graphic. |
| `~RLW#` | `~DSC#` | Draws Red **"Cross / X"** graphic. |
| `~AWO#` | (None) | Emits hardware Beep-Beep sound. Does not return a response. |
| `~AWT#` / `~AWS#` | (None) | *Deprecated:* Originally intended for base-time and byoyomi warnings, but these commands emit no sound and return no response on current firmware. Developers should use standard Android Text-To-Speech (TTS) or media players for time warnings. |

### 3.7 Hardware Button Events
These events are emitted upon user interaction. They are triggered on **Key-Up** (button release). B/W names merely indicate physical location.

| Event Emitted | Action Triggered |
| :--- | :--- |
| `~BKY#` | Top button **short press**. |
| `~BTK#` | Top button **long press** (Triggered upon release if held for **> 1 second**). |
| `~WKY#` | Bottom button **short press**. |
| `~WTK#` | Bottom button **long press** (Triggered upon release if held for **> 1 second**). |