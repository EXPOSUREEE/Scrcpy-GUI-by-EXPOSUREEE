"""Qt-facing state. Workers return values; only the GUI thread mutates the model."""
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
from threading import Event, Thread
import urllib.request

from PySide6.QtCore import QObject, Property, QStandardPaths, QTimer, Signal, Slot, Qt
from PySide6.QtGui import QGuiApplication

from adb import AdbManager, DeviceError, HIDDEN
from assets import APP_DIR, RESOURCES, VERSION, child_environment, executable, get_writable_runtime
from config import DEFAULTS, SettingsStore, normalize
from console import ConsoleModel, infer_fix_hint
from library import address, endpoint, merge_devices
from processes import ProcessRunner
from scrcpy_command import build_scrcpy_command
from updater import (
    download_installer,
    extract_scrcpy_archive,
    find_latest_scrcpy_release,
    find_latest_update,
    get_installed_scrcpy_version,
    launch_installer_and_restart,
)
from workflows import Connections


class Deck(QObject):
    stateChanged = Signal()
    settingsChanged = Signal()
    savedChanged = Signal()
    recoveryOffered = Signal(int)
    paired = Signal()
    _completed = Signal(object, object, str)
    _processExited = Signal(str, int)
    _updateFound = Signal(object)
    _updateProgress = Signal(int)
    _updateStatusChanged = Signal(str, str)
    _scrcpyChecked = Signal(object)
    _scrcpyProgress = Signal(int)
    _scrcpyStatusChanged = Signal(str, str)

    def __init__(self, profile=None, app_dir=APP_DIR):
        super().__init__()
        self.app_dir = Path(app_dir)
        profile = profile or Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)) / "config.json"
        self.store = SettingsStore(profile, self.app_dir / "config.json")
        self.logs = ConsoleModel()
        self.adb = AdbManager(executable("adb"), RESOURCES, self.logs.log)
        self.scrcpy = executable("scrcpy")
        self.scrcpy_version = get_installed_scrcpy_version(self.scrcpy) or "5.0.1"
        self.env = child_environment(self.adb.exe, self.scrcpy)
        self.stop = Event()
        self.wireless = Connections(self.adb, self.stop)
        self._closed = False
        self._update_info = None
        self._update_cancel = Event()
        self._scrcpy_info = None
        self._scrcpy_cancel = Event()
        self._state = dict(status="Ready", error="", busy=False, devices=[], serial="",
                           tcpSerial="", port="", lenses=["Default"], recovering=False,
                           update="", updateStatus="", updateProgress=0, updateError="",
                           updateSize=0, sessions=0,
                           scrcpyVersion=self.scrcpy_version,
                           scrcpyLatest="",
                           scrcpyStatus="",
                           scrcpyProgress=0,
                           scrcpyError="")
        self._guides = json.loads((RESOURCES / "data/guides.json").read_text(encoding="utf-8"))
        self.runner = ProcessRunner(self.env, self.logs.log, self._processExited.emit)
        self._completed.connect(self._finish, Qt.QueuedConnection)
        self._processExited.connect(self._exited, Qt.QueuedConnection)
        self._updateFound.connect(self._on_update_found, Qt.QueuedConnection)
        self._updateProgress.connect(lambda p: self._change(updateProgress=p), Qt.QueuedConnection)
        self._updateStatusChanged.connect(self._on_update_status_changed, Qt.QueuedConnection)
        self._scrcpyChecked.connect(self._on_scrcpy_checked, Qt.QueuedConnection)
        self._scrcpyProgress.connect(lambda p: self._change(scrcpyProgress=p), Qt.QueuedConnection)
        self._scrcpyStatusChanged.connect(self._on_scrcpy_status_changed, Qt.QueuedConnection)
        self.timer = QTimer(self, interval=350, singleShot=True)
        self.timer.timeout.connect(self.save)
        self.logs.log("INFO", "Console ready.")
        if self.store.error:
            self._error(self.store.error)
        elif self.store.dirty:
            self.timer.start()

    @Property("QVariantMap", notify=stateChanged)
    def state(self):
        return self._state

    @Property("QVariantMap", notify=settingsChanged)
    def settings(self):
        return self.store.values

    @Property("QVariantList", notify=savedChanged)
    def saved(self):
        return self.store.saved

    @Property("QVariantMap", constant=True)
    def guides(self):
        return self._guides

    @Property(str, constant=True)
    def version(self):
        return VERSION

    def _change(self, **values):
        if any(self._state.get(k) != v for k, v in values.items()):
            self._state.update(values)
            self.stateChanged.emit()

    def _error(self, reason):
        self.logs.log("ERROR", reason)
        hint = infer_fix_hint(reason)
        if hint:
            self.logs.log("HINT", hint)
        self._change(status="Attention needed", error=str(reason))

    @Slot(str, "QVariant")
    def configure(self, key, value):
        if key not in DEFAULTS:
            return
        value = normalize(key, value)
        if self.store.values[key] != value:
            self.store.values[key] = value
            self.store.dirty = True
            self.settingsChanged.emit()
            self.timer.start()

    @Slot()
    def save(self):
        try:
            self.store.save()
        except OSError as exc:
            self._error(f"Settings could not be saved. {exc}")

    def _library_changed(self):
        self.savedChanged.emit()
        self.store.dirty = True
        self.timer.start()

    def _job(self, title, work, done, failed=None):
        if self._state["busy"] or self._closed:
            return
        self.stop.clear()
        self._change(status=title, error="", busy=True)
        def execute():
            try:
                result = work()
            except Exception as exc:
                if not self._closed:
                    self._completed.emit(failed, None, str(exc) or type(exc).__name__)
            else:
                if not self._closed:
                    self._completed.emit(done, result, "")
        Thread(target=execute, daemon=True).start()

    @Slot(object, object, str)
    def _finish(self, callback, result, error):
        if self._closed:
            return
        cancelled = self.stop.is_set()
        self._change(busy=False, recovering=False)
        if cancelled:
            self._change(status="Cancelled")
        elif error:
            self._error(error)
            if callback:
                callback(error)
        else:
            callback(result)

    def _scanned(self, devices, preferred="", launch=False):
        ready = [d.serial for d in devices if d.state == "device"]
        previous = self._state["serial"]
        saved_endpoint = self.settings["ip"] + ":5555"
        selected = next((s for s in [preferred, previous, saved_endpoint, *ready] if s in ready), "")
        if merge_devices(self.store.saved, devices):
            self._library_changed()
        if selected != previous:
            self._change(lenses=["Default"])
        self._change(devices=[asdict(d) for d in devices], serial=selected,
                     tcpSerial=self._state["tcpSerial"] if selected == previous else "",
                     status=f"{len(ready)} authorized device(s)" if ready else "Waiting for a device")
        if launch:
            if preferred in ready:
                self.launch()
            else:
                self._error("The saved device is unavailable. Connect it by USB and authorize this computer.")

    @Slot()
    def scan(self):
        self._job("Scanning devices…", self.adb.scan, self._scanned,
                  lambda _: self._change(devices=[], serial="", tcpSerial="", lenses=["Default"]))

    @Slot(str)
    def select(self, serial):
        if not self._state["busy"] and any(d["serial"] == serial and d["state"] == "device" for d in self._state["devices"]):
            self._change(serial=serial, lenses=["Default"], error="")

    @Slot()
    def getIp(self):
        serial = self._state["serial"]
        if serial:
            def found(ip):
                self.configure("ip", ip)
                self._change(status=f"Wi-Fi address found · {ip}")
            self._job("Reading Wi-Fi address…", lambda: self.adb.wifi_ip(serial), found)

    @Slot()
    def enableTcp(self):
        serial = self._state["serial"]
        if serial:
            self._job("Enabling TCP/IP…", lambda: self.adb.tcpip(serial),
                      lambda _: self._change(tcpSerial=serial, status="Port 5555 enabled. Connect over Wi-Fi."))

    @Slot(str, str)
    def pair(self, port, code):
        try:
            target = endpoint(self.store.values["ip"], port)
            if not re.fullmatch(r"[0-9]{6}", code):
                raise ValueError("Enter the six-digit pairing code shown on the phone.")
        except ValueError as exc:
            self._error(str(exc))
            return
        def done(_):
            self._change(status="Paired. Enter the connection port from Wireless debugging.")
            self.paired.emit()
        self._job("Pairing with phone…", lambda: self.adb.pair(target, code), done)

    @Slot()
    def detectPort(self):
        try:
            ip = address(self.store.values["ip"])
        except ValueError as exc:
            self._error(str(exc))
            return
        self._job("Looking up wireless port…", lambda: self.adb.discover(ip, self.stop),
                  lambda port: self._change(port=port, status=f"Discovered port {port}"))

    @Slot(str)
    def setPort(self, value):
        self._change(port=value)

    def _connected(self, result, launch=False):
        target, devices = result
        if ":" in target:
            ip, _, port = target.rpartition(":")
            self.configure("ip", ip)
            self._change(port=port)
        self._scanned(devices, target, launch)

    @Slot(str)
    @Slot(str, bool)
    def connectWifi(self, port, accept_embedded=False):
        try:
            target = endpoint(self.store.values["ip"], port, accept_embedded=accept_embedded)
        except ValueError as exc:
            self._error(str(exc))
            return
        self._job(f"Connecting to {target}…", lambda: self.wireless.connect(target), self._connected)

    @Slot(int)
    def connectSaved(self, index):
        if not 0 <= index < len(self.saved):
            return
        record = self.saved[index]
        serial = record.get("serial", "")
        if record.get("type") != "wireless":
            self._job("Finding saved device…", self.adb.scan, lambda items: self._scanned(items, serial, True))
            return
        if record.get("ip"):
            try:
                target = endpoint(record["ip"], serial.rsplit(":", 1)[1] if ":" in serial else "5555")
            except ValueError as exc:
                self._error(str(exc))
                self.recoveryOffered.emit(index)
                return
        else:
            target = serial
        self._job("Reconnecting saved device…", lambda: self.wireless.connect(target, hardware=record.get("hardware_serial", "")),
                  lambda result: self._connected(result, True), lambda _: self.recoveryOffered.emit(index))

    @Slot(int)
    def findSaved(self, index):
        if not 0 <= index < len(self.saved):
            return
        hardware = self.saved[index].get("hardware_serial", "")
        if hardware:
            def find():
                target = self.adb.resolve_device_by_serial(hardware, self.stop)
                return self.wireless.connect(target, hardware=hardware)
            self._job("Looking for the saved phone on Wi-Fi…", find,
                      lambda result: self._connected(result, True), lambda _: self.recoveryOffered.emit(index))

    @Slot(int)
    def recover(self, index):
        if not self._state["busy"] and 0 <= index < len(self.saved):
            record = self.saved[index].copy()
            def recovered(result):
                target, devices = result
                self.store.saved[index].update(serial=target, ip=target.partition(":")[0])
                self._library_changed()
                self._connected((target, devices), True)
            self._change(recovering=True)
            self._job("Waiting for the saved phone over USB…", lambda: self.wireless.recover(record), recovered)

    @Slot()
    def cancelRecovery(self):
        if self._state["recovering"]:
            self.stop.set()

    @Slot(int, str, str, result=bool)
    def editSaved(self, index, nickname, ip):
        if self._state["busy"] or not 0 <= index < len(self.saved):
            return False
        record = self.store.saved[index]
        if record.get("type") == "wireless" and ip != record.get("ip", ""):
            try:
                serial = record.get("serial", "")
                target = endpoint(ip, serial.rsplit(":", 1)[1] if ":" in serial else "5555")
            except ValueError as exc:
                self._error(str(exc))
                return False
            record.update(serial=target, ip=ip.strip())
        record["nickname"] = nickname.strip()
        self._library_changed()
        return True

    @Slot(int)
    def forget(self, index):
        if not self._state["busy"] and 0 <= index < len(self.saved):
            del self.store.saved[index]
            self._library_changed()

    @Slot(bool)
    def maintenance(self, reset):
        def done(_):
            self._scanned([])
            self._change(status="Connections reset. Authorize the phone again." if reset else "ADB server stopped.")
        self._job("Resetting connections…" if reset else "Stopping ADB…",
                  self.adb.reset if reset else lambda: self.adb.run(["kill-server"]), done)

    @Slot()
    def detectLenses(self):
        serial = self._state["serial"]
        if not serial:
            self._error("Select an authorized device to detect its cameras.")
            return
        def detect():
            cmd = [self.scrcpy, "-s", serial, "--list-cameras"]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                    timeout=15, creationflags=HIDDEN, env=self.env)
            output = result.stdout + "\n" + result.stderr
            self.logs.log("OUT", output)
            if result.returncode:
                raise DeviceError(output.strip() or "Lens scan failed")
            return ["Default", *[f"ID {n}: {desc}" for n, desc in re.findall(r"--camera-id=([^\s]+)\s*\(([^)]+)\)", output)]]
        def found(lenses):
            current = self.settings["camera_id"]
            if current not in lenses:
                self.configure("camera_id", next((x for x in lenses if x.startswith(f"ID {current}:")), "Default"))
            self._change(lenses=lenses, status=f"{len(lenses) - 1} camera lenses found")
        self._job("Detecting camera lenses…", detect, found)

    @Slot()
    def launch(self):
        s = self.settings.copy()
        serial = self._state["serial"]
        otg = s["source"] == "screen" and s["screen_mode"] == "OTG"
        if not serial and not otg:
            self._error("Select an authorized device before starting a session.")
            return
        if otg and serial and not any(d["serial"] == serial and d["transport"] == "usb" for d in self._state["devices"]):
            self._error("OTG requires a USB connection.")
            return
        try:
            if s["source"].startswith("camera") and s["camera_zoom"]:
                zoom = float(s["camera_zoom"])
                if not math.isfinite(zoom) or zoom <= 0:
                    raise ValueError("Camera zoom must be a positive number.")
            cmd = build_scrcpy_command(dict(s, device_serial=serial, scrcpy_exe=self.scrcpy))
            cwd = self.app_dir
            if "--record" in cmd:
                cwd = Path(QStandardPaths.writableLocation(QStandardPaths.MoviesLocation)) / "Scrcpy Deck"
                cwd.mkdir(parents=True, exist_ok=True)
                self.logs.log("INFO", f"Recording to {cwd / cmd[cmd.index('--record') + 1]}")
            self.runner.start(cmd, cwd, debug=s["debug_mode"])
            self._change(sessions=self._state["sessions"] + 1, error="", status="Starting scrcpy…")
        except (OSError, ValueError) as exc:
            self._error(f"scrcpy could not start. {exc}")

    @Slot(str)
    def runCommand(self, command):
        if command.strip():
            try:
                self.runner.start(command, self.app_dir, shell=True)
            except OSError as exc:
                self._error(str(exc))

    @Slot(str, int)
    def _exited(self, name, code):
        if self._closed:
            return
        self.logs.log("ERROR" if code else "INFO", f"{name} exited with code {code}.")
        if name == "scrcpy":
            self._change(sessions=max(0, self._state["sessions"] - 1))
            if code:
                self._error(f"scrcpy exited with code {code}. Open the console for details.")
            else:
                self._change(status="Session ended")

    @Slot(str)
    def copy(self, value):
        QGuiApplication.clipboard().setText(value)

    def _on_update_found(self, update):
        if self._closed:
            return
        if update:
            self._update_info = update
            version_str = update["version"]
            self.logs.log("INFO", f"Update available: Scrcpy Deck v{version_str}")
            self._change(
                update=version_str,
                updateStatus="available",
                updateProgress=0,
                updateError="",
                updateSize=update.get("size", 0),
            )
        else:
            self._update_info = None
            self._change(
                update="",
                updateStatus="",
                updateProgress=0,
                updateError="",
                updateSize=0,
            )

    def _on_update_status_changed(self, status, error=""):
        if self._closed:
            return
        self._change(updateStatus=status, updateError=error)

    @Slot()
    def checkForUpdates(self):
        if self._closed or self._state.get("updateStatus") == "downloading":
            return
        def check():
            try:
                update = find_latest_update(VERSION)
                if not self._closed:
                    self._updateFound.emit(update)
            except Exception as exc:
                self.logs.log("WARN", f"Could not check for updates: {exc}")
        Thread(target=check, daemon=True).start()

    @Slot()
    def installUpdate(self):
        if self._closed or not self._update_info:
            return
        if self._state.get("updateStatus") == "downloading":
            return
        self._update_cancel.clear()
        self._change(updateStatus="downloading", updateProgress=0, updateError="")

        def run_download():
            try:
                temp_dir = Path(tempfile.gettempdir()) / "ScrcpyDeckUpdate"
                temp_dir.mkdir(parents=True, exist_ok=True)
                installer_name = self._update_info.get("asset_name") or "ScrcpyDeckSetup.exe"
                installer_path = temp_dir / installer_name
                url = self._update_info["download_url"]

                self.logs.log("INFO", f"Downloading update v{self._update_info['version']}...")
                success = download_installer(
                    url,
                    installer_path,
                    on_progress=lambda pct: self._updateProgress.emit(pct),
                    cancel_event=self._update_cancel,
                )
                if not success:
                    if self._update_cancel.is_set():
                        self.logs.log("INFO", "Update download cancelled.")
                        self._updateStatusChanged.emit("available", "")
                    else:
                        self.logs.log("ERROR", "Update download failed.")
                        self._updateStatusChanged.emit("error", "Download failed. Please check network connection.")
                    return

                self.logs.log("INFO", f"Update downloaded. Launching installer and restarting...")
                self._updateStatusChanged.emit("installing", "")
                launch_installer_and_restart(installer_path)
                QTimer.singleShot(600, QGuiApplication.quit)
            except Exception as exc:
                self.logs.log("ERROR", f"Update failed: {exc}")
                self._updateStatusChanged.emit("error", str(exc))

        Thread(target=run_download, daemon=True).start()

    @Slot()
    def cancelUpdate(self):
        self._update_cancel.set()

    def _on_scrcpy_checked(self, info):
        if self._closed:
            return
        if info:
            self._scrcpy_info = info
            latest = info["version"]
            status = "available" if info.get("has_update") else "up-to-date"
            self.logs.log("INFO", f"Genymobile/scrcpy: current v{self.scrcpy_version}, latest v{latest} ({status}).")
            self._change(scrcpyLatest=latest, scrcpyStatus=status, scrcpyError="")
        else:
            self._change(scrcpyStatus="error", scrcpyError="Could not fetch release from Genymobile/scrcpy.")

    def _on_scrcpy_status_changed(self, status, error=""):
        if self._closed:
            return
        self._change(scrcpyStatus=status, scrcpyError=error)

    @Slot()
    def checkScrcpyUpdate(self):
        if self._closed or self._state.get("scrcpyStatus") == "downloading":
            return
        self._change(scrcpyStatus="checking", scrcpyError="")
        def check():
            try:
                info = find_latest_scrcpy_release(self.scrcpy_version)
                if not self._closed:
                    self._scrcpyChecked.emit(info)
            except Exception as exc:
                if not self._closed:
                    self.logs.log("WARN", f"Scrcpy release check failed: {exc}")
                    self._scrcpyStatusChanged.emit("error", str(exc))
        Thread(target=check, daemon=True).start()

    @Slot()
    def installScrcpyUpdate(self):
        if self._closed or not self._scrcpy_info:
            return
        if self._state.get("scrcpyStatus") == "downloading":
            return
        self._scrcpy_cancel.clear()
        self._change(scrcpyStatus="downloading", scrcpyProgress=0, scrcpyError="")

        def run_update():
            try:
                temp_dir = Path(tempfile.gettempdir()) / "ScrcpyDeckUpdate"
                temp_dir.mkdir(parents=True, exist_ok=True)
                zip_name = self._scrcpy_info.get("asset_name") or "scrcpy.zip"
                zip_path = temp_dir / zip_name
                url = self._scrcpy_info["download_url"]

                self.logs.log("INFO", f"Downloading scrcpy core {self._scrcpy_info['version']} from {url}...")
                success = download_installer(
                    url,
                    zip_path,
                    on_progress=lambda pct: self._scrcpyProgress.emit(pct),
                    cancel_event=self._scrcpy_cancel,
                )
                if not success:
                    if self._scrcpy_cancel.is_set():
                        self.logs.log("INFO", "Scrcpy download cancelled.")
                        self._scrcpyStatusChanged.emit("available", "")
                    else:
                        self.logs.log("ERROR", "Scrcpy download failed.")
                        self._scrcpyStatusChanged.emit("error", "Download failed.")
                    return

                self.logs.log("INFO", "Extracting scrcpy runtime binaries...")
                self._scrcpyStatusChanged.emit("installing", "")
                target_dir = get_writable_runtime()
                extract_scrcpy_archive(zip_path, target_dir)

                # Reinitialize scrcpy and adb paths
                self.scrcpy = executable("scrcpy")
                self.adb = AdbManager(executable("adb"), RESOURCES, self.logs.log)
                self.env = child_environment(self.adb.exe, self.scrcpy)
                self.scrcpy_version = get_installed_scrcpy_version(self.scrcpy) or self._scrcpy_info["version"]
                self.logs.log("INFO", f"Scrcpy updated successfully to v{self.scrcpy_version}!")
                self._change(scrcpyVersion=self.scrcpy_version, scrcpyStatus="installed", scrcpyProgress=100)
            except Exception as exc:
                self.logs.log("ERROR", f"Scrcpy update failed: {exc}")
                self._scrcpyStatusChanged.emit("error", str(exc))

        Thread(target=run_update, daemon=True).start()

    def startup(self):
        self.scan()
        self.checkForUpdates()

    @Slot()
    def shutdown(self):
        self._closed = True
        self.stop.set()
        self._update_cancel.set()
        self._scrcpy_cancel.set()
        self.timer.stop()
        self.save()
