"""Bounded, event-driven console output for process and worker diagnostics."""
from collections import deque
from datetime import datetime
from threading import Lock

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Signal, Slot


def infer_fix_hint(message):
    lowered = message.lower()
    if "adb" in lowered and ("not recognized" in lowered or "not responding" in lowered or "no such file" in lowered or "cannot find" in lowered):
        return "Make sure adb.exe is next to this app or available in PATH."
    if "scrcpy" in lowered and ("not recognized" in lowered or "no such file" in lowered or "cannot find" in lowered):
        return "Make sure scrcpy.exe is next to this app or available in PATH."
    if "unauthorized" in lowered:
        return "Unlock the phone and accept the USB debugging authorization prompt, then scan again."
    if "no devices" in lowered or "device not found" in lowered:
        return "Connect the phone by USB, enable USB debugging, and tap 'Scan devices' again."
    if "failed to connect" in lowered or "unable to connect" in lowered or "connection failed" in lowered:
        return "Check that phone and PC are on the same Wi-Fi, the IP is correct, and TCP/IP mode is enabled on port 5555."
    if "could not find ip" in lowered or "wlan0" in lowered:
        return "Turn Wi-Fi on for the phone and keep the USB connection active while fetching the address."
    if "access is denied" in lowered:
        return "Try running the app as administrator and confirm no other tool is locking adb or scrcpy."
    if "more than one device" in lowered:
        return "Disconnect extra devices or keep using the selected serial with the device chooser."
    if "capture/encoding error" in lowered:
        return "Camera or screen capture failed on this resolution/aspect-ratio. Try setting a lower 'Max size' (e.g. 1920 or 1080) in Settings, or check if the camera is already in use by another app."
    return None


class ConsoleModel(QAbstractListModel):
    wake = Signal()
    limit = 2000

    def __init__(self):
        super().__init__()
        self.rows = []
        self.pending = deque(maxlen=self.limit)
        self.lock = Lock()
        self.wake.connect(self.flush, Qt.QueuedConnection)

    def roleNames(self):
        return {Qt.UserRole: b"line", Qt.UserRole + 1: b"severity"}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def data(self, index, role):
        if index.isValid() and role in (Qt.UserRole, Qt.UserRole + 1):
            return self.rows[index.row()][role - Qt.UserRole]
        return None

    def log(self, level, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        with self.lock:
            notify = not self.pending
            for line in str(message).splitlines():
                self.pending.append((f"{timestamp}  {level:<5}  {line}", level))
        if notify:
            self.wake.emit()

    @Slot()
    def flush(self):
        with self.lock:
            batch = list(self.pending)
            self.pending.clear()
        if not batch:
            return
        excess = len(self.rows) + len(batch) - self.limit
        if excess > 0:
            self.beginRemoveRows(QModelIndex(), 0, excess - 1)
            del self.rows[:excess]
            self.endRemoveRows()
        self.beginInsertRows(QModelIndex(), len(self.rows), len(self.rows) + len(batch) - 1)
        self.rows.extend(batch)
        self.endInsertRows()

    @Slot()
    def clear(self):
        self.flush()
        self.beginResetModel()
        self.rows.clear()
        self.endResetModel()

    @Slot(result=str)
    def transcript(self):
        return "\n".join(row[0] for row in self.rows)

