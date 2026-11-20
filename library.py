"""Merge live transports with legacy saved device records without losing user edits."""
import ipaddress


def address(value):
    try:
        return str(ipaddress.IPv4Address(value.strip()))
    except ValueError as exc:
        raise ValueError("Enter the phone's Wi-Fi IPv4 address.") from exc


def endpoint(ip, port):
    ip = address(ip)
    if not port.isascii() or not port.isdecimal() or not 1 <= int(port) <= 65535:
        raise ValueError("Enter a port between 1 and 65535.")
    return f"{ip}:{port}"


def _matches(entry, device, ip):
    kind = entry.get("type", "usb")
    if kind == "usb" and entry.get("serial", "").startswith("emulator-"):
        kind = "emulator"
    if kind != device.transport:
        return False
    if entry.get("hardware_serial") and device.hardware_serial:
        return entry["hardware_serial"] == device.hardware_serial
    return entry.get("serial") == device.serial or bool(ip and entry.get("ip") == ip)


def merge_devices(saved, devices):
    changed = False
    seen = set()
    # A paired phone may be advertised under its mDNS name and numeric ports.
    # Keep the stable endpoint when several aliases are in the same scan.
    for device in sorted(devices, key=lambda d: (not d.serial.endswith(":5555"), ":" not in d.serial)):
        if device.state != "device":
            continue
        identity = (device.transport, device.hardware_serial or device.serial)
        if identity in seen:
            continue
        seen.add(identity)
        ip = device.serial.rpartition(":")[0] if device.transport == "wireless" else ""
        kind = device.transport
        entry = next((d for d in saved if _matches(d, device, ip)), None)
        if entry is None:
            entry = {"nickname": ""}
            saved.append(entry)
        preserve_endpoint = kind == "wireless" and not ip and entry.get("ip") and ":" in entry.get("serial", "")
        fields = dict(serial=entry["serial"] if preserve_endpoint else device.serial,
                      ip=ip or entry.get("ip", ""), type=kind,
                      brand=device.brand, model=device.model, display_name=device.display_name,
                      hardware_serial=device.hardware_serial or entry.get("hardware_serial", ""))
        if any(entry.get(k) != v for k, v in fields.items()):
            entry.update(fields)
            changed = True
    return changed
