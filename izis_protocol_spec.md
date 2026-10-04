# Izis Smart Go Board - Third-Party Developer Guide & Protocol Specification

> **⚠️ DISCLAIMER**
> This document is the result of personal reverse engineering research through the decompilation of genuine Izis applications and serial packet inspection. The author makes no guarantees regarding its accuracy, safety, or whether it aligns with Izis's original design intentions. Izis does not provide an official SDK, public documentation, or third-party developer support. Incorrect usage of these commands may potentially cause damage to the hardware. The author is in no way affiliated with Izis. Use this information entirely at your own risk.

## 1. Android Environment & System Setup

The Izis Smart Go Board contains an Android embedded system board and a microcontroller-based (MCU) Go board hardware with an RGB LED matrix. It runs a customized Android operating system and communicates with the Go board hardware through a serial interface.

### 1.1 Go Board Hardware Communication Endpoint
*   **Port:** UART mapped to `/dev/ttyS1`
*   **Configuration:** 115200 baud, 8 data bits, No parity, 1 stop bit (115200, 8, N, 1)
*   **Permissions:** The port is accessible to user-space applications (Read/Write). Standard Android Serial APIs can interact with it directly without root access.

### 1.2 USB Port Architecture, ADB & Sideloading
*   **USB Port Operating Mode:** The physical USB port functions as a **standard USB 2.0 Host port**. It natively supports standard USB peripherals (USB flash drives, keyboards, and mice) as well as external Prolific PL2303 USB-to-UART bridges (Vendor ID `0x067B`, Product ID `0x2303`) via bundled driver libraries found in genuine Izis APKs. However, the controller does not support USB Device / Peripheral mode. Consequently, direct PC-to-board wired ADB over cable is not supported; **ADB over Wi-Fi is the primary interface for debugging and shell access**.
*   **Sideloading APKs:** Place APKs onto a FAT32/NTFS USB flash drive, attach it to the board's USB port, and install via the native Android file manager (`Settings -> Storage -> Documents & other`).
*   **ADB over Wi-Fi Setup:**
    1. Connect the board and PC to the same local network.
    2. Enable Wireless Debugging / ADB over Network in Android Developer Options.
    3. Wireless ADB pairing (if prompted): `adb pair <BOARD_IP>:<PAIR_PORT>`.
    4. Connect from your PC: `adb connect <BOARD_IP>:<PORT>`.
    5. *Alternative:* If Developer Options are inaccessible, sideload a Terminal Emulator app via USB drive and enable ADB over TCP/IP (`setprop service.adb.tcp.port 5555 && stop adbd && start adbd`), then connect via `adb connect <BOARD_IP>:5555`.
    6. The board firmware is pre-rooted (`su` is available in `adb shell`).

### 1.3 The App Launcher & Architecture Warning
The proprietary default launcher hides sideloaded third-party applications.
*   **Third-Party Launcher Workaround:** Sideload a lightweight launcher (e.g., Lawnchair or Lawnchair-Lite). In Android Settings, configure it as the default "Home" application to access all installed apps.
*   **ES File Explorer Workaround:** `com.estrongs.android.pop` — ES File Explorer is whitelisted and will be visible in the "System Tools" folder if installed; therefore, it can be used to launch third-party applications hidden by the default launcher.
*   **Package Name Camouflage:** The primary filter for the proprietary default launcher uses a loose substring check. Any custom third-party application built with `cn.izis` in its package name or `applicationId` (e.g., `cn.izis.customapp`) bypasses the filter and renders directly on the main desktop screen.
*   **Disabling the Proprietary Launcher (optional):** The proprietary launcher is observed to sometimes set itself back as "Home" applications. It can be disabled via ADB (**DO NOT** do this before installing third-party launcher):
    ```bash
    adb shell pm disable-user --user 0 com.example.lxf.laucher2
    ```
