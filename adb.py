"""Blocking ADB operations. The frontend calls these on a worker thread."""
import re
import subprocess
from pathlib import Path

from device_names import DeviceInfo, build_display_name, load_device_name_map

HIDDEN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class DeviceError(RuntimeError):
    """An actionable command or device error for the operator."""


class AdbManager:
    def __init__(self, adb_exe, resources, log):
        self.exe = str(adb_exe)
        self.mapping = load_device_name_map(resources)
        self.log = log
        self._cache = {}

    def run(self, args, quiet=False, input_text=None):
        if not quiet:
            self.log("INFO", subprocess.list2cmdline(["adb", *args]))
        try:
            result = subprocess.run([self.exe, *args], capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", timeout=15,
                                    creationflags=HIDDEN, input=input_text)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise DeviceError(f"adb {args[0]} failed: {exc}") from exc
        output = "\n".join(s.strip() for s in (result.stdout, result.stderr) if s.strip())
        if result.returncode:
            raise DeviceError(output or f"adb exited with code {result.returncode}")
        if not quiet and output:
            self.log("OUT", output)
        return output

    def scan(self):
        devices = []
        present = {}
        for line in self.run(["devices", "-l"]).splitlines():
            parts = line.split()
            if len(parts) < 2 or parts[1] not in {"device", "offline", "unauthorized", "recovery", "sideload"}:
                continue
            serial, state = parts[:2]
            tags = dict(part.split(":", 1) for part in parts[2:] if ":" in part)
            transport = ("emulator" if serial.startswith("emulator-") else
                         "wireless" if ":" in serial or "_adb-tls-" in serial else "usb")
            key = (serial, tags.get("transport_id"))
            if state == "device" and key in self._cache:
                info = self._cache[key]
                present[key] = info
            else:
                info = DeviceInfo(serial, state, transport, model=tags.get("model", ""),
                                  product=tags.get("product", ""), device=tags.get("device", ""))
                if state == "device":
                    try:
                        output = self.run(["-s", serial, "shell", "getprop"], quiet=True)
                        props = dict(re.findall(r"^\[([^]]+)\]: \[(.*?)\]\s*$", output, re.M))
                        info.hardware_serial = props.get("ro.serialno") or (serial if transport == "usb" else "")
                        info.brand = props.get("ro.product.brand", "")
                        info.manufacturer = props.get("ro.product.manufacturer", "")
                        info.model = props.get("ro.product.model") or info.model or props.get("ro.vendor.product.model") or props.get("ro.product.vendor.model", "")
                        info.product = props.get("ro.product.name") or info.product
                        info.device = props.get("ro.product.device") or info.device
                        info.market_name = next((props[p] for p in (
                            "ro.product.marketname", "ro.config.marketing_name",
                            "ro.vendor.oplus.market.name", "ro.miui.device.name"
                        ) if props.get(p)), "")
                        present[key] = info
                    except DeviceError as exc:
                        self.log("WARN", str(exc))
                build_display_name(info, self.mapping)
            devices.append(info)
        self._cache = present
        return devices

    def wifi_ip(self, serial):
        output = self.run(["-s", serial, "shell", "ip", "-f", "inet", "addr", "show", "wlan0"])
        match = re.search(r"\binet (\d+\.\d+\.\d+\.\d+)", output)
        if not match:
            raise DeviceError("Could not find IP on wlan0. Connect the phone to Wi-Fi.")
        return match[1]

    def tcpip(self, serial):
        self.run(["-s", serial, "tcpip", "5555"])

    def connect(self, target):
        output = self.run(["connect", target])
        if not re.search(r"^(already )?connected to ", output, re.I | re.M):
            raise DeviceError(output or f"Failed to connect to {target}")

    def pair(self, target, code):
        output = self.run(["pair", target], input_text=code + "\n")
        if "successfully paired" not in output.lower():
            raise DeviceError(output or "Pairing failed. Request a fresh code on the phone.")

    def discover(self, ip, cancelled):
        for attempt in range(5):
            if cancelled.is_set():
                break
            for line in self.run(["mdns", "services"]).splitlines():
                if "_adb-tls-connect._tcp" in line:
                    match = re.search(r"\b" + re.escape(ip) + r":(\d+)\b", line)
                    if match:
                        return match[1]
            if attempt < 4:
                cancelled.wait(1.5)
        raise DeviceError("No matching mDNS service. Enter the connect port from Wireless debugging.")

    def reset(self):
        self.run(["disconnect"])
        self.run(["kill-server"])
        try:
            for name in ("adbkey", "adbkey.pub"):
                (Path.home() / ".android" / name).unlink(missing_ok=True)
        finally:
            self.run(["start-server"])
