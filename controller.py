"""Qt-facing state. Workers return values; only the GUI thread mutates the model."""
from dataclasses import asdict
from datetime import datetime
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from threading import Event, Lock, Thread
import urllib.request
import uuid

from PySide6.QtCore import QObject, Property, QStandardPaths, QTimer, Signal, Slot, Qt
from PySide6.QtGui import QGuiApplication

from adb import AdbManager, DeviceError, HIDDEN
from assets import APP_DIR, RESOURCES, VERSION, child_environment, executable, get_writable_runtime
from config import DEFAULTS, SettingsStore, normalize
from console import ConsoleModel, infer_fix_hint
from library import address, endpoint, merge_devices
from processes import ProcessRunner
from release_catalog import (
    DECK_REPO,
    SCRCPY_REPO,
    ReleaseEntry,
    get_catalog,
    parse_semver,
)
from runtime_capabilities import (
    check_feature_support,
    get_all_capabilities,
    summarize_incompatibilities,
)
from runtime_manager import (
    clean_unused_runtimes,
    cleanup_staging,
    get_active_pointer,
    get_installed_runtime_path,
    get_installed_runtimes,
    is_valid_runtime_dir,
    promote_staging_to_version,
    prune_old_versions,
    remove_active_pointer,
    stage_and_validate_runtime,
    write_active_pointer,
)
from scrcpy_command import build_scrcpy_command
from updater import (
    backup_user_settings,
    download_installer,
    extract_scrcpy_archive,
    find_latest_scrcpy_release,
    find_latest_update,
    get_installed_scrcpy_version,
    get_target_executable,
    get_version_preferences,
    launch_installer_and_restart,
    set_version_preference,
)
from workflows import Connections


def format_date_str(date_str: str) -> str:
    """Format ISO date string to human-readable 'DD Month YYYY'."""
    if not date_str:
        return ""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%d %B %Y")
    except Exception:
        return str(date_str)[:10]


def format_size_bytes(bytes_int: int) -> str:
    """Format bytes into KB or MB string."""
    if not bytes_int or bytes_int <= 0:
        return ""
    if bytes_int < 1024 * 1024:
        return f"{bytes_int / 1024:.1f} KB"
    return f"{bytes_int / (1024 * 1024):.1f} MB"


def _same_version(left, right) -> bool:
    """Compare display versions semantically (``5.0`` equals ``5.0.0``)."""
    left_tuple = parse_semver(str(left or ""))
    right_tuple = parse_semver(str(right or ""))
    return bool(left_tuple and right_tuple and left_tuple == right_tuple)


def normalize_release_for_ui(entry, component: str, installed_version: str) -> dict:
    """Return the single release schema consumed by controller state and QML.

    ``ReleaseEntry`` field names intentionally remain unchanged because they are
    also the persistent cache schema.  This boundary accepts both those objects
    and legacy dictionaries, including dictionaries already normalized by older
    tests or callers.
    """
    if isinstance(entry, ReleaseEntry):
        raw = entry.to_dict()
    elif isinstance(entry, dict):
        raw = dict(entry)
    else:
        raise TypeError(f"Unsupported release entry type: {type(entry).__name__}")

    version = str(raw.get("version") or raw.get("version_str") or "").strip()
    version_tuple = raw.get("version_tuple") or parse_semver(version)
    if isinstance(version_tuple, list):
        version_tuple = tuple(version_tuple)
    if not (
        isinstance(version_tuple, tuple)
        and len(version_tuple) == 3
        and all(isinstance(part, int) for part in version_tuple)
    ):
        version_tuple = parse_semver(str(raw.get("tag_name") or version))
    if not version or version_tuple is None:
        raise ValueError("Release metadata does not contain a semantic version")

    installed_tuple = parse_semver(installed_version)
    if installed_tuple is None:
        action_type = "install"
    elif version_tuple > installed_tuple:
        action_type = "upgrade"
    elif version_tuple < installed_tuple:
        action_type = "downgrade"
    else:
        action_type = "reinstall" if component == "deck" else "active"

    size = raw.get("size", raw.get("asset_size", 0))
    try:
        size = max(0, int(size or 0))
    except (TypeError, ValueError):
        size = 0

    return {
        "version": version,
        "tag_name": str(raw.get("tag_name") or f"v{version}"),
        "version_tuple": list(version_tuple),
        "published_at": str(raw.get("published_at") or ""),
        "download_url": raw.get("download_url") or "",
        "asset_name": raw.get("asset_name") or "",
        "size": size,
        "is_compatible": bool(raw.get("is_compatible", raw.get("is_compatible_asset", False))),
        "action_type": action_type,
        "html_url": str(raw.get("html_url") or ""),
        "body": str(raw.get("body") or ""),
    }


def _installed_scrcpy_runtime(version):
    """Resolve a local runtime even when its folder uses an equivalent semver."""
    exact = get_installed_runtime_path(version)
    if exact:
        return exact
    for runtime_dir in get_installed_runtimes():
        if _same_version(Path(runtime_dir).name, version):
            return Path(runtime_dir)
    return None


