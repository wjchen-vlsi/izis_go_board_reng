# Izis Smart Go Board - Third-Party Developer Guide & Protocol Specification

> **⚠️ DISCLAIMER**
> This document is the result of independent, personal reverse-engineering research on genuine Izis software and on the behaviour of the board, written to let third-party software work with the board. The author is in no way affiliated with Izis, and this document is not endorsed or supported by Izis, which provides no official SDK, public documentation, or third-party developer support. The author makes no guarantees regarding its accuracy, completeness, safety, or whether it aligns with Izis's original design intentions, and an Izis software or firmware update may change the behaviour described here at any time. Some commands change the board permanently or could make it unusable (section 3.8); incorrect usage may damage the hardware. Use this information entirely at your own risk.

> **Scope and basis tags**
> Tested on an Izis Smart Go Board 3Plus 5G (model UW-M527, Android 13) running MCU firmware 121 (`~GVE#` answers `~VER121#`). Other models and firmware versions may behave differently; some codes that genuine Izis apps send are meant for other firmware (section 3.9). Each claim carries one tag, which says how it is known:
> * **[verified]** - seen on the tested board: its LEDs, sound, replies and events, or what its Android system and logs show, including what genuine Izis apps were seen sending to it. RGB values are given as the firmware sets them; on such a value, [verified] means the board showed a matching colour.
> * **[RE]** - read in code, the board's firmware or a genuine Izis app, and not seen on the board: not tested yet, or unsafe to test (⚠️).
> * **[inferred]** - reasoned from the above, neither read in code nor seen; an estimate or an educated guess.
>
> A claim about what Izis apps do, not the board, says so ("Izis apps ..."); its tag says how that is known. In the tables, the Basis column covers what the command does and its reply; any other statement in a row carries its own tag. Advice and definitions carry no tag. ⚠️, **[DANGER]** and **[RISKY]** mark risk, not evidence.

## 1. Android Environment & System Setup

The Izis Smart Go Board contains an Android embedded system board and a microcontroller-based (MCU) Go board hardware with an RGB LED matrix. It runs a customized Android operating system and communicates with the Go board hardware through a serial interface.

### 1.1 Go Board Hardware Communication Endpoint
*   **Port:** UART mapped to `/dev/ttyS1`
*   **Configuration:** 115200 baud, 8 data bits, No parity, 1 stop bit (115200, 8, N, 1)
*   **Permissions:** `/dev/ttyS1` is world-readable and world-writable (`crw-rw-rw-`, owner `system`), so any app can open it with standard Android serial APIs, without root access **[verified]**. This also means any installed app can send the firmware update command (section 3.8).
*   **One reader at a time:** Izis apps that use the launcher's serial service (sections 1.3 and 1.5) make the launcher open the port; the launcher holds it only while such an app is connected **[verified]**. When two processes have the port open, each reads part of the incoming byte stream, so replies and events reach one process or the other **[verified]**; a single frame may also be split between them **[inferred]**. Close the Izis Go apps before running your own direct-serial app.

### 1.2 USB Port Architecture, ADB & Sideloading
*   **USB Port Operating Mode:** The physical USB port functions as a **standard USB 2.0 Host port**. It natively supports standard USB peripherals (USB flash drives, keyboards, and mice) as well as external Prolific PL2303 USB-to-UART bridges via the driver library bundled in genuine Izis apps, which accepts the USB IDs `067B:2303`, `067B:2551`, `067B:2503`, `067B:AAA5`, `05AD:0FBA` and `067B:2304` **[RE]**. However, the controller does not support USB Device / Peripheral mode. Consequently, direct PC-to-board wired ADB over cable is not supported; **ADB over Wi-Fi is the primary interface for debugging and shell access**.
*   **Sideloading APKs:** Place APKs onto a FAT32/NTFS USB flash drive, attach it to the board's USB port, and install via the native Android file manager (`Settings -> Storage -> Documents & other`).
*   **ADB over Wi-Fi Setup:**
    1. Connect the board and PC to the same local network.
    2. Enable Wireless Debugging / ADB over Network in Android Developer Options.
    3. Wireless ADB pairing (if prompted): `adb pair <BOARD_IP>:<PAIR_PORT>`.
    4. Connect from your PC: `adb connect <BOARD_IP>:<PORT>`.
    5. *Alternative:* If Developer Options are inaccessible, sideload a Terminal Emulator app via USB drive and enable ADB over TCP/IP (`setprop service.adb.tcp.port 5555 && stop adbd && start adbd`), then connect via `adb connect <BOARD_IP>:5555`.
    6. The board firmware is pre-rooted: `/system/xbin/su` is setuid root and takes the form `su 0 <command>` (not `su -c`). It works from `adb shell`, but not from app processes; apps do not need it, because `/dev/ttyS1` is world-writable **[verified]**.