*   **⚠️ IPC Dependency Warning:** Analysis of genuine Izis apps reveals two distinct hardware connection strategies:
    1. *Direct Serial (`SerialConnectDirect`):* Standalone apps like Fox Go (`com.foxwq.yhznqp`) access `/dev/ttyS1` directly and continue working with the stock launcher disabled.
    2. *IPC Service (`SerialConnectService`):* Stock satellite apps connect to `com.example.lxf.laucher2` via Android Binder IPC. Disabling `laucher2` kills this daemon, causing any native app that relies on `com.example.lxf.laucher2` to fail to communicate with the Go board hardware (such as `cn.izis.chessdesk2` and `cn.izis.yzbook`, the apps will still launch, but they will not be able to detect stone placements or light up LEDs).

### 1.4 Native App Endpoints
Izis package updates and platform integration clients can be extracted via (`adb shell pm list packages -3`) or inspected via the distribution endpoint:
`http://121.40.208.40:8080/GoWebService/every_chess_config.json`

---

## 2. Go Board Hardware Layout & Coordinate System

The board features a 19x19 physical LED/sensor grid, two turn indicator LEDs, and two physical buttons for clock/timer functions.
*   **Coordinate Rules:** The protocol uses a **1-based index**, numbered from **Right-to-Left, Top-to-Bottom**.
*   **Padding:** Coordinate values must **always be zero-padded to 3 digits** in commands (e.g., `001`, `019`, `361`).

### 2.1 Dynamic Board Sizing (`BOD` Commands)
The board dynamically alters its logical coordinate system and `SDA` payload length for smaller board sizes. A bounding box of green LEDs is illuminated on the physical boundary lines.

#### `~BOD19#` (19x19 Full Board)
*   **Valid Range:** `001` to `361`
*   **SDA Payload:** 361 characters. No boundary box is drawn.
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

### 3.1 Hardware Constraints & Timing Model
1. **Packet Framing:** Commands start with `~` and terminate with `#`. Packet extraction regex: `~?[A-Z]{3}[^~#]*#`. Decompiled serial code shows the app rejects packets containing characters outside `[A-Za-z0-9~#.,]`.
2. **Baseline Pacing Delay:** The MCU serial input parser requires a minimum baseline delay of **80 ms** between consecutive commands. Blasting commands without this pacing could potentially drop serial frames.
3. **Extended Render Delay:** Commands that clear or fill the full LED matrix (`~RGC#`, `~RGF#`, `~FLL#`) presumably halt MCU interrupts to update LED array. Genuine Izis client code mandates an extended delay of **240 ms** after sending these commands.
4. **Retry & Timeout Profile:** Decompiled client code implements a **500 ms** response timeout with up to **3 retries**.
5. **Color Rendering:** The matrix LEDs are standard RGB (no dedicated White diode). Mixed dim colors may appear washed out. Developers should test RGB values on physical hardware to ensure contrast.

### 3.2 System & Sensor Configuration

| Command | Expected ACK | Description |
| :--- | :--- | :--- |
| `~BOD19#` | `~GBS19#` | Configure board dimension and payload mode to 19x19. |
| `~BOD13#` | `~GBS13#` | Configure board dimension and payload mode to 13x13. |
| `~BOD09#` | `~GBS09#` | Configure board dimension and payload mode to 9x9. |
| `~STA#` | `~SDA<data>#` | Query full board state. `<data>` length matches active `BOD` mode (361, 169, or 81 chars). `0`=Empty, `1`=Black, `2`=White. |
| `~CTS1#` | `~UDS1#` | Enable auto-reporting (board emits `~SDA...#` asynchronously on stone changes). |
| `~CTS0#` | `~UDS0#` | Disable auto-reporting. |
| `~GVE#` | `~VERxxx#` | Query MCU firmware version (e.g., `~VER121#`). Expected response within 300 ms based on genuine app timeout logic. |
| `~GSV#` | `~FJX0.xx#` | Query Hall sensor threshold config. *Hypothesis:* Returns the comparator/ADC voltage threshold (分界线, *fēnjièxiàn*, e.g., 0.32V or 0.15V) used for stone detection. |
| `~SEP32#` | `~SSS#` | Set Hall sensor threshold to 0.32. |
| `~SEP15#` | `~SSS#` | Set Hall sensor threshold to 0.15. |
| `~ADJ#` | `~AEN#` | Calibrate Hall sensors. **Board must be completely empty.** Calibration blocks the MCU for > 30 seconds before returning `~AEN#`. Do not power off during calibration. |

