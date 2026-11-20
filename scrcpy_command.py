"""Translate the persisted session profile to a shell-free scrcpy argument list."""
from datetime import datetime


def build_scrcpy_command(settings: dict) -> list:
    cmd = [settings.get("scrcpy_exe", "scrcpy")]
    serial = settings.get("device_serial")
    if serial:
        cmd.extend(["-s", serial])
    source = settings.get("source", "screen")
    if source == "screen" and settings.get("screen_mode", "").startswith("OTG"):
        return [*cmd, "--otg"]

    camera = source in {"camera", "camera_back", "camera_front"}
    mic = source == "mic_only"
    if mic:
        cmd.extend(["--no-video", "--audio-source=mic"])
    if camera:
        cmd.extend(["--video-source=camera", "--no-audio"])
        lens = settings.get("camera_id", "Default")
        if lens and lens != "Default":
            cmd.append("--camera-id=" + lens.removeprefix("ID ").partition(":")[0].strip())
        elif source != "camera":
            cmd.append("--camera-facing=" + source.split("_")[1])
        aspect = settings.get("cam_ar", "Full Sensor (Default)")
        if aspect != "Full Sensor (Default)":
            cmd.append("--camera-ar=" + aspect)
        rotation = settings.get("cam_orientation", "0° (Default)").split("°")[0]
        if rotation in {"90", "180", "270"}:
            cmd.append("--orientation=" + rotation)
        if settings.get("camera_torch"):
            cmd.append("--camera-torch")
        zoom = settings.get("camera_zoom", "1.0")
        if zoom and zoom != "1.0":
            cmd.extend(["--camera-zoom", zoom])

    if not mic:
        bitrate = settings.get("bitrate", "8")
        if bitrate:
            cmd.extend(["--video-bit-rate", f"{bitrate}M"])
        fps = settings.get("camera_fps", "30") if camera else settings.get("max_fps", "0")
        size = settings.get("camera_max_size" if camera else "max_size", "0")
        if fps and fps != "0":
            cmd.extend(["--camera-fps" if camera else "--max-fps", fps])
        if size and size != "0":
            cmd.extend(["--max-size", size])
        if not camera and settings.get("video_codec", "h264") != "h264":
            cmd.extend(["--video-codec", settings["video_codec"]])
    if not camera:
        if settings.get("no_audio") and not mic:
            cmd.append("--no-audio")
        elif settings.get("audio_codec", "opus") != "opus":
            cmd.extend(["--audio-codec", settings["audio_codec"]])
    if settings.get("record"):
        name = datetime.now().strftime("recording_%Y%m%d_%H%M%S_%f.mp4")
        cmd.extend(["--record", name])
    if settings.get("renderer", "auto") != "auto":
        cmd.extend(["--render-driver", settings["renderer"]])
    if not camera and not mic:
        orientation = settings.get("orientation", "").partition("(@")[2].rstrip(")")
        if orientation in {"0", "90", "180", "270"}:
            cmd.append("--capture-orientation=@" + orientation)
        if settings.get("no_control"):
            cmd.append("--no-control")
        else:
            if settings.get("screen_mode") == "UHID":
                cmd.extend(["--keyboard=uhid", "--mouse=uhid"])
            for key, flag in (("stay_awake", "--stay-awake"), ("screen_off", "--turn-screen-off"),
                              ("show_touches", "--show-touches")):
                if settings.get(key, key == "stay_awake"):
                    cmd.append(flag)
    for key, flag in (("always_on_top", "--always-on-top"), ("borderless", "--window-borderless"),
                      ("fullscreen", "--fullscreen")):
        if settings.get(key) and not (mic and key == "fullscreen"):
            cmd.append(flag)
    return cmd