### 1.3 The App Launcher & Architecture Warning
The proprietary default launcher hides sideloaded third-party applications.
*   **Third-Party Launcher Workaround:** Sideload a lightweight launcher (e.g., Lawnchair or Lawnchair-Lite). In Android Settings, configure it as the default "Home" application to access all installed apps.
*   **ES File Explorer Workaround:** `com.estrongs.android.pop` — ES File Explorer is whitelisted and will be visible in the "System Tools" folder if installed (together with the Izis test app `cn.izis.yzutil` and the Izis app store `cn.izis.yzbrowser`) **[verified]**; the launcher's code puts Settings there too **[RE]**; therefore, it can be used to launch third-party applications hidden by the default launcher.
*   **Package Name Camouflage:** The launcher puts every launchable app whose package name contains the substring `cn.izis` (anywhere in the name) on the main desktop, except `cn.izis.yzutil` and `cn.izis.yzbrowser`, which go to "System Tools" **[verified]**. A custom application built with `cn.izis` in its package name or `applicationId` (e.g., `cn.izis.customapp`) therefore renders directly on the main desktop. Some launcher builds list a few other named packages as well (for example Fox Go on A133-based models) **[RE]**; on the UW-M527, Fox Go is not on the desktop but is listed in the online-platform connector `com.izis.yzext` **[verified]**.
*   **Disabling the Proprietary Launcher (optional):** The proprietary launcher is observed to sometimes set itself back as "Home" applications. It can be disabled via ADB (**DO NOT** do this before installing third-party launcher):
    ```bash
    adb shell pm disable-user --user 0 com.example.lxf.laucher2
    ```
*   **⚠️ IPC Dependency Warning:** Genuine Izis apps use two hardware connection strategies:
    1. *Direct Serial:* Fox Go (`com.foxwq.yhznqp`), the Izis test app (`cn.izis.yzutil`) and the Izis serial demo app (`cn.izis.codelibserialport`) open `/dev/ttyS1` themselves on the UW-M527 **[verified]**; these apps keep working with the stock launcher disabled **[RE]**.
    2. *Launcher Service:* On the UW-M527 the tsumego app `cn.izis.yzbook`, the main Go app `cn.izis.chessdesk2` and the online-platform connector `com.izis.yzext` connect to the serial service of `com.example.lxf.laucher2` via Android Binder IPC, and the launcher holds the port for them **[verified]**. The tsumego app does so always, the main Go app when the launcher's version code is 7 or higher (14 on the tested board), and the connector except on old launchers **[RE]**. Disabling `laucher2` removes this service, so these apps still launch but cannot detect stone placements or light up LEDs **[RE]**.
*   **Shared connection:** All apps connected to the launcher service share one serial connection. When one of them closes the connection, it is closed for every connected app (section 1.5) **[RE]**.

### 1.4 Native App Endpoints
Izis package updates and platform integration clients can be extracted via (`adb shell pm list packages -3`) or inspected via the distribution endpoint:
`http://121.40.208.40:8080/GoWebService/every_chess_config.json`

### 1.5 Sharing the Board Through the Launcher's Serial Service
The launcher's serial service is exported without a permission and does not check its callers, so any installed app can bind it and drive the board alongside running Izis apps **[RE]**. No third-party app has been tested with it yet.

*   **Binding:** `Intent` with action `com.lxf.aidl.SerialServer` and package `com.example.lxf.laucher2`, flag `BIND_AUTO_CREATE`; then call `registerListener` **[RE]**. The tested board's launcher (version 1.1.4+1) registers its serial service for this action **[verified]**. If the port is already open, the new listener gets `onConnectSuccess()` at once; otherwise the service opens it.
*   **Interfaces:** Both AIDL files must be declared in package `com.example.lxf.laucher2` with these names, and the methods must keep this order, because the order fixes the Binder transaction codes (shown as comments) **[RE]**:

    ```aidl
    // ISerialService.aidl
    package com.example.lxf.laucher2;
    import com.example.lxf.laucher2.ISerialServiceListener;

    interface ISerialService {
        void registerListener(ISerialServiceListener listener);    // 1
        void unRegisterListener(ISerialServiceListener listener);  // 2
        void writeAndFlush(String cmd);      // 3  write now (paced), never waits for a reply
        void addCommend(String cmd);         // 4  queue: paced, waits for the ACK, retries
        void writeFile(String path);         // 5
        boolean writeBytes(in byte[] data);  // 6
        void clearCommend();                 // 7  empty the queue
        void setConnectMaxNum(int n);        // 8
        void setSendMaxNum(int n);           // 9  retries per queued command (default 3)
        void setMinDelay(int ms);            // 10 base gap between writes (default 80)
        void setDelayTimes(int n);           // 11 gap multiplier for delay keys (default 3)
        void addResponseCommend(String key, String ack); // 12 key = first 4 chars, e.g. "~RGF"
        void addDelayCommend(String key);    // 13 key gets minDelay x delayTimes after it
        void close(boolean clear);           // 14 closes the port for EVERY client
    }

    // ISerialServiceListener.aidl
    package com.example.lxf.laucher2;

    interface ISerialServiceListener {
        void onReceiveNormalData(String frame);   // 1
        void onReceiveErrorData(String text);     // 2
        void onSendData(String cmd, boolean ok);  // 3
        void onConnectSuccess();                  // 4
        void onConnectFail(int code);             // 5
        void onConnectError();                    // 6
        void onClose();                           // 7
    }
    ```