> **Architecture Note on Move Detection (`CTS1` vs. `CTS0`):**
> Genuine Izis apps enable auto-reporting (`~CTS1#`) on boot, which requires custom software-level debounce filtering to handle the noisy stream of `~SDA...#` updates caused by hand movement and stone sliding over Hall sensors. For third-party turn-based implementations, disabling auto-reporting (`~CTS0#`) and querying the board state explicitly (`~STA#`) only upon receiving a physical clock button release event (`~BKY#` / `~WKY#`) provides a cleaner architecture that eliminates sensor jitter and prevents serial/TCP buffer flooding.

### 3.3 Hardware Indicator LEDs
The Top (Green) and Bottom (White) turn indicators are mutually exclusive.

| Command | Expected ACK | Description |
| :--- | :--- | :--- |
| `~LED11#` | `~LOS#` | Turn **ON Top Green**, turn OFF Bottom White. |
| `~LED21#` | `~LOS#` | Turn **ON Bottom White**, turn OFF Top Green. |
| `~LED10#` or `~LED20#` | `~LOS#` | Turn OFF both indicators. |

### 3.4 Single & Batch LED Target Commands
Target positions must always be zero-padded to 3 digits (e.g., `001`, `081`).
The RGB channels themselves must also be zero-padded to 3 digits (e.g., `r000g255b000`, not `r0g255b0`).

| Command Format | Expected ACK | Description |
| :--- | :--- | :--- |
| `~SHP<pos>,r<R>g<G>b<B>,<m>#` | `~HCS#` | **Single LED (Destructive):** Lights coordinate `<pos>`. Automatically clears previous `SHP` points. Mode `<m>` is typically `1` or `2` in decompiled app code (visually identical on hardware). |
| `~TLO<pos>,r<R>g<G>b<B>,<m>#` | `~TLS#` | **Sync LED:** Lights `<pos>` and syncs turn indicators. `m`: `0`=Indicators off, `1`=Top on, `2`=Bottom on, `3`=Both on. Automatically clears previous `TLO` points. |
| `~HOTA<p1>r<R>g<G>b<B>B<p2>...C<p3>...D<p4>...N<c>#` | `~HSM#` | **Batch LED (Non-Destructive):** Appends up to 4 LEDs without clearing existing lights. **All 4 points (A, B, C, D) must be present in the command string**, while `N<c>` (`1`–`4`) specifies the actual render count. Unused points must be padded with dummy data. |

*Batch Example:* `~HOTA001r255g000b000B019r000g255b000C001r000g000b000D001r000g000b000N2#` (Renders points A and B).

### 3.5 Full Matrix LED Render Commands

| Command | Expected ACK | Delay Rule | Description |
| :--- | :--- | :--- | :--- |
| `~RGC#` | `~ALC#` | **240 ms** | **Clear All:** Extinguishes all LEDs, including boundary frames. |
| `~RGF#` | `~SIC#` | **240 ms** | **Clear Inner:** Extinguishes grid LEDs while preserving the active `BOD` boundary frame. |
| `~FLL#` | (None) | **240 ms** | **Fill:** Illuminates the entire matrix in dim white. Treated as fire-and-forget in decompiled serial code. |
| `~SA[L\|M\|W\|R]<361_chars>#` | `~ALS#` | **80 ms** | **Matrix Write:** 361-character array (`0`=Off, `1`–`9`=Palette indices). Brightness hierarchy (highest to lowest): **`SAR` (Raw / Max)** > **`SAL` (High)** > **`SAM` (Medium)** > **`SAW` (Low)**. |