class Deck(QObject):
    stateChanged = Signal()
    settingsChanged = Signal()
    savedChanged = Signal()
    recoveryOffered = Signal(int)
    paired = Signal()
    capabilitiesChanged = Signal()
    versionManagerChanged = Signal()
    notificationsChanged = Signal()
    navigateToSection = Signal(str, str)
    _completed = Signal(object, object, str)
    _processExited = Signal(str, int)
    _updateFound = Signal(object)
    _updateProgress = Signal(int)
    _updateStatusChanged = Signal(str, str)
    _updateDownloaded = Signal(object)
    _scrcpyChecked = Signal(object)
    _scrcpyProgress = Signal(int)
    _scrcpyStatusChanged = Signal(str, str)
    _scrcpyPrepared = Signal(object)
    _catalogLoaded = Signal(object)

    def __init__(self, profile=None, app_dir=APP_DIR):
        super().__init__()
        self.app_dir = Path(app_dir)
        profile = profile or Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)) / "config.json"
        self._profile_dir = Path(profile).parent
        self.store = SettingsStore(profile, self.app_dir / "config.json")
        self.logs = ConsoleModel()

        # Clean up any interrupted update staging directories on startup
        try:
            cleanup_staging()
        except Exception:
            pass

        self.adb = AdbManager(executable("adb"), RESOURCES, self.logs.log)
        self.scrcpy = executable("scrcpy")

        # Resolve installed version from binary or committed active runtime pointer
        active_version = None
        try:
            pointer = get_active_pointer(get_writable_runtime())
            if pointer and pointer.get("version"):
                active_version = str(pointer["version"])
        except Exception:
            pass

        self.scrcpy_version = (
            get_installed_scrcpy_version(self.scrcpy)
            or active_version
            or "5.0.1"
        )
        self._capabilities = get_all_capabilities(self.scrcpy_version, self.scrcpy)

        self.env = child_environment(self.adb.exe, self.scrcpy)
        self.stop = Event()
        self.wireless = Connections(self.adb, self.stop)
        self._closed = False
        self._update_info = None
        self._update_cancel = Event()
        self._update_op_id = 0
        self._deck_op_id = 0
        self._scrcpy_info = None
        self._scrcpy_cancel = Event()
        self._scrcpy_op_id = 0
        self._pending_scrcpy_runtime = None
        self._activating_runtime = False
        self._catalog_lock = Lock()
        self._catalog_generation = 0
        self._catalog_pending = set()
        self._catalog_inflight = False
        self._catalog_cancel = Event()

        self._version_prefs = get_version_preferences(self._profile_dir)
        self._deck_releases = []
        self._scrcpy_releases = []
        self._selected_deck_release = None
        self._selected_scrcpy_release = None

        self._notifications = {
            "deck": {
                "visible": False,
                "latest_version": "",
                "current_version": VERSION,
                "title": "",
                "message": "",
            },
            "scrcpy": {
                "visible": False,
                "latest_version": "",
                "current_version": self.scrcpy_version,
                "title": "",
                "message": "",
            },
        }

        self._state = dict(
            status="Ready", error="", busy=False, devices=[], serial="",
            tcpSerial="", port="", lenses=["Default"], recovering=False,
            update="", updateStatus="", updateProgress=0, updateError="",
            updateSize=0, sessions=0,
            deckLatest="", deckCatalogSource="",
            scrcpyVersion=self.scrcpy_version,
            scrcpyLatest="",
            scrcpyCatalogSource="",
            scrcpyStatus="",
            scrcpyProgress=0,
            scrcpyError="",
            # Version manager state
            deckReleases=[],
            deckReleaseLabels=[],
            deckReleaseVersions=[],
            selectedDeckIndex=0,
            selectedDeckInfo={},
            deckActionText="Check for updates",
            deckPinningPreference=self._version_prefs.get("deck_pinning", "follow_latest"),
            scrcpyReleases=[],
            scrcpyReleaseLabels=[],
            scrcpyReleaseVersions=[],
            selectedScrcpyIndex=0,
            selectedScrcpyInfo={},
            scrcpyActionText="Check for updates",
            scrcpyPinningPreference=self._version_prefs.get("scrcpy_pinning", "follow_latest"),
            scrcpyCompatibilitySummary=[],
            installedScrcpyVersions=[Path(p).name for p in get_installed_runtimes()],
        )
        self._guides = json.loads((RESOURCES / "data/guides.json").read_text(encoding="utf-8"))
        self.runner = ProcessRunner(self.env, self.logs.log, self._processExited.emit)

        # Qt queued connections for thread safety
        self._completed.connect(self._finish, Qt.QueuedConnection)
        self._processExited.connect(self._exited, Qt.QueuedConnection)
        self._updateFound.connect(self._on_update_found, Qt.QueuedConnection)
        self._updateProgress.connect(lambda p: self._change(updateProgress=p), Qt.QueuedConnection)
        self._updateStatusChanged.connect(self._on_update_status_changed, Qt.QueuedConnection)
        self._updateDownloaded.connect(self._on_update_downloaded, Qt.QueuedConnection)
        self._scrcpyChecked.connect(self._on_scrcpy_checked, Qt.QueuedConnection)
        self._scrcpyProgress.connect(lambda p: self._change(scrcpyProgress=p), Qt.QueuedConnection)
        self._scrcpyStatusChanged.connect(self._on_scrcpy_status_changed, Qt.QueuedConnection)
        self._scrcpyPrepared.connect(self._on_scrcpy_prepared, Qt.QueuedConnection)
        self._catalogLoaded.connect(self._on_catalog_loaded, Qt.QueuedConnection)

        self.timer = QTimer(self, interval=350, singleShot=True)
        self.timer.timeout.connect(self.save)
        self.logs.log("INFO", "Console ready.")
        if self.store.error:
            self._error(self.store.error)
        elif self.store.dirty:
            self.timer.start()

        self._refresh_version_manager_lists()

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

    @Property("QVariantMap", notify=capabilitiesChanged)
    def capabilities(self):
        return self._capabilities

    @Property("QVariantMap", notify=notificationsChanged)
    def notifications(self):
        return self._notifications

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

    @Slot()
    def save(self):
        if self.store.dirty:
            self.store.save()
            self.logs.log("INFO", "Settings saved.")

    def _library_changed(self):
        self.savedChanged.emit()
        self.store.dirty = True
        self.timer.start()

    def _job(self, title, work, done, failed=None):
        if self._state["busy"]:
            return
        self.stop.clear()
        self._change(busy=True, busyText=title, error="")

        def execute():
            try:
                result = work()
                error = None
            except Exception as exc:
                result = None
                error = exc
            self._completed.emit(done if error is None else failed, result, str(error) if error else "")

        Thread(target=execute, daemon=True).start()

    @Slot(object, object, str)
    def _finish(self, callback, result, error):
        if self._closed:
            return
        self._change(busy=False, busyText="")
        if self.stop.is_set():
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
        if getattr(self, "_activating_runtime", False):
            self._error("Cannot start session while runtime update is activating.")
            return
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
            cmd = build_scrcpy_command(
                dict(s, device_serial=serial, scrcpy_exe=self.scrcpy, scrcpy_version=self.scrcpy_version),
                capabilities=self._capabilities,
            )
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
        if name == "scrcpy" or "scrcpy" in name.lower():
            self._change(sessions=max(0, self._state["sessions"] - 1))
            if code:
                self._error(f"scrcpy exited with code {code}. Open the console for details.")
            else:
                self._change(status="Session ended")

    @Slot(str)
    def copy(self, value):
        QGuiApplication.clipboard().setText(value)

    def _activate_runtime(self, runtime_dir, version_str=None):
        """Authoritative main-thread runtime synchronization and activation."""
        self._activating_runtime = True
        try:
            if self._state.get("sessions", 0) > 0:
                raise RuntimeError(
                    "Cannot update scrcpy runtime while active mirroring sessions are running. "
                    "Please close all active sessions and retry."
                )

            target_dir = Path(runtime_dir).resolve()
            new_scrcpy = target_dir / "scrcpy.exe"
            new_adb_exe = target_dir / "adb.exe"
            new_server = target_dir / "scrcpy-server"

            for f in (new_scrcpy, new_adb_exe, new_server):
                if not f.is_file():
                    raise FileNotFoundError(f"Missing required runtime binary: {f}")

            version = (
                version_str
                or get_installed_scrcpy_version(new_scrcpy)
                or self.scrcpy_version
            )

            # Pre-construct dependencies before mutating active references
            new_adb = AdbManager(str(new_adb_exe), RESOURCES, self.logs.log)
            new_env = child_environment(str(new_adb_exe), str(new_scrcpy))

            # Atomic pointer write
            from runtime_manager import (
                get_active_pointer,
                prune_old_versions,
                write_active_pointer,
            )
            from assets import get_writable_runtime

            root = get_writable_runtime()
            old_pointer = get_active_pointer(root)
            prev_rel = old_pointer.get("relative_path") if old_pointer else None

            try:
                rel_path = target_dir.relative_to(root)
            except ValueError:
                rel_path = Path("versions") / target_dir.name

            write_active_pointer(root, version, str(rel_path), prev_rel)

            # In-memory dependency synchronization with rollback
            old_scrcpy = self.scrcpy
            old_adb = self.adb
            old_env = self.env
            old_version = self.scrcpy_version
            old_runner_env = self.runner.env
            old_wireless_adb = self.wireless.adb

            try:
                self.scrcpy = str(new_scrcpy)
                self.adb = new_adb
                self.env = new_env
                self.scrcpy_version = version
                self.wireless.set_adb(new_adb)
                self.runner.set_env(new_env)

                # Confirm consistency
                assert self.scrcpy == str(new_scrcpy)
                assert self.adb.exe == str(new_adb_exe)
                assert self.runner.env == new_env
                assert self.wireless.adb == new_adb

                # Recompute capabilities
                self._capabilities = get_all_capabilities(version, str(new_scrcpy))
                self.capabilitiesChanged.emit()

                prune_old_versions(root)
                self._change(
                    scrcpyVersion=version,
                    scrcpyStatus="installed",
                    scrcpyProgress=100,
                    scrcpyError="",
                    installedScrcpyVersions=[Path(p).name for p in get_installed_runtimes()],
                )
                self._refresh_version_manager_lists()
                self.logs.log(
                    "INFO",
                    f"Scrcpy runtime successfully updated and synchronized to v{version}!",
                )
                return True
            except Exception as exc:
                # Rollback in-memory
                self.scrcpy = old_scrcpy
                self.adb = old_adb
                self.env = old_env
                self.scrcpy_version = old_version
                self.wireless.adb = old_wireless_adb
                self.runner.env = old_runner_env
                # Rollback active pointer
                if old_pointer:
                    try:
                        write_active_pointer(
                            root,
                            old_pointer.get("version", old_version),
                            old_pointer.get("relative_path"),
                            old_pointer.get("previous_relative_path"),
                        )
                    except Exception:
                        pass
                raise exc
        finally:
            self._activating_runtime = False

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

    @Slot(object)
    def _on_update_downloaded(self, result):
        if self._closed:
            return
        if not isinstance(result, dict) or result.get("op_id") != self._update_op_id:
            return

        installer_path = result.get("installer_path")
        target_exe = get_target_executable()

        if not getattr(sys, "frozen", False):
            # Running from source mode
            if not target_exe or target_exe.name.lower() != "scrcpydeck.exe" or not target_exe.is_file():
                self.logs.log(
                    "WARN",
                    "In-app installation requires the packaged Scrcpy Deck application. "
                    f"Installer downloaded to: {installer_path}",
                )
                self._change(
                    updateStatus="available",
                    updateError=(
                        "In-app installation requires the packaged Scrcpy Deck application. "
                        f"Installer saved to: {installer_path}"
                    ),
                )
                return

        # Prepare and save state before shutdown
        self.timer.stop()
        self.save()

        self._change(updateStatus="installing", updateError="")
        self.logs.log("INFO", "Update downloaded. Launching installer and preparing restart...")

        try:
            proc = launch_installer_and_restart(installer_path, target_exe, pid=os.getpid())
            if not proc:
                raise RuntimeError("Failed to launch installer runner process.")
        except Exception as exc:
            self.logs.log("ERROR", f"Installer launch failed: {exc}")
            self._change(updateStatus="error", updateError=f"Installer launch failed: {exc}")
            return

        # Clean Qt application shutdown initiated on the main thread
        QGuiApplication.quit()

    @Slot()
    def checkForUpdates(self):
        if self._closed or self._state.get("updateStatus") in ("checking", "downloading", "installing"):
            return
        self._change(updateStatus="checking", updateProgress=0, updateError="")

        def check():
            try:
                update = find_latest_update()
                self._updateFound.emit(update)
            except Exception as exc:
                self.logs.log("ERROR", f"Update check failed: {exc}")
                self._updateStatusChanged.emit("error", str(exc))

        Thread(target=check, daemon=True).start()

    @Slot()
    def installUpdate(self):
        if self._closed or not self._update_info:
            return
        if self._state.get("updateStatus") in ("downloading", "installing"):
            return
        if self._state.get("scrcpyStatus") in ("downloading", "installing"):
            self.logs.log("WARN", "Cannot install application update while scrcpy core update is in progress.")
            return

        self._update_cancel.clear()
        self._update_op_id += 1
        op_id = self._update_op_id
        info = dict(self._update_info)
        self._change(updateStatus="downloading", updateProgress=0, updateError="")

        def run_download():
            try:
                temp_dir = Path(tempfile.gettempdir()) / "ScrcpyDeckUpdate"
                temp_dir.mkdir(parents=True, exist_ok=True)
                installer_name = info.get("asset_name") or "ScrcpyDeckSetup.exe"
                installer_path = temp_dir / installer_name
                url = info["download_url"]

                self.logs.log("INFO", f"Downloading update v{info['version']}...")
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

                # Worker emits completion to the main thread
                self._updateDownloaded.emit({
                    "installer_path": str(installer_path),
                    "op_id": op_id,
                    "version": info["version"],
                })
            except Exception as exc:
                self.logs.log("ERROR", f"Update failed: {exc}")
                self._updateStatusChanged.emit("error", str(exc))

        Thread(target=run_download, daemon=True).start()

    @Slot()
    def cancelUpdate(self):
        self._update_cancel.set()
        if self._state.get("updateStatus") == "downloading":
            self._change(updateStatus="available", updateProgress=0, updateError="Download cancelled.")

    @Slot()
    def cancelScrcpyUpdate(self):
        self._scrcpy_cancel.set()
        if self._state.get("scrcpyStatus") in ("downloading", "installing"):
            self._change(scrcpyStatus="available", scrcpyProgress=0, scrcpyError="Download cancelled.")

    def _on_scrcpy_checked(self, info):
        if self._closed:
            return
        if info:
            self._scrcpy_info = info
            self.logs.log("INFO", f"Scrcpy update available: v{info['version']}")
            self._change(
                scrcpyLatest=info["version"],
                scrcpyStatus="available",
                scrcpyProgress=0,
                scrcpyError="",
                scrcpySize=info.get("size", 0),
            )
        else:
            self._scrcpy_info = None
            self._change(scrcpyLatest="", scrcpyStatus="", scrcpyProgress=0, scrcpyError="")

    def _on_scrcpy_status_changed(self, status, error=""):
        if self._closed:
            return
        changes = {"scrcpyStatus": status, "scrcpyError": error}
        if status == "available":
            changes["scrcpyProgress"] = 0
        self._change(**changes)

    @Slot(object)
    def _on_scrcpy_prepared(self, result):
        if self._closed:
            return
        if not isinstance(result, dict):
            return
        if result.get("op_id") != self._scrcpy_op_id and result != self._pending_scrcpy_runtime:
            return

        runtime_dir = result.get("runtime_dir")
        version = result.get("version", "")

        if self._state.get("sessions", 0) > 0:
            self._pending_scrcpy_runtime = result
            self.logs.log(
                "WARN",
                f"Scrcpy v{version} update is ready, but mirroring sessions are active. Close them to activate.",
            )
            self._change(
                scrcpyStatus="available",
                scrcpyError=(
                    f"Scrcpy v{version} is ready to install, but active mirroring sessions are running. "
                    "Please close them and click Install again."
                ),
            )
            return

        self._pending_scrcpy_runtime = None
        self._change(scrcpyStatus="installing", scrcpyError="")

        try:
            self._activate_runtime(runtime_dir, version)
        except Exception as exc:
            self.logs.log("ERROR", f"Activation of scrcpy v{version} failed: {exc}")
            self._change(scrcpyStatus="error", scrcpyError=str(exc))

    @Slot()
    def checkScrcpyUpdate(self):
        if self._closed or self._state.get("scrcpyStatus") in ("checking", "downloading", "installing"):
            return
        self._change(scrcpyStatus="checking", scrcpyProgress=0, scrcpyError="")

        def check():
            try:
                info = find_latest_scrcpy_release(self.scrcpy_version)
                self._scrcpyChecked.emit(info)
            except Exception as exc:
                self.logs.log("ERROR", f"Scrcpy update check failed: {exc}")
                self._scrcpyStatusChanged.emit("error", str(exc))

        Thread(target=check, daemon=True).start()

    @Slot()
    def installScrcpyUpdate(self):
        if self._closed or not (self._selected_scrcpy_release or self._scrcpy_info):
            return
        if self._state.get("scrcpyStatus") in ("downloading", "installing"):
            return
        if self._state.get("updateStatus") in ("downloading", "installing"):
            self.logs.log("WARN", "Cannot install scrcpy update while Scrcpy Deck application update is in progress.")
            return

        info = dict(self._selected_scrcpy_release or self._scrcpy_info)
        target_version = info.get("version")

        # Check if already prepared and pending activation due to previous active sessions
        if (
            self._pending_scrcpy_runtime
            and self._pending_scrcpy_runtime.get("version") == target_version
        ):
            if self._state.get("sessions", 0) == 0:
                self._change(scrcpyStatus="installing", scrcpyError="")
                self._on_scrcpy_prepared(self._pending_scrcpy_runtime)
                return
            else:
                self._change(
                    scrcpyStatus="available",
                    scrcpyError="Cannot install while active sessions are running. Close sessions and click Install.",
                )
                return

        if self._state.get("sessions", 0) > 0:
            self.logs.log("WARN", "Cannot change scrcpy runtime while mirroring sessions are active. Close them first.")
            self._change(
                scrcpyStatus="available",
                scrcpyError="Cannot change runtime while active sessions are running. Please close all sessions.",
            )
            return

        if _same_version(target_version, self.scrcpy_version):
            self.logs.log("INFO", f"Scrcpy v{target_version} is already the active runtime.")
            return

        # Check if version is already installed locally in versions/
        local_dir = _installed_scrcpy_runtime(target_version)
        if local_dir:
            self.logs.log("INFO", f"Activating locally installed scrcpy runtime v{target_version}...")
            self._change(scrcpyStatus="installing", scrcpyError="")
            try:
                self._activate_runtime(local_dir, target_version)
            except Exception as exc:
                self.logs.log("ERROR", f"Activation failed: {exc}")
                self._change(scrcpyStatus="error", scrcpyError=str(exc))
            return

        self._scrcpy_cancel.clear()
        self._scrcpy_op_id += 1
        op_id = self._scrcpy_op_id
        cancel_evt = self._scrcpy_cancel

        self._change(scrcpyStatus="downloading", scrcpyProgress=0, scrcpyError="")

        def run_update():
            try:
                temp_dir = Path(tempfile.gettempdir()) / "ScrcpyDeckUpdate"
                temp_dir.mkdir(parents=True, exist_ok=True)
                zip_name = info.get("asset_name") or "scrcpy.zip"
                zip_path = temp_dir / zip_name
                url = info["download_url"]

                self.logs.log("INFO", f"Downloading scrcpy core {info['version']} from {url}...")
                success = download_installer(
                    url,
                    zip_path,
                    on_progress=lambda pct: self._scrcpyProgress.emit(pct),
                    cancel_event=cancel_evt,
                )
                if not success:
                    if cancel_evt.is_set():
                        self.logs.log("INFO", "Scrcpy download cancelled.")
                        self._scrcpyStatusChanged.emit("available", "")
                    else:
                        self.logs.log("ERROR", "Scrcpy download failed.")
                        self._scrcpyStatusChanged.emit("error", "Download failed.")
                    return

                if cancel_evt.is_set():
                    self.logs.log("INFO", "Scrcpy update cancelled before staging.")
                    self._scrcpyStatusChanged.emit("available", "")
                    return

                self.logs.log("INFO", "Staging and validating scrcpy runtime binaries...")
                self._scrcpyStatusChanged.emit("installing", "")

                import runtime_manager
                staging_dir, detected_version = runtime_manager.stage_and_validate_runtime(
                    zip_path,
                    expected_version=info.get("version"),
                )

                if cancel_evt.is_set():
                    shutil.rmtree(staging_dir, ignore_errors=True)
                    self.logs.log("INFO", "Scrcpy update cancelled before promotion.")
                    self._scrcpyStatusChanged.emit("available", "")
                    return

                final_dir = runtime_manager.promote_staging_to_version(staging_dir, detected_version)

                # Worker emits completion to the main thread
                self._scrcpyPrepared.emit({
                    "version": detected_version,
                    "runtime_dir": str(final_dir),
                    "op_id": op_id,
                })
            except Exception as exc:
                self.logs.log("ERROR", f"Scrcpy update failed: {exc}")
                self._scrcpyStatusChanged.emit("error", str(exc))

        Thread(target=run_update, daemon=True).start()

    @Slot()
    @Slot(bool)
    def checkAllUpdates(self, force=False):
        if self._closed or self._catalog_inflight:
            return
        self._catalog_generation += 1
        generation = self._catalog_generation
        self._catalog_pending = {"deck", "scrcpy"}
        self._catalog_inflight = True
        self._catalog_cancel.clear()
        changes = {}
        if self._state.get("updateStatus") not in ("downloading", "installing"):
            changes.update(updateStatus="checking", updateError="")
        if self._state.get("scrcpyStatus") not in ("downloading", "installing"):
            changes.update(scrcpyStatus="checking", scrcpyError="")
        self._change(**changes)

        # Resolve the singleton before starting workers so concurrent first use
        # cannot construct two cache services that overwrite one another.
        try:
            catalog = get_catalog()
        except Exception as exc:
            self._set_catalog_error("deck", str(exc))
            self._set_catalog_error("scrcpy", str(exc))
            self._catalog_pending.clear()
            self._catalog_inflight = False
            return

        def run_fetch(component, repo):
            try:
                entries, _is_cached, source = catalog.fetch_releases(
                    repo,
                    force_refresh=force,
                    cancel_event=self._catalog_cancel,
                    return_source=True,
                )
                self._catalogLoaded.emit({
                    "generation": generation,
                    "component": component,
                    "entries": entries,
                    "source": source,
                    "error": "",
                })
            except Exception as exc:
                self._catalogLoaded.emit({
                    "generation": generation,
                    "component": component,
                    "entries": [],
                    "source": "error",
                    "error": str(exc),
                })

        Thread(target=run_fetch, args=("deck", DECK_REPO), daemon=True).start()
        Thread(target=run_fetch, args=("scrcpy", SCRCPY_REPO), daemon=True).start()

    def _normalize_catalog_entries(self, entries, component):
        installed = VERSION if component == "deck" else self.scrcpy_version
        normalized = []
        seen = set()
        for entry in entries or []:
            try:
                item = normalize_release_for_ui(entry, component, installed)
            except Exception as exc:
                self.logs.log(
                    "WARN",
                    f"release_catalog component={component} result=skipped error={exc}",
                )
                continue
            version_key = tuple(item["version_tuple"])
            if version_key in seen:
                continue
            seen.add(version_key)
            normalized.append(item)
        normalized.sort(key=lambda item: tuple(item["version_tuple"]), reverse=True)
        return normalized

    def _set_catalog_error(self, component, message):
        message = message or "Unknown release catalog error"
        self.logs.log(
            "ERROR",
            f"release_catalog component={component} result=error error={message}",
        )
        if component == "deck":
            changes = {"updateStatus": "error", "updateError": message, "deckCatalogSource": "error"}
            if not self._deck_releases:
                changes.update(update="", deckLatest="")
            self._change(**changes)
        else:
            changes = {"scrcpyStatus": "error", "scrcpyError": message, "scrcpyCatalogSource": "error"}
            if not self._scrcpy_releases:
                changes["scrcpyLatest"] = ""
            self._change(**changes)

    def _update_catalog_notification(self, component, target):
        pref_key = f"{component}_pinning"
        dismissed_key = f"dismissed_{component}_notifications"
        dismissed = self._version_prefs.get(dismissed_key, [])
        visible = bool(
            target
            and self._version_prefs.get(pref_key, "follow_latest") != "pinned"
            and target["version"] not in dismissed
        )
        current = VERSION if component == "deck" else self.scrcpy_version
        title_name = "Scrcpy Deck" if component == "deck" else "scrcpy core"
        self._notifications[component] = {
            "visible": visible,
            "latest_version": target["version"] if target else "",
            "current_version": current,
            "title": f"{title_name} v{target['version']} is available" if target else "",
            "message": (
                "A newer stable version of Scrcpy Deck was released."
                if component == "deck" and target
                else "A newer engine release is available for download."
                if target
                else ""
            ),
        }
        self.notificationsChanged.emit()

    def _apply_catalog_result(self, component, entries, source):
        normalized = self._normalize_catalog_entries(entries, component)
        if not normalized:
            raise ValueError(f"No valid stable {component} releases were returned")

        with self._catalog_lock:
            if component == "deck":
                self._deck_releases = normalized
            else:
                self._scrcpy_releases = normalized
            self._refresh_version_manager_lists()

        latest = normalized[0]
        target = next((item for item in normalized if item["action_type"] == "upgrade"), None)
        offline = source == "offline_cache"
        if component == "deck":
            self._update_info = dict(target) if target else None
            changes = {
                "deckLatest": latest["version"],
                "deckCatalogSource": source,
                "update": target["version"] if target else "",
                "updateSize": target.get("size", 0) if target else 0,
                "updateProgress": 0,
                "updateError": "Offline; showing cached releases." if offline else "",
            }
            if self._state.get("updateStatus") not in ("downloading", "installing"):
                changes["updateStatus"] = "offline" if offline else "available" if target else "up-to-date"
            self._change(**changes)
        else:
            self._scrcpy_info = dict(target) if target else None
            changes = {
                "scrcpyLatest": latest["version"],
                "scrcpyCatalogSource": source,
                "scrcpyProgress": 0,
                "scrcpyError": "Offline; showing cached releases." if offline else "",
                "scrcpySize": target.get("size", 0) if target else 0,
            }
            if self._state.get("scrcpyStatus") not in ("downloading", "installing"):
                changes["scrcpyStatus"] = "offline" if offline else "available" if target else "up-to-date"
            self._change(**changes)

        self._update_catalog_notification(component, target)
        self.logs.log(
            "INFO",
            f"release_catalog component={component} result=success source={source} releases={len(normalized)}",
        )

    @Slot(object)
    def _on_catalog_loaded(self, catalogs):
        if self._closed:
            return
        if not isinstance(catalogs, dict):
            self._set_catalog_error("deck", "Invalid catalog completion payload")
            self._set_catalog_error("scrcpy", "Invalid catalog completion payload")
            self._catalog_inflight = False
            return

        # Production workers emit one independently completed repository.  Keep
        # support for the original bulk payload for callers and cached tests.
        if "component" in catalogs:
            generation = catalogs.get("generation")
            component = catalogs.get("component")
            if generation != self._catalog_generation or component not in ("deck", "scrcpy"):
                self.logs.log(
                    "INFO",
                    f"release_catalog result=ignored generation={generation} current={self._catalog_generation}",
                )
                return
            try:
                if catalogs.get("error"):
                    self._set_catalog_error(component, catalogs["error"])
                else:
                    self._apply_catalog_result(component, catalogs.get("entries", []), catalogs.get("source", "network"))
            except Exception as exc:
                self._set_catalog_error(component, f"Could not process release metadata: {exc}")
            finally:
                self._catalog_pending.discard(component)
                if not self._catalog_pending:
                    self._catalog_inflight = False
            return

        for component in ("deck", "scrcpy"):
            try:
                self._apply_catalog_result(component, catalogs.get(component, []), "network")
            except Exception as exc:
                self._set_catalog_error(component, f"Could not process release metadata: {exc}")
        self._catalog_inflight = False

    def _refresh_version_manager_lists(self):
        installed_scrcpy_dirs = get_installed_runtimes()
        installed_scrcpy_versions = [Path(p).name for p in installed_scrcpy_dirs]
        if (
            self.scrcpy_version != "unknown"
            and not any(_same_version(self.scrcpy_version, version) for version in installed_scrcpy_versions)
        ):
            installed_scrcpy_versions.append(self.scrcpy_version)

        def is_local_scrcpy(version):
            return any(_same_version(version, local) for local in installed_scrcpy_versions)

        # 1. Deck releases
        deck_labels = []
        deck_versions = []
        latest_deck_ver = self._deck_releases[0]["version"] if self._deck_releases else VERSION
        for r in self._deck_releases:
            v = r["version"]
            deck_versions.append(v)
            is_cur = _same_version(v, VERSION)
            is_latest = _same_version(v, latest_deck_ver)
            if is_cur and is_latest:
                label = f"v{v} — Installed · Latest"
            elif is_cur:
                label = f"v{v} — Installed"
            elif is_latest:
                label = f"v{v} — Latest release"
            else:
                label = f"v{v} — Previous release"
            deck_labels.append(label)

        if not deck_labels:
            deck_labels = [f"v{VERSION} — Installed · Latest"]
            deck_versions = [VERSION]

        selected_deck_version = (
            self._selected_deck_release.get("version")
            if isinstance(self._selected_deck_release, dict)
            else None
        )
        cur_deck_idx = next(
            (i for i, version in enumerate(deck_versions) if _same_version(version, selected_deck_version)),
            0,
        )
        sel_deck_ver = deck_versions[cur_deck_idx]
        sel_deck_entry = next(
            (r for r in self._deck_releases if _same_version(r["version"], sel_deck_ver)),
            None,
        )

        if not sel_deck_entry:
            sel_deck_info = {
                "version": sel_deck_ver,
                "date": "Installed",
                "size_str": "",
                "action": "reinstall" if _same_version(sel_deck_ver, VERSION) else "install",
                "html_url": f"https://github.com/{DECK_REPO}/releases",
                "is_compatible": True,
                "body": "",
            }
        else:
            action = sel_deck_entry.get("action_type", "reinstall")
            sel_deck_info = {
                "version": sel_deck_entry["version"],
                "date": format_date_str(sel_deck_entry.get("published_at", "")),
                "size_str": format_size_bytes(sel_deck_entry.get("size", 0)),
                "action": action,
                "html_url": sel_deck_entry.get("html_url", f"https://github.com/{DECK_REPO}/releases"),
                "is_compatible": sel_deck_entry.get("is_compatible", True),
                "body": sel_deck_entry.get("body", ""),
            }
        self._selected_deck_release = sel_deck_entry

        act = sel_deck_info.get("action", "install")
        ver = sel_deck_info["version"]
        if act == "upgrade":
            deck_act_text = f"Upgrade to v{ver}"
        elif act == "downgrade":
            deck_act_text = f"Downgrade to v{ver}"
        elif act == "reinstall":
            deck_act_text = f"Reinstall v{ver}"
        else:
            deck_act_text = f"Install v{ver}"

        # 2. Scrcpy releases
        scrcpy_labels = []
        scrcpy_versions = []
        latest_scrcpy_ver = self._scrcpy_releases[0]["version"] if self._scrcpy_releases else self.scrcpy_version
        for r in self._scrcpy_releases:
            v = r["version"]
            scrcpy_versions.append(v)
            is_active = _same_version(v, self.scrcpy_version)
            is_local = is_local_scrcpy(v)
            is_latest = _same_version(v, latest_scrcpy_ver)
            if is_active and is_latest:
                label = f"v{v} — Active · Latest"
            elif is_active:
                label = f"v{v} — Active"
            elif is_local:
                label = f"v{v} — Available locally"
            elif is_latest:
                label = f"v{v} — Latest release"
            else:
                label = f"v{v} — Available"
            scrcpy_labels.append(label)

        if not scrcpy_labels:
            scrcpy_labels = [f"v{self.scrcpy_version} — Active · Current"]
            scrcpy_versions = [self.scrcpy_version]

        selected_scrcpy_version = (
            self._selected_scrcpy_release.get("version")
            if isinstance(self._selected_scrcpy_release, dict)
            else None
        )
        cur_scrcpy_idx = next(
            (i for i, version in enumerate(scrcpy_versions) if _same_version(version, selected_scrcpy_version)),
            0,
        )
        sel_scrcpy_ver = scrcpy_versions[cur_scrcpy_idx]
        sel_scrcpy_entry = next(
            (r for r in self._scrcpy_releases if _same_version(r["version"], sel_scrcpy_ver)),
            None,
        )

        is_installed = is_local_scrcpy(sel_scrcpy_ver) or _same_version(sel_scrcpy_ver, self.scrcpy_version)
        if not sel_scrcpy_entry:
            sel_scrcpy_info = {
                "version": sel_scrcpy_ver,
                "date": "Active" if sel_scrcpy_ver == self.scrcpy_version else "Installed",
                "size_str": "",
                "is_installed": is_installed,
                "html_url": f"https://github.com/{SCRCPY_REPO}/releases",
                "is_compatible": True,
                "body": "",
            }
        else:
            sel_scrcpy_info = {
                "version": sel_scrcpy_entry["version"],
                "date": format_date_str(sel_scrcpy_entry.get("published_at", "")),
                "size_str": format_size_bytes(sel_scrcpy_entry.get("size", 0)),
                "is_installed": is_installed,
                "html_url": sel_scrcpy_entry.get("html_url", f"https://github.com/{SCRCPY_REPO}/releases"),
                "is_compatible": sel_scrcpy_entry.get("is_compatible", True),
                "body": sel_scrcpy_entry.get("body", ""),
            }
        self._selected_scrcpy_release = sel_scrcpy_entry

        if _same_version(sel_scrcpy_ver, self.scrcpy_version):
            scrcpy_act_text = "Active runtime"
        elif is_installed:
            scrcpy_act_text = f"Activate v{sel_scrcpy_ver}"
        else:
            scrcpy_act_text = f"Install v{sel_scrcpy_ver}"

        sel_caps = get_all_capabilities(sel_scrcpy_ver)
        incompats = summarize_incompatibilities(sel_caps)

        self._change(
            deckReleases=list(self._deck_releases),
            deckReleaseLabels=deck_labels,
            deckReleaseVersions=deck_versions,
            selectedDeckIndex=cur_deck_idx,
            selectedDeckInfo=sel_deck_info,
            deckActionText=deck_act_text,
            scrcpyReleases=list(self._scrcpy_releases),
            scrcpyReleaseLabels=scrcpy_labels,
            scrcpyReleaseVersions=scrcpy_versions,
            selectedScrcpyIndex=cur_scrcpy_idx,
            selectedScrcpyInfo=sel_scrcpy_info,
            scrcpyActionText=scrcpy_act_text,
            scrcpyCompatibilitySummary=incompats,
            installedScrcpyVersions=installed_scrcpy_versions,
        )
        self.versionManagerChanged.emit()

    @Slot(int)
    def selectDeckRelease(self, index):
        if self._closed:
            return
        versions = self._state.get("deckReleaseVersions", [])
        if 0 <= index < len(versions):
            ver = versions[index]
            self._selected_deck_release = next(
                (r for r in self._deck_releases if _same_version(r["version"], ver)),
                None,
            )
            self._refresh_version_manager_lists()

    @Slot(int)
    def selectScrcpyRelease(self, index):
        if self._closed:
            return
        versions = self._state.get("scrcpyReleaseVersions", [])
        if 0 <= index < len(versions):
            ver = versions[index]
            self._selected_scrcpy_release = next(
                (r for r in self._scrcpy_releases if _same_version(r["version"], ver)),
                None,
            )
            self._refresh_version_manager_lists()

    @Slot(str)
    def setDeckPinning(self, preference):
        if preference in ("follow_latest", "pinned"):
            self._version_prefs["deck_pinning"] = preference
            if preference == "pinned":
                self._version_prefs["deck_pinned_version"] = VERSION
            set_version_preference("deck_pinning", preference, self._profile_dir)
            if preference == "pinned":
                set_version_preference("deck_pinned_version", VERSION, self._profile_dir)
            self._change(deckPinningPreference=preference)
            self._refresh_version_manager_lists()

    @Slot(str)
    def setScrcpyPinning(self, preference):
        if preference in ("follow_latest", "pinned"):
            self._version_prefs["scrcpy_pinning"] = preference
            if preference == "pinned":
                self._version_prefs["scrcpy_pinned_version"] = self.scrcpy_version
            set_version_preference("scrcpy_pinning", preference, self._profile_dir)
            if preference == "pinned":
                set_version_preference("scrcpy_pinned_version", self.scrcpy_version, self._profile_dir)
            self._change(scrcpyPinningPreference=preference)
            self._refresh_version_manager_lists()

    @Slot()
    def cleanUnusedRuntimes(self):
        try:
            pinned = self._version_prefs.get("scrcpy_pinned_version", "")
            keep = {self.scrcpy_version}
            if pinned:
                keep.add(pinned)
            removed = clean_unused_runtimes(keep_versions=keep)
            if removed:
                self.logs.log("INFO", f"Cleaned up {len(removed)} old scrcpy runtime(s): {', '.join(removed)}")
            else:
                self.logs.log("INFO", "No unused runtimes to clean.")
            self._refresh_version_manager_lists()
        except Exception as exc:
            self.logs.log("ERROR", f"Failed to clean runtimes: {exc}")

    @Slot()
    @Slot(bool)
    def installSelectedDeck(self, confirmed_downgrade=False):
        if self._closed:
            return
        info = self._selected_deck_release or self._update_info
        if not info:
            self.checkForUpdates()
            return
        if self._state.get("updateStatus") in ("downloading", "installing"):
            return

        if not info.get("download_url"):
            self._change(updateStatus="error", updateError="Selected release does not have a downloadable installer.")
            return

        if info.get("action_type") == "downgrade" and not confirmed_downgrade:
            return

        try:
            backup_path = backup_user_settings()
            if backup_path:
                self.logs.log("INFO", f"Created settings backup at: {backup_path.name}")
        except Exception as exc:
            self.logs.log("WARN", f"Could not create settings backup: {exc}")

        self._update_cancel.clear()
        self._deck_op_id += 1
        self._update_op_id = self._deck_op_id
        op_id = self._deck_op_id
        cancel_evt = self._update_cancel

        self._change(updateStatus="downloading", updateProgress=0, updateError="")
        url = info["download_url"]
        asset_name = info.get("asset_name") or f"ScrcpyDeck-{info['version']}-setup.exe"
        version_str = info["version"]

        def run_deck_download():
            try:
                temp_dir = Path(tempfile.gettempdir()) / "ScrcpyDeckUpdate"
                temp_dir.mkdir(parents=True, exist_ok=True)
                installer_path = temp_dir / asset_name

                self.logs.log("INFO", f"Downloading Scrcpy Deck v{version_str}...")
                success = download_installer(
                    url,
                    installer_path,
                    on_progress=lambda pct: self._updateProgress.emit(pct),
                    cancel_event=cancel_evt,
                )
                if not success:
                    if cancel_evt.is_set():
                        self.logs.log("INFO", "Scrcpy Deck download cancelled.")
                        self._updateStatusChanged.emit("available", "")
                    else:
                        self.logs.log("ERROR", "Scrcpy Deck download failed.")
                        self._updateStatusChanged.emit("error", "Download failed. Please check network connection.")
                    return

                self._updateDownloaded.emit({
                    "installer_path": str(installer_path),
                    "op_id": op_id,
                    "version": version_str,
                })
            except Exception as exc:
                self.logs.log("ERROR", f"Update failed: {exc}")
                self._updateStatusChanged.emit("error", str(exc))

        Thread(target=run_deck_download, daemon=True).start()

    @Slot()
    @Slot(bool)
    def installOrActivateSelectedScrcpy(self, confirmed_incompatible=False):
        if self._closed:
            return
        info = self._selected_scrcpy_release or self._scrcpy_info
        if not info:
            self.checkScrcpyUpdate()
            return
        if self._state.get("scrcpyStatus") in ("downloading", "installing"):
            return
        if self._state.get("updateStatus") in ("downloading", "installing"):
            self.logs.log("WARN", "Cannot install scrcpy core while application update is in progress.")
            return

        target_version = info.get("version")

        # Check if already prepared and pending activation due to previous active sessions
        if (
            self._pending_scrcpy_runtime
            and self._pending_scrcpy_runtime.get("version") == target_version
        ):
            if self._state.get("sessions", 0) == 0:
                self._change(scrcpyStatus="installing", scrcpyError="")
                self._on_scrcpy_prepared(self._pending_scrcpy_runtime)
                return
            else:
                self._change(
                    scrcpyStatus="available",
                    scrcpyError="Cannot install while active sessions are running. Close sessions and click Install.",
                )
                return

        if self._state.get("sessions", 0) > 0:
            self.logs.log("WARN", "Cannot change scrcpy runtime while mirroring sessions are active. Close them first.")
            self._change(
                scrcpyStatus="available",
                scrcpyError="Cannot change runtime while active sessions are running. Please close all sessions.",
            )
            return

        if _same_version(target_version, self.scrcpy_version):
            self.logs.log("INFO", f"Scrcpy v{target_version} is already the active runtime.")
            return

        # Check if version is already installed locally in versions/
        local_dir = _installed_scrcpy_runtime(target_version)
        if local_dir:
            self.logs.log("INFO", f"Activating locally installed scrcpy runtime v{target_version}...")
            self._change(scrcpyStatus="installing", scrcpyError="")
            try:
                self._activate_runtime(local_dir, target_version)
            except Exception as exc:
                self.logs.log("ERROR", f"Activation failed: {exc}")
                self._change(scrcpyStatus="error", scrcpyError=str(exc))
            return

        if not info.get("download_url"):
            self._change(scrcpyStatus="error", scrcpyError="No download URL available for this scrcpy release.")
            return

        self._scrcpy_cancel.clear()
        self._scrcpy_op_id += 1
        op_id = self._scrcpy_op_id
        cancel_evt = self._scrcpy_cancel

        self._change(scrcpyStatus="downloading", scrcpyProgress=0, scrcpyError="")
        url = info["download_url"]
        asset_name = info.get("asset_name") or f"scrcpy-win64-{target_version}.zip"

        def run_scrcpy_fetch():
            try:
                temp_dir = Path(tempfile.gettempdir()) / "ScrcpyDeckUpdate"
                temp_dir.mkdir(parents=True, exist_ok=True)
                zip_path = temp_dir / asset_name

                self.logs.log("INFO", f"Downloading scrcpy core v{target_version}...")
                success = download_installer(
                    url,
                    zip_path,
                    on_progress=lambda pct: self._scrcpyProgress.emit(pct),
                    cancel_event=cancel_evt,
                )
                if not success:
                    if cancel_evt.is_set():
                        self.logs.log("INFO", "Scrcpy download cancelled.")
                        self._scrcpyStatusChanged.emit("available", "")
                    else:
                        self.logs.log("ERROR", "Scrcpy download failed.")
                        self._scrcpyStatusChanged.emit("error", "Download failed.")
                    return

                if cancel_evt.is_set():
                    self.logs.log("INFO", "Scrcpy update cancelled before staging.")
                    self._scrcpyStatusChanged.emit("available", "")
                    return

                self.logs.log("INFO", "Staging and validating scrcpy binaries...")
                self._scrcpyStatusChanged.emit("installing", "")

                import runtime_manager
                staging_dir, detected_version = runtime_manager.stage_and_validate_runtime(
                    zip_path,
                    expected_version=target_version,
                )

                if cancel_evt.is_set():
                    shutil.rmtree(staging_dir, ignore_errors=True)
                    self.logs.log("INFO", "Scrcpy update cancelled before promotion.")
                    self._scrcpyStatusChanged.emit("available", "")
                    return

                final_dir = runtime_manager.promote_staging_to_version(staging_dir, detected_version)

                self._scrcpyPrepared.emit({
                    "version": detected_version,
                    "runtime_dir": str(final_dir),
                    "op_id": op_id,
                })
            except Exception as exc:
                self.logs.log("ERROR", f"Scrcpy update failed: {exc}")
                self._scrcpyStatusChanged.emit("error", str(exc))

        Thread(target=run_scrcpy_fetch, daemon=True).start()

    @Slot()
    def dismissDeckNotification(self):
        self._notifications["deck"]["visible"] = False
        version = self._notifications["deck"].get("latest_version")
        dismissed = list(self._version_prefs.get("dismissed_deck_notifications", []))
        if version and version not in dismissed:
            dismissed.append(version)
            self._version_prefs["dismissed_deck_notifications"] = dismissed
            set_version_preference("dismissed_deck_notifications", dismissed, self._profile_dir)
        self.notificationsChanged.emit()

    @Slot()
    def dismissScrcpyNotification(self):
        self._notifications["scrcpy"]["visible"] = False
        version = self._notifications["scrcpy"].get("latest_version")
        dismissed = list(self._version_prefs.get("dismissed_scrcpy_notifications", []))
        if version and version not in dismissed:
            dismissed.append(version)
            self._version_prefs["dismissed_scrcpy_notifications"] = dismissed
            set_version_preference("dismissed_scrcpy_notifications", dismissed, self._profile_dir)
        self.notificationsChanged.emit()

    @Slot(str, str)
    def openHelpSection(self, page, section):
        self.navigateToSection.emit(page, section)

    def startup(self):
        self.scan()
        QTimer.singleShot(400, lambda: self.checkAllUpdates(force=False))

    @Slot()
    def shutdown(self):
        self._closed = True
        self._catalog_generation += 1
        self._catalog_inflight = False
        self._catalog_pending.clear()
        self._catalog_cancel.set()
        self.stop.set()
        self._update_cancel.set()
        self._scrcpy_cancel.set()
        self.timer.stop()
        self.save()
