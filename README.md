# Scrcpy Deck

Scrcpy Deck is a Windows desktop controller for Android screen mirroring, camera capture, microphone forwarding and USB input. Its PySide6 and Qt Quick interface manages devices and session settings. ADB handles device communication, and scrcpy opens the mirror in its own window.

![Scrcpy Deck connection workspace](assets/preview.png)

## Run on Windows

For a source checkout, use 64-bit Python 3.11 or later. The application has been run with Python 3.12 on Windows.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python main.py
```

Extract the complete Windows x64 scrcpy distribution into `runtime` beside `main.py` to run device sessions from source. Deck also looks beside the application and on `PATH`. Keep `scrcpy-server` and the upstream DLLs with their executable. Scrcpy Deck uses scrcpy 5.0.1. [Official scrcpy download](https://github.com/Genymobile/scrcpy/releases/tag/v5.0.1)

## Connect a phone

| Workflow | In Scrcpy Deck |
| --- | --- |
| USB | Enable USB debugging on the phone, connect a data cable and accept its authorization prompt. Choose **Scan devices**. If several transports are available, select the intended one in the device card. Choose **Start session**. |
| USB-assisted Wi-Fi | Keep the cable attached and connect both devices to the same network. Choose **Get IP**, **Enable TCP/IP**, then **Connect Wi-Fi**. Unplug once the wireless transport is selected. |
| Android 11+ direct pairing | On the phone, open **Developer options → Wireless debugging → Pair device with pairing code**. Under **Pair with code**, enter its IP, pairing port and six-digit code. After pairing, enter the connection port from the main Wireless debugging screen or choose **Detect**. Choose **Connect**. Deck attempts to switch to port 5555 and verifies the selected transport. |
| Saved devices | Authorized transports appear in **Saved devices**. Edit their nicknames or Wi-Fi addresses, forget an entry, or choose **Connect & start**. If a wireless address has changed, search for the saved hardware identity on Wi-Fi or choose **Recover over USB**. The recovery reads the current IP before restarting the phone's ADB daemon and retains the nickname. |
| Authorization problems | Open **Help center** for manufacturer-specific instructions. **Stop ADB server** affects other clients of the host daemon. **Reset connections** also removes the current user's ADB keys and restarts the daemon. The app confirms both actions. |

## Configure a session

Open **Quick settings** with the gear or **Ctrl+,**. The Screen, Camera and Mic tabs share their settings with the full pages. **Apply & close** selects the active tab as the capture source. **F5** rescans devices.

- **Advance settings** controls capture source, screen quality, video and audio codecs, mirror render driver, screen-audio muting, orientation, window modes, camera parameters, device behaviors, and recording & diagnostics.
- **Camera** supports lens discovery, aspect ratio, rotation, maximum size, camera FPS, zoom and torch. An explicit lens takes precedence over front/back selection. The phone and scrcpy version determine which capture combinations are available.
- **Input modes** include the original mirror-and-control behavior, explicit UHID keyboard/mouse input and USB OTG control-only mode. OTG can start with a USB phone that has no ADB authorization. Windows USB driver access is required.
- **Recording** writes timestamped MP4 files under the user's Videos folder in `Scrcpy Deck`. The console includes the full recording path. Close the scrcpy window to finish the recording.
- **Console** streams stdout, stderr, exit codes and troubleshooting hints. Run commands in the application directory with the Windows command shell, copy the log or clear it. External debug mode opens scrcpy in its own console.
- **Help center** includes USB setup checklists for eight manufacturer groups, the original tutorials, FAQs, downloads and creator support.

## Settings and upgrades

The default profile is `%LOCALAPPDATA%\Scrcpy Deck\config.json`. On first run, Deck imports an existing v4 `config.json` beside the source or executable. It preserves all 27 settings, saved device records, nicknames and unknown JSON fields. The old file remains available to the previous frontend. An existing per-user profile takes precedence. Use the `SCRCPY_DECK_PROFILE_DIR` environment variable to run with an isolated profile.

Changes are saved after a short debounce and flushed on normal exit. Writes replace the profile atomically. A per-profile lock prevents two desktop instances from overwriting each other. Pairing codes are transient and are sent to ADB through stdin.

## Application structure

| Location | Responsibility |
| --- | --- |
| `main.py`, `assets.py` | Qt startup, profile locking, fonts, resources and executable discovery |
| `qml/` | Responsive application shell, shared controls, five pages and settings dialogs |
| `controller.py` | Observable application state, UI-thread transitions and serialized background device operations |
| `adb.py`, `device_names.py` | ADB commands, mDNS, per-transport identity caching and Android marketing names |
| `workflows.py`, `library.py` | Verified wireless connection, recovery, target selection and saved-record merging |
| `scrcpy_command.py`, `processes.py` | Argument construction, session launch, subprocess streaming and exit reporting |
| `config.py`, `console.py` | Backwards-compatible settings store and a bounded, event-driven log model |
| `data/` | Device name mappings, manufacturer guides, FAQs and video links |

Device scans retrieve the full Android property set in one subprocess for a newly authorized transport. Later scans reuse its identity until the transport changes. QML loads the selected page on demand. Log updates wake the UI only when there are new lines. The console retains the latest 2,000 lines.

## Windows verification

The migration was exercised on Windows 11 with a Redmi 12 5G running Android 13.

| Check | Observed result |
| --- | --- |
| Wired sessions | USB mirroring, read-only viewing, UHID mirroring, MP4 finalization, microphone mode and the external debug console completed. OTG selected the phone and its control window closed cleanly. Physical keystrokes and mouse input were outside that check. |
| Camera | Six lenses enumerated. Front, rear and explicitly selected lens sessions ran. The selected-lens test used a size limit, frame rate, rotation, aspect ratio and zoom. |
| Wireless | USB-assisted connection, live pairing-code exchange, mDNS port discovery, transition to port 5555, saved-device launch and USB recovery after a failed reconnect succeeded. The phone returned to authorized USB operation afterward. |
Three source launches per frontend on the same machine gave a median of **1.97 s** for CustomTkinter and **0.57 s** for Qt from process start to a visible window responding to a Windows message. Median process working set three seconds later was **63 MiB** and **172 MiB**, respectively. Qt reported a threaded Direct3D 11 render loop. These are machine-specific observations.

## License

Scrcpy Deck is distributed under GPLv3. The bundled runtime includes upstream scrcpy and ADB components. Nunito and Cascadia Code carry their respective font notices. [Project license](LICENSE) · [Font notices](packaging/licenses)