*   **Caveats** **[RE]**:
    1. All clients share one send queue and one ACK context: a reply is matched against whichever command any client wrote last.
    2. `setMinDelay`, `setDelayTimes`, `addResponseCommend` and `addDelayCommend` change global tables, for every client, until the launcher process restarts; `setSendMaxNum` and `setConnectMaxNum` last until the service reopens the port.
    3. Every received frame is delivered to every registered client.
    4. Do not call `close(...)` to disconnect: it closes the port for all clients. Call `unRegisterListener` and unbind instead.
    5. All calls are synchronous, in both directions: the launcher waits for each of your listener callbacks to return, so keep them short.
    6. When the port cannot be opened, the launcher shows its own system dialog; clients receive no `onConnectFail`.

---

## 2. Go Board Hardware Layout & Coordinate System

The board features a 19x19 physical LED/sensor grid, two turn indicator LEDs, and two physical buttons for clock/timer functions. The turn indicators are RGB LEDs whose default colours are green (top) and white (bottom) **[verified]**. On the board's surface the top indicator is outlined by a black circle and the bottom one by a white circle **[verified]**.

*   **Coordinate Rules:** The protocol uses a **1-based index**, numbered from **Right-to-Left, Top-to-Bottom**.
*   **Padding:** Coordinate values must **always be zero-padded to 3 digits** in commands (e.g., `001`, `019`, `361`). The board accepts an unpadded position, but it reads the colour and mode fields at fixed character positions, so every later field shifts by one character: `~SHP19,r255g000b000,1#` lights the point visibly dimmer than `~SHP019,r255g000b000,1#`, because red is read as 55, and `~TLO19,r000g255b000,2#` loses its mode and switches both turn indicators off **[verified]**.
*   **Range:** Positions follow the active board size and are not range-checked. After `~BOD13#`, `~SHP181` (beyond 169) is drawn as if a 14th row existed, on the frame line below the 13x13 area **[verified]**.

### 2.1 Dynamic Board Sizing (`BOD` Commands)
The board dynamically alters its logical coordinate system and `SDA` payload length for smaller board sizes. A bounding box of dim green LEDs (RGB 5, 26, 4 **[verified]**) is illuminated on the physical lines just outside the playing area.

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

#### Other Board Sizes
Firmware 121 accepts `~BOD<nn>#` with exactly two digits for nn = `04`, `05`, `06`, `07`, `08`, `09`, `10`, `11`, `12`, `13`, `15` and `19` (16 to 361 points), answers `~GBS<nn>#` and draws the frame around the centred nn x nn area (19x19 has no frame) **[verified]**. Any other value selects 19x19 without a reply but leaves the previous frame lit; clear it with `~RGC#` **[verified]**. Genuine Izis apps use only 19, 13 and 09 **[RE]**.

#### Custom Frame Colour (`~BSC`)
`~BSC<nn>R<RRR>G<GGG>B<BBB>#` works like `~BOD<nn>#` but draws the frame in the given colour, e.g. `~BSC13R005G026B004#` (the default colour); the values are read at fixed character positions and the letters are not checked (lower case works); the reply is `~GBS<nn>#` **[verified]**. Blue at 255 looks clearly less bright than red or green at 255 **[verified]**. Izis apps do not use it **[RE]**.

#### Power-On State
The board starts in 19x19 with auto-report on, and it does not keep `~BOD` or `~CTS` settings across a power cut **[verified]**. After a restart it sends `~GBS19#` and a full `~SDA...#` without being asked (seen after a firmware-update restart) **[verified]**. The launcher sends `~CTS1#` and `~BOD19#` at boot only after a successful online update check **[verified]**, so do not rely on it to reset the board.

---

## 3. Protocol Instruction Set

