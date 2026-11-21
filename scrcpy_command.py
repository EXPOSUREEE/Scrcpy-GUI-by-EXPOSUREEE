"""Translate the persisted session profile to a shell-free scrcpy argument list with capability validation."""
from datetime import datetime

from runtime_capabilities import check_feature_support, get_all_capabilities


def build_scrcpy_command(settings: dict, capabilities: dict = None) -> list:
    """Build scrcpy command line, omitting unsupported optional flags and checking essential features."""
    scrcpy_exe = settings.get("scrcpy_exe", "scrcpy")
    scrcpy_ver = settings.get("scrcpy_version", "")
    caps = capabilities or (get_all_capabilities(scrcpy_ver, scrcpy_exe) if scrcpy_ver else {})

    cmd = [scrcpy_exe]
    serial = settings.get("device_serial")
    if serial:
        cmd.extend(["-s", serial])

    source = settings.get("source", "screen")
    screen_mode = settings.get("screen_mode", "")

    # OTG mode check
    if source == "screen" and screen_mode.startswith("OTG"):
        if caps and not caps.get("otg_mode", {}).get("supported", True):
            raise ValueError(caps["otg_mode"].get("reason", "OTG mode is not supported by this scrcpy runtime."))
        return [*cmd, "--otg"]

    camera = source in {"camera", "camera_back", "camera_front"}
    mic = source == "mic_only"

    # Essential feature validation
    if camera and caps and not caps.get("camera_source", {}).get("supported", True):
        raise ValueError(caps["camera_source"].get("reason", "Camera capture requires scrcpy 2.0 or newer."))

    if mic and caps and not caps.get("mic_only", {}).get("supported", True):
        raise ValueError(caps["mic_only"].get("reason", "Microphone capture requires scrcpy 2.0 or newer."))

    if mic:
        cmd.extend(["--no-video", "--audio-source=mic"])

    if camera:
        cmd.extend(["--video-source=camera", "--no-audio"])
        lens = settings.get("camera_id", "Default")
        if lens and lens != "Default":
            if not caps or caps.get("camera_id", {}).get("supported", True):
                cmd.append("--camera-id=" + lens.removeprefix("ID ").partition(":")[0].strip())
        elif source != "camera":
            if not caps or caps.get("camera_facing", {}).get("supported", True):
                cmd.append("--camera-facing=" + source.split("_")[1])

        aspect = settings.get("cam_ar", "Full Sensor (Default)")
        if aspect != "Full Sensor (Default)":
            if not caps or caps.get("camera_ar", {}).get("supported", True):
                cmd.append("--camera-ar=" + aspect)

        rotation = settings.get("cam_orientation", "0° (Default)").split("°")[0]
        if rotation in {"90", "180", "270"}:
            cmd.append("--orientation=" + rotation)

        # Optional camera features: only include if supported
        if settings.get("camera_torch"):
            if not caps or caps.get("camera_torch", {}).get("supported", True):
                cmd.append("--camera-torch")

        zoom = settings.get("camera_zoom", "1.0")
        if zoom and zoom != "1.0":
            if not caps or caps.get("camera_zoom", {}).get("supported", True):
                cmd.extend(["--camera-zoom", str(zoom)])

    if not mic:
        bitrate = settings.get("bitrate", "8")
        if bitrate:
            cmd.extend(["--video-bit-rate", f"{bitrate}M"])
        fps = settings.get("camera_fps", "30") if camera else settings.get("max_fps", "0")
        size = settings.get("camera_max_size" if camera else "max_size", "0")
        if fps and fps != "0":
            if not camera or not caps or caps.get("camera_fps", {}).get("supported", True):
                cmd.extend(["--camera-fps" if camera else "--max-fps", fps])
        if size and size != "0":
            cmd.extend(["--max-size", size])

        if not camera:
            codec = settings.get("video_codec", "h264")
            if codec != "h264":
                if codec == "h265" and caps and not caps.get("codec_h265", {}).get("supported", True):
                    pass  # Safely omit or fallback
                elif codec == "av1" and caps and not caps.get("codec_av1", {}).get("supported", True):
                    pass  # Safely omit or fallback
                else:
                    cmd.extend(["--video-codec", codec])

    if not camera:
        if settings.get("no_audio") and not mic:
            cmd.append("--no-audio")
        elif settings.get("audio_codec", "opus") != "opus":
            if not caps or caps.get("audio_codec", {}).get("supported", True):
                cmd.extend(["--audio-codec", settings["audio_codec"]])

    if settings.get("record"):
        name = datetime.now().strftime("recording_%Y%m%d_%H%M%S_%f.mp4")
        cmd.extend(["--record", name])

    if settings.get("renderer", "auto") != "auto":
        cmd.extend(["--render-driver", settings["renderer"]])

    if not camera and not mic:
        orientation = settings.get("orientation", "").partition("(@")[2].rstrip(")")
        if orientation in {"0", "90", "180", "270"}:
            if not caps or caps.get("capture_orientation", {}).get("supported", True):
                cmd.append("--capture-orientation=@" + orientation)

        if settings.get("no_control"):
            cmd.append("--no-control")
        else:
            if screen_mode == "UHID":
                if caps and not caps.get("uhid_input", {}).get("supported", True):
                    raise ValueError(caps["uhid_input"].get("reason", "UHID mode is not supported by this scrcpy runtime."))
                cmd.extend(["--keyboard=uhid", "--mouse=uhid"])

            for key, flag, cap_key in (
                ("stay_awake", "--stay-awake", "stay_awake"),
                ("screen_off", "--turn-screen-off", "turn_screen_off"),
                ("show_touches", "--show-touches", "show_touches"),
            ):
                if settings.get(key, key == "stay_awake"):
                    if not caps or caps.get(cap_key, {}).get("supported", True):
                        cmd.append(flag)

    for key, flag in (
        ("always_on_top", "--always-on-top"),
        ("borderless", "--window-borderless"),
        ("fullscreen", "--fullscreen"),
    ):
        if settings.get(key) and not (mic and key == "fullscreen"):
            cmd.append(flag)

    return cmd
