"""Per-user settings with backwards-compatible import of the v4 JSON file."""
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

DEFAULTS = {
    "ip": "", "source": "screen", "bitrate": "8", "max_fps": "0", "max_size": "0",
    "video_codec": "h264", "audio_codec": "opus", "cam_ar": "Full Sensor (Default)",
    "cam_orientation": "0° (Default)", "renderer": "software",
    "orientation": "Auto (Rotate with Phone)", "always_on_top": False,
    "stay_awake": True, "screen_off": False, "show_touches": False, "no_audio": False,
    "fullscreen": False, "borderless": False, "no_control": False, "record": False,
    "debug_mode": False, "screen_mode": "HID", "camera_id": "Default",
    "camera_torch": False, "camera_zoom": "1.0", "camera_max_size": "0", "camera_fps": "30",
}


def normalize(key, value):
    """Accept Tk string/boolean representations written by earlier releases."""
    if isinstance(DEFAULTS[key], bool):
        return value is True or str(value).lower() in {"1", "true", "yes", "on"}
    if value is None or not isinstance(value, (str, int, float)):
        return DEFAULTS[key]
    if key == "screen_mode":
        return next((mode for mode in ("OTG", "UHID") if str(value).upper().startswith(mode)), "HID")
    return str(value)


class SettingsStore:
    def __init__(self, path: Path, legacy: Path):
        self.path = path
        self.values = DEFAULTS.copy()
        self.saved = []
        self.extra = {}
        self.error = ""
        self.dirty = False
        source = path if path.exists() else legacy
        if not source.is_file():
            return
        try:
            data = json.loads(source.read_text(encoding="utf-8-sig"))
            if not isinstance(data, dict):
                raise ValueError("Expected a JSON object")
            records = data.get("saved_devices", [])
            if not isinstance(records, list) or not all(isinstance(d, dict) for d in records):
                raise ValueError("Invalid saved device list")
            self.saved = records
            self.values.update({k: normalize(k, data[k]) for k in DEFAULTS if k in data})
            self.extra = {k: v for k, v in data.items() if k not in DEFAULTS and k != "saved_devices"}
            self.dirty = source != path
        except (ValueError, OSError) as exc:
            self.error = f"Could not read {source}: {exc}"

    def save(self):
        """Replace the profile only after the complete new file has been flushed."""
        if not self.dirty:
            return
        if self.error:
            raise OSError(self.error)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {**self.extra, **self.values, "saved_devices": self.saved}
        temporary = None
        try:
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                    prefix=".config-", delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(self.path)
            self.dirty = False
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