#### ⚠️ Hardware Power Limiting Rule
Driving more than 50 LEDs simultaneously draws substantial current. In genuine Izis apps, **whenever more than 50 LEDs are illuminated simultaneously, the LED matrix write command is forced down to `~SAW` (Low)** presumably to prevent overstressing the power supply. Third-party applications (e.g., rendering KataGo territory ownership or heatmaps) must enforce this limit to be on the safe side.

> **Brightness Hierarchy & Hardware Palette Access:**
> Empirical hardware testing reveals key functional distinctions between `~SAR` and `~SA[L|M|W]`:
> 1. **Brightness Levels:** `~SAR` renders at full, unattenuated maximum brightness (higher than `~SAL`). `~SAL` (High), `~SAM` (Medium), and `~SAW` (Low) correspond to firmware-scaled brightness tiers (mapped to app-level values 180, 150, and 100 respectively).
> 2. **Color Palette Availability:** `~SAL`, `~SAM`, and `~SAW` only render palette indices `1` and `2` (turning off indices `3`–`9`). Only `~SAR` enables the full 9-color hardware lookup table (visually resolving into 5 distinct human-visible colors on the board).
> * **Green:** `1`, `3`, `8` (visually indistinguishable; use `1` as standard)
> * **White:** `2`, `4`, `9` (visually indistinguishable; use `2` as standard)
> * **Pure Red:** `5` (vibrant red)
> * **Magenta:** `6` (distinct pink-purple)
> * **Peach / Salmon:** `7` (warm amber/salmon, approx. RGB 245, 175, 130)
> 3. **Thermal & Power Caution:** Because `~SAR` operates at maximum LED brightness, displaying dense matrices (>50 LEDs) under `~SAR` draws significant current. Engines rendering large heatmaps should avoid illuminating the entire matrix under `~SAR` simultaneously to prevent supply voltage drops.

> **Sub-Board Boundary Notice for Matrix Writes:**
> All `~SA*` commands unconditionally overwrite the entire 361-LED matrix. When running in 13x13 or 9x9 mode, issuing a raw `~SA*` array of `0`s will wipe out the green boundary frame created by `~BODxx#`. In genuine Izis apps, helper methods like `lampMultiple()` explicitly pre-populate the perimeter indices with palette color `1` (which renders as green) within the 361-character payload so that matrix updates do not erase the active board boundary.

### 3.6 Graphic & Audio Feedback

| Command | Expected ACK | Description |
| :--- | :--- | :--- |
| `~RLO#` | `~DSC#` | Displays green **"OK / Circle"** matrix icon. (Decompiled client code treats as fire-and-forget). |
| `~RLT#` | `~DSC#` | Displays green **"Checkmark / V"** matrix icon. (Decompiled client code treats as fire-and-forget). |
| `~RLW#` | `~DSC#` | Displays red **"Cross / X"** matrix icon. (Decompiled client code treats as fire-and-forget). |
| `~AWO#` | (None) | Standard prompt / error buzzer beep. Fire-and-forget. |
| `~AWS#` | (None) | *Decompiled Method:* `secondWarning()` (Byo-yomi countdown beep). *Note:* Produces no audible output on tested hardware revisions. |
| `~AWT#` | (None) | *Decompiled Method:* `baseTimeWarning()` (Time expiration alarm). *Note:* Produces no audible output on tested hardware revisions. |

### 3.7 Hardware Button Events
Hardware button events are emitted upon key release.

| Event | Physical Interaction | Decompiled App Identifier | Description |
| :--- | :--- | :--- | :--- |
| `~BKY#` | Top Button Short Press | `clickBlack` | Emitted immediately on button release. |
| `~BTK#` | Top Button Long Press | `doubleClickBlack` | Labeled as double-click in decompiled app code, but triggers on hardware upon key release after holding for ~1 second. |
| `~WKY#` | Bottom Button Short Press | `clickWhite` | Emitted immediately on button release. |
| `~WTK#` | Bottom Button Long Press | `doubleClickWhite` | Labeled as double-click in decompiled app code, but triggers on hardware upon key release after holding for ~1 second. |