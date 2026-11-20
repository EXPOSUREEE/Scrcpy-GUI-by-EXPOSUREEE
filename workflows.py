"""Connection sequences executed away from the GUI thread."""
from adb import DeviceError
from library import endpoint


class Connections:
    def __init__(self, adb, cancelled):
        self.adb = adb
        self.cancelled = cancelled

    def set_adb(self, adb):
        self.adb = adb

    def connect(self, target, promote=True, hardware=""):
        self.adb.connect(target)
        if hardware:
            devices = self._authorized(target)
            identity = next(d.hardware_serial for d in devices if d.serial == target)
            if identity != hardware:
                raise DeviceError("The wireless endpoint could not be identified as the saved phone. Recover over USB or edit its address.")
        if promote and ":" in target and not target.endswith(":5555"):
            stable = target.rpartition(":")[0] + ":5555"
            try:
                self.adb.tcpip(target)
                self._retry_connect(stable)
                target = stable
            except DeviceError as exc:
                self.adb.log("WARN", f"Could not enable port 5555. Checking the original connection. {exc}")
        return target, self._authorized(target)

    def _authorized(self, target):
        for attempt in range(3):
            devices = self.adb.scan()
            if any(d.serial == target and d.state == "device" for d in devices):
                return devices
            if attempt < 2:
                self.cancelled.wait(0.5)
        raise DeviceError(f"{target} is missing from the authorized ADB device list. Scan again.")

    def _retry_connect(self, target):
        for attempt in range(3):
            if self.cancelled.wait(0.5):
                raise DeviceError("Cancelled")
            try:
                self.adb.connect(target)
                return
            except DeviceError:
                if attempt == 2:
                    raise

    def recover(self, record):
        hardware = record.get("hardware_serial")
        while not self.cancelled.is_set():
            usb = [d for d in self.adb.scan() if d.transport == "usb" and d.state == "device"]
            matches = [d for d in usb if hardware == d.hardware_serial] if hardware else usb
            if len(matches) == 1:
                serial = matches[0].serial
                target = endpoint(self.adb.wifi_ip(serial), "5555")
                if self.cancelled.is_set():
                    break
                self.adb.tcpip(serial)
                self._retry_connect(target)
                return target, self._authorized(target)
            self.cancelled.wait(2)
        raise DeviceError("Recovery cancelled")