### 3.1 Hardware Constraints & Timing Model
1. **Packet Framing:** Commands start with `~` and terminate with `#`.
    * *Board side:* The board keeps one receive buffer that restarts at every `~` and ends at `#` **[RE]**. A frame with more than 370 characters before `#` or with an unknown code is dropped without any reply **[verified]**, and so is a frame that fails the code's format check **[RE]** (`~HOTA` is an exception, section 3.4). The board never echoes the command it received **[verified]**.
    * *App side:* Izis apps extract packets with the regex `~?[A-Z]{3}[^~#]*#`. Packets containing characters outside `[A-Za-z0-9~#.,]` are not dropped: they are passed on as error data, and ACK matching still runs on them **[RE]**. Replies can arrive split across several reads (a full `~SDA` came as two TCP chunks through a Wi-Fi bridge) **[verified]**, so buffer received text until `#`.
2. **Baseline Pacing Delay:** Izis apps keep at least **80 ms** between the *starts* of consecutive writes, waiting before the next write rather than after each command; the bundled serial library caps each such wait at 300 ms (the main Go app's copy does not) **[RE]**. On the board, a complete frame waits for the board's next internal timer tick (every 45.1 ms) and then for its main loop, which takes at most one frame per scan step; a frame is lost when the next frame starts arriving before it was taken **[RE]**. Measured through a Wi-Fi serial bridge, with 10 trials per gap between write starts: after a short frame, a second short frame was lost in 10, 8, 5 and 1 trials at 0, 10, 20 and 30 ms and never from 40 ms on; after a full 366-byte `~SAR` frame (32 ms on the line) it was lost in every trial up to 30 ms and in 9, 9, 8, 5 and 3 trials at 40, 50, 60, 70 and 80 ms **[verified]**. The longer window after `~SA*` fits the time the board needs to apply the frame and redraw the matrix, during which it takes no serial input **[inferred]**. So 80 ms between write starts is enough after short frames, but not after `~SA*` frames.
    * **Recommended:** wait for each command's reply before sending the next: the board replies only after it has finished the command, including its LED updates **[RE]**. This matters most after `~SA*` frames: wait for `~ALS#` **[verified]**. For commands without a reply, leave at least 80 ms plus the frame's own transmission time (87 µs per character) before the next write **[inferred]**.
3. **Extended Render Delay:** Genuine Izis apps wait **240 ms** after `~RGC#` and `~FLL#` **[RE]**. `~RGF#` gets 240 ms (and an ACK wait for `~SIC#`) only where the main Go app has registered it, in the launcher's shared service; elsewhere it gets 80 ms and no ACK wait **[RE]**; using 240 ms after it as well is the safe choice **[inferred]**. The board cannot receive serial input while it writes LEDs (about 0.6 ms per matrix row, about 11 ms for a full-matrix update), while it saves settings (`~ADJ#`, `~SEP`), and while it loads its calibration after a restart **[RE]**; bytes arriving then are lost.
4. **Retry & Timeout Profile:** Izis apps wait **500 ms** for the ACK and resend up to **3 times** (4 writes in total), then drop the command silently **[verified]**. Commands without an ACK (e.g. `~FLL#`, `~AWO#`) are sent fire-and-forget **[RE]**. Only queued commands wait for an ACK; Izis apps also write some commands directly, paced but without waiting **[RE]**.
5. **Reply Latency:** Measured on a PC through a Wi-Fi serial bridge, replies arrived 20-50 ms after short commands and about 140 ms after a full 366-byte `~SAR` frame **[verified]**, which fits the timer tick above.
6. **After a Restart:** After power-on, a firmware update or a crash, the board loads its calibration for about 16 s **[inferred]** and ignores input until it sends its unprompted `~GBS19#` and `~SDA...#` (section 2.1). Wait for that frame before sending commands.
7. **Color Rendering:** The matrix LEDs are standard RGB (no dedicated White diode). The board's built-in colours use low values (e.g. palette green 0, 150, 0; indicator green 0, 30, 0) **[verified]**; full-scale values such as 255 are much brighter **[verified]**. Mixed dim colors may appear washed out. Developers should test RGB values on physical hardware to ensure contrast.

### 3.2 System & Sensor Configuration

| Command | Expected ACK | Basis | Description |
| :--- | :--- | :--- | :--- |
| `~BOD19#` | `~GBS19#` | [verified] | Configure board dimension and payload mode to 19x19. |
| `~BOD13#` | `~GBS13#` | [verified] | Configure board dimension and payload mode to 13x13. |
| `~BOD09#` | `~GBS09#` | [verified] | Configure board dimension and payload mode to 9x9. Other sizes: section 2.1. |
| `~STA#` | `~SDA<data>#` | [verified] | Query full board state. `<data>` length matches active `BOD` mode (361, 169, or 81 chars). `0`=Empty, `1`=Black, `2`=White. |
| `~CTS1#` | `~UDS1#` | [verified] | Enable auto-reporting (board emits `~SDA...#` asynchronously on stone changes). |
| `~CTS0#` | `~UDS0#` | [verified] | Disable auto-reporting. |
| `~GVE#` | `~VERxxx#` | [verified] | Query MCU firmware version (`~VER121#` on the tested board). Izis apps send it with the normal 500 ms ACK wait and retries; the main Go app's 300 ms timer only falls back to its cached version **[RE]**. |
| `~GSV#` | `~FJX0.xx#` | [verified] | Query the stone-detection separator (分界线, *fēnjièxiàn*, "dividing line") set by `~SEP`; `~FJX0.32#` on the tested board. 0.32 is used when no valid value is stored **[RE]**. |
| `~SEP<nn>#` | `~SSS#` | [verified] | ⚠️ Set the separator to nn/100 (exactly two digits, e.g. `~SEP32#` = 0.32, `~SEP15#` = 0.15). **Stored permanently** (survives power cuts) **[verified]**. A point reads empty while its sensor voltage stays within ± separator of its calibrated empty-board value, black below that band and white above it **[RE]**. |
| `~ADJ#` | `~AEN#` | [verified] | ⚠️ Calibrate: stores the latest reading of every point (an average of 20 samples) as its empty-board value, **permanently** **[RE]**. **Board must be completely empty**; check with `~REQ#` first. Takes about 40 s, during which button presses are lost **[verified]**; serial input is presumably lost too **[RE]**: send nothing until `~AEN#` (use a timeout of at least 60 s) and do not power off. |
| `~REQ#` | `~DAT...#` | [verified] | Read the sensor voltage of every point: one frame `~DAT1b<v>w<v>,2b<v>w<v>,...,361b<v>w<v>#`, one decimal, `b` and `w` always equal. On the tested board an empty point read about 1.5 V, a black stone about 0.4 V and a white stone about 2.5 V, jittering by 0.1 **[verified]**. Read-only **[RE]**; useful for choosing a separator. |
| `~GBS#` | `~BHZ<n>#` | [verified] | Reads one stored byte that `~WBS<d>#` writes **[RE]**; the tested board answered `~BHZ255#` **[verified]**, the value of a byte that was never written **[inferred]**. Meaning unknown, not used by Izis apps **[RE]**. Not to be confused with the `~GBS<nn>#` reply of `~BOD`: the firmware uses the same three letters for both **[RE]**. |
| `~WBS<d>#` | (None) | [RE] | ⚠️ Writes that byte permanently. Do not use. |

> **Architecture Note on Move Detection (`CTS1` vs. `CTS0`):**
> The board powers up with auto-reporting on **[verified]**. Izis apps differ **[RE]**: the Go and tsumego apps send `~CTS1#` when they connect; the online-platform connector sends `~CTS0#`, requests `~STA#` itself and restores `~CTS1#` on exit; Fox Go sends `~CTS1#` and then `~STA#` when a board view opens. Auto-reporting pauses for a few scan cycles after `~BOD` with a size other than 19, `~BSC`, `~SA*`, `~RL*` and `~AWO#` **[RE]**. Both approaches work:
> * **Auto-reporting (`~CTS1#`):** the board reports every change at once, so the app can flag a misplaced or disturbed stone immediately, without waiting for a button press. An app can act on each report as it arrives, without a debounce filter, if its cues do not repeat: one alarm per new error, and a reminder only after a few seconds without change **[verified]**.
> * **Polling (`~CTS0#`):** the app queries `~STA#` only on a clock button release (`~BKY#` / `~WKY#`). This is simpler to implement and avoids sensor jitter and serial/TCP traffic, but misplaced stones are noticed only at the next button press.

**Unsolicited frames from the board:**

| Frame | Basis | Meaning |
| :--- | :--- | :--- |
| `~SDA<data>#` | [verified] | Auto-report of the board state (same format as the `~STA#` reply). |
| `~GBS19#` + `~SDA...#` | [verified] | Sent after a restart (section 2.1). |
| `~ILL#` | [RE] | The MCU firmware crashed and is restarting. |
| `~24C32 Check Failed!#` (repeated) | [RE] | The board's settings memory failed its start-up check; the board does not start normally. |

The board accepts no commands for about 16 s after a restart, until it sends `~GBS19#` **[inferred]** (section 3.1).

### 3.3 Hardware Indicator LEDs
The top and bottom turn indicators are RGB LEDs **[verified]**. `~LED` switches between their default colours; `~GLC` sets any colour. `~LED` and `~GLC` overwrite each other's effect.

| Command | Expected ACK | Basis | Description |
| :--- | :--- | :--- | :--- |
| `~LED11#` | `~LOS#` | [verified] | Turn **ON Top Green** (RGB 0, 30, 0), turn OFF Bottom. |
| `~LED21#` | `~LOS#` | [verified] | Turn **ON Bottom White** (RGB 10, 10, 10), turn OFF Top. |
| `~LED10#` or `~LED20#` | `~LOS#` | [verified] | Turn OFF both indicators (also when they were lit by `~GLC`). |
| `~GLC1R<RRR>G<GGG>B<BBB>#` | `~LOS#` | [verified] | Set the **top** indicator to any colour, e.g. `~GLC1R255G000B000#` = red. The bottom indicator is left as it is, so both can be lit. Letters may be lower case. |
| `~GLC2R<RRR>G<GGG>B<BBB>#` | `~LOS#` | [verified] | Set the **bottom** indicator to any colour. |

Because the `~LED` colours are only (0, 30, 0) and (10, 10, 10), full-scale `~GLC` colours are much brighter **[verified]**; `~GLC1R000G030B000#` and `~GLC2R010G010B010#` reproduce the `~LED` colours **[verified]**. Izis apps do not use `~GLC` **[RE]**. `~TLO` also sets the indicators (section 3.4).

### 3.4 Single & Batch LED Target Commands
Target positions must always be zero-padded to 3 digits (e.g., `001`, `081`).
The RGB channels themselves must also be zero-padded to 3 digits (e.g., `r000g255b000`, not `r0g255b0`). The board reads every field at a fixed character position (section 2) **[verified]**.

A lit point cannot be seen under a stone: a black or a white stone blocks the light of a `~SHP` point even at full-scale red, and of `~SAR` points **[verified]**.

| Command Format | Expected ACK | Basis | Description |
| :--- | :--- | :--- | :--- |
| `~SHP<pos>,r<R>g<G>b<B>,<m>#` | `~HCS#` | [verified] | **Single LED (Destructive):** Lights coordinate `<pos>` and switches off the previous `~SHP` or `~TLO` point. The mode `<m>` is ignored by firmware 121: `0`, `1`, `2` and `9` look identical **[verified]**; Izis apps send `1` or `2` **[RE]**. |
| `~TLO<pos>,r<R>g<G>b<B>,<m>#` | `~TLS#` | [verified] | **Sync LED:** Lights `<pos>`, switches off the previous `~SHP` or `~TLO` point, and sets the turn indicators: `m` = `0` both off, `1` top only, `2` bottom only, `3` both on; other values leave the indicators unchanged **[verified]**. The indicators show their default `~LED` colours whatever the point colour. |
| `~HOTA<p1>r<R>g<G>b<B>B<p2>...C<p3>...D<p4>...N<c>#` | `~HSM#` | [verified] | **Batch LED (Non-Destructive):** Adds up to 4 LEDs without clearing existing lights. **All 4 segments (A, B, C, D) must be present**, 16 characters each, because the count `<c>` is read at a fixed position; exactly the first `c` segments (`1`–`4`, starting with A) are drawn. Unused segments must be padded with dummy data; their content is not checked **[RE]**. Izis apps always send all four segments, repeating point A for unused ones **[RE]**. |

*Batch Example:* `~HOTA001r255g000b000B019r000g255b000C001r000g000b000D001r000g000b000N2#` renders points A and B **[verified]**. A shorter frame such as `~HOTA183r000g000b255N1#` does not draw its points **[verified]**; the board still answers `~HSM#` and draws the points of the previous complete `~HOTA` again, even after `~RGC#` (none after power-on) **[verified]**.

> **Shared single-point slot:** `~SHP` and `~TLO` remember one "current point". Each new `~SHP` or `~TLO` switches that point off first, even if a later `~HOTA` frame **[verified]** or `~SA*` frame **[RE]** repainted it. Use `~HOTA` or `~SA*` for points that must stay lit **[inferred]**.

### 3.5 Full Matrix LED Render Commands

| Command | Expected ACK | Delay Rule | Basis | Description |
| :--- | :--- | :--- | :--- | :--- |
| `~RGC#` | `~ALC#` | **240 ms** | [verified] | **Clear All:** Extinguishes all matrix LEDs, including boundary frames; the turn indicators stay as they are. |
| `~RGF#` | `~SIC#` | **240 ms** (recommended, section 3.1) | [verified] | **Clear Inner:** Extinguishes grid LEDs while preserving the active `BOD` boundary frame, including frame cells that a point had overwritten. |
| `~FLL#` | (None) | **240 ms** | [verified] | **Fill:** Illuminates the entire matrix in dim white, RGB (15, 15, 15). No reply. |
| `~SAR<361_chars>#` | `~ALS#` | **80 ms** | [verified] | **Matrix Write, full palette:** 361-character array (`0`=Off, `1`–`9`=Palette indices). |
| `~SA[L\|M\|W]<361_chars>#` | `~ALS#` | **80 ms** | [verified] | **Matrix Write, two colours:** only `0` (off), `1` and `2` are drawn; digits `3`–`9` leave that LED as it was **[verified]** (clear with `~RGC#` first if needed). |

The payload always has 361 characters in 19x19 order, whatever the `BOD` size **[RE]**.

**Palette (RGB values set by firmware 121) [verified]:**

| Digit | `~SAR` | `~SAL` | `~SAM` | `~SAW` |
| :--- | :--- | :--- | :--- | :--- |
| `0` | off | off | off | off |
| `1` | 0, 150, 0 (green) | 0, 70, 0 | 0, 68, 0 | 0, 45, 0 |
| `2` | 50, 50, 50 (white) | 40, 40, 70 | 45, 45, 45 | 30, 30, 30 |
| `3` | 0, 70, 0 (green) | unchanged | unchanged | unchanged |
| `4` | 40, 40, 70 (bluish white) | unchanged | unchanged | unchanged |
| `5` | 255, 0, 0 (red) | unchanged | unchanged | unchanged |
| `6` | 238, 20, 147 (magenta) | unchanged | unchanged | unchanged |
| `7` | 255, 110, 180 (pink) | unchanged | unchanged | unchanged |
| `8` | 0, 80, 80 (teal) | unchanged | unchanged | unchanged |
| `9` | 33, 33, 24 (warm white) | unchanged | unchanged | unchanged |

On the board, `1`, `3` and `8` are hard to tell apart (green), and so are `2`, `4` and `9` (white) **[verified]**; for clearly distinct colours use `1`, `2`, `5`, `6` and `7`, or explicit RGB values with `~SHP`, `~TLO` or `~HOTA`.

> **Brightness Hierarchy:**
> By the values above, green is brightest under `~SAR` (150), then `~SAL` (70) and `~SAM` (68), nearly equal, then `~SAW` (45); white is (50, 50, 50) under `~SAR`, 45 under `~SAM`, a bluish (40, 40, 70) under `~SAL` and 30 under `~SAW` **[verified]**. The main Izis Go app's LED level setting maps 150 to `~SAM`, 100 to `~SAW` and other values to `~SAL` **[RE]**.

#### ⚠️ Power Rule in Izis Apps
The main Go app and the tsumego app switch their stone display to `~SAW` once more than 50 moves are recorded in the game; since every stone on the board is in the move list, every frame with more than 50 lit stones is sent as `~SAW` **[RE]**. Whether this rule protects the power supply is not known **[inferred]**; other Izis apps, including Fox Go, send full frames with `~SAR` without such a rule **[RE]**. Third-party applications that render dense matrices (e.g., KataGo territory ownership or heatmaps) may prefer the dimmer tiers to be on the safe side **[inferred]**.

> **Sub-Board Boundary Notice for Matrix Writes:**
> All `~SA*` frames cover the entire 361-LED matrix. When running in 13x13 or 9x9 mode, a `0` on a frame cell switches that part of the green boundary frame drawn by `~BODxx#` off. Genuine Izis apps therefore pre-populate the perimeter indices within the 361-character payload with palette colour `1` (green; some apps use `5` or `3`) **[RE]**. Under `~SAL`/`~SAM`/`~SAW`, a digit from `3` to `9` on the frame cells leaves the existing frame as it is **[inferred]**.

### 3.6 Graphic & Audio Feedback

| Command | Expected ACK | Basis | Description |
| :--- | :--- | :--- | :--- |
| `~RLO#` | `~DSC#` | [verified] | Displays green (RGB 0, 100, 0) **"OK / Circle"** matrix icon. Izis apps send it fire-and-forget **[RE]**. |
| `~RLT#` | `~DSC#` | [verified] | Displays green (RGB 0, 100, 0) **"Checkmark / V"** matrix icon. Izis apps send it fire-and-forget **[RE]**. |
| `~RLW#` | `~DSC#` | [verified] | Displays red (RGB 100, 0, 0) **"Cross / X"** matrix icon. Izis apps send it fire-and-forget **[RE]**. |
| `~AWO#` | (None) | [verified] | Standard prompt / error sound: two short beeps **[verified]**, two pulses of about 45 ms, 135 ms apart from start to start, about 270 ms in all **[RE]**. Fire-and-forget. |

`~RLT#` and `~RLW#` draw their icon over the LEDs as they are lit: the board sets the green (`~RLT#`) or red (`~RLW#`) value of each icon point to 100 and keeps its other two values, so a point that is already lit shows a mixed colour (a full-white point under the check reads 255, 100, 255), and leaves every other LED as it is **[verified]**. The board never switches an icon off: it stays until a frame rewrites those LEDs; a `~SA*` frame removes it **[verified]**, as do `~RGC#` and, for one point, `~SHP` **[RE]**. The check covers positions 129, 147, 165, 183 and 201, then 181, 161, 141, 121, 101, 81 and 61: a check mark upright as seen from the bottom edge **[verified]**. The cross covers 90 to 234 in steps of 18 and 82 to 242 in steps of 20, crossing at 162 **[verified]**. The board answers `~DSC#` once the icon is drawn **[RE]**.

`~AWS#` and `~AWT#` (countdown beep and time-out alarm in Izis apps) are not accepted by firmware 121 (section 3.9).

### 3.7 Hardware Button Events
Hardware button events are emitted upon key release **[verified]**.

| Event | Physical Interaction | Name in Izis Apps | Description |
| :--- | :--- | :--- | :--- |
| `~BKY#` | Top Button Short Press | `clickBlack` | Emitted immediately on button release. |
| `~BTK#` | Top Button Long Press | `doubleClickBlack` | Labeled as double-click in Izis apps, but triggers on key release after holding for about 1.2 seconds. |
| `~WKY#` | Bottom Button Short Press | `clickWhite` | Emitted immediately on button release. |
| `~WTK#` | Bottom Button Long Press | `doubleClickWhite` | Labeled as double-click in Izis apps, but triggers on key release after holding for about 1.2 seconds. |

*   Two presses closer than about 200-250 ms produce a single event, on the release of the second press **[verified]**.
*   A 1.0 s hold gives the short-press event and a 1.5 s hold the long-press event; holding the second press of a merged pair still gives the short-press event **[verified]**.
*   Timing **[RE]**: the board samples each button every 45.1 ms. A press counts after 2 samples in a row read it down (a press shorter than about 45 ms can be missed), and the event is sent after 2 samples read it up again (45-90 ms after the release). A long press needs about 1.2 s of holding. Two presses merge when the button goes down again before 2 "up" samples: always for a gap under 45 ms, never for a gap over 90 ms.
*   Izis apps also handle `~BDK#` and `~WDK#` (like `~BKY#`/`~WKY#`) and recognise, without acting on them, `~SIN`, `~CMD`, `~PAB`, `~PAW`, `~REB`, `~REW`, `~RNB`, `~RNW`, `~GIB`, `~GIW` and `~ANA` **[RE]**. The tested board never sent any of these, with any press pattern or during play **[verified]**, and firmware 121 has no code that could send `~BDK#` or `~WDK#` **[RE]**.

### 3.8 ⚠️ Commands That Change the Board Permanently

> **[DANGER] Never send `~UPD#`.** It starts an MCU firmware update: the board restarts into its bootloader without a reply, and the bootloader waits for a new firmware image and talks in plain-text frames such as `~pleas send new program!#` **[verified]**; before restarting, the firmware stores an update flag in its settings memory **[RE]**. How to recover if no valid image follows is unknown. Because `/dev/ttyS1` is world-writable (section 1.1), any app can send this command. The replies `~CRCYES#`, `~CRCERR#`, `~CRY#` and `~CRE#` that Izis apps send belong to the update procedure; never send them either.

> **[DANGER] Launcher firmware update dialog.** On the UW-M527, a double tap on the firmware-version row of the launcher's device-info screen opens a firmware update dialog **[verified]**. Its confirm button would flash a firmware image built for a different model (kids edition) **[RE]**, which most likely lacks the separator, sensor-readout and calibration commands (`~GSV#`, `~REQ#`, `~ADJ#`, `~SEP`) **[inferred]**. Do not confirm it.

**[RISKY] Settings memory:** `~ADJ#` (calibration), `~SEP<nn>#` (separator) and `~WBS<d>#` write the board's non-volatile memory and survive power cuts (tested for the separator **[verified]**; `~ADJ#` and `~WBS` **[RE]**). A calibration with stones on the board, or a badly chosen separator, makes stone detection unreliable until the board is recalibrated empty **[inferred]**. Note the value of `~GSV#` before changing the separator; the tested board read 0.32 (`~SEP32#`) **[verified]**.

### 3.9 Codes in Izis Apps That Firmware 121 Ignores
Genuine Izis apps send these codes **[RE]**, but firmware 121 does not act on them; they are probably meant for older firmware **[inferred]**. Do not rely on them.

| Code | Use in Izis apps | Firmware 121 |
| :--- | :--- | :--- |
| `~CAL#` | Sent in the exit sequence of several apps, after the LED-off commands. | No reply, no visible effect **[verified]**. |
| `~QDB<pos>,r<R>g<G>b<B>,1#`, `~RGW#` | Hint points, sent in batches followed by `~RGW#`. | No reply, no effect **[verified]**. |
| `~SAU<361_chars>#`, `~SAN<361_chars>#` | Matrix writes labelled ultra-low and lowest brightness. | No reply, no effect **[verified]**. |
| `~AWS#`, `~AWT#` | Countdown beep (once per second in the last 10 s of byo-yomi, only on Android below 8.0) and time-out alarm. | Not accepted **[RE]**; no audible output **[verified]**. |
| `~SJD...`, `~SCS...` | The factory test app sends per-point calibration values as `~SJD`; it builds `~SCS` frames but never sends them (meaning unknown). | Not accepted **[RE]**. Do not use. |
