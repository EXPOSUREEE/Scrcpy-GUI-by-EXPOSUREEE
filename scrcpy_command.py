from datetime import datetime

def build_scrcpy_command(settings: dict) -> list:
    """
    Builds the scrcpy command line based on the provided settings dictionary.
    
    settings expected keys:
        - scrcpy_exe (str): path to scrcpy executable
        - device_serial (str): serial of the connected device
        - source (str)
        - cam_ar (str)
        - bitrate (str)
        - max_fps (str)
        - max_size (str)
        - video_codec (str)
        - audio_codec (str)
        - no_audio (bool)
        - record (bool)
        - renderer (str)
        - orientation (str)
        - always_on_top (bool)
        - borderless (bool)
        - fullscreen (bool)
        - stay_awake (bool)
        - screen_off (bool)
        - show_touches (bool)
        - no_control (bool)
    """
    scrcpy_exe = settings.get("scrcpy_exe", "scrcpy")
    device_serial = settings.get("device_serial", "")
    
    cmd = [scrcpy_exe]
    if device_serial:
        cmd.extend(["-s", device_serial])
        
    source = settings.get("source", "screen")
    is_camera = (source == "camera_back" or source == "camera_front")
    is_mic_only = (source == "mic_only")

    # --- SOURCE LOGIC ---
    if is_mic_only:
        cmd.extend(["--no-video", "--audio-source=mic"])
    elif is_camera:
        cmd.append("--video-source=camera")
        if source == "camera_back":
            cmd.append("--camera-facing=back")
        else:
            cmd.append("--camera-facing=front")
        cmd.append("--no-audio") 
        
        cam_ar = settings.get("cam_ar", "Full Sensor (Default)")
        if cam_ar != "Full Sensor (Default)":
            cmd.append(f"--camera-ar={cam_ar}")
    
    # --- VIDEO & AUDIO SETTINGS ---
    if not is_mic_only: 
        bitrate = settings.get("bitrate", "8").strip()
        if bitrate: cmd.extend(["--video-bit-rate", f"{bitrate}M"])
        
        max_fps = settings.get("max_fps", "0").strip()
        if max_fps and max_fps != "0": cmd.extend(["--max-fps", max_fps])
        
        max_size = settings.get("max_size", "0").strip()
        if max_size and max_size != "0": cmd.extend(["--max-size", max_size])
        
        vid_codec = settings.get("video_codec", "h264")
        if vid_codec != "h264": cmd.extend(["--video-codec", vid_codec])
        
    if not is_camera and not settings.get("no_audio", False):
        aud_codec = settings.get("audio_codec", "opus")
        if aud_codec != "opus": cmd.extend(["--audio-codec", aud_codec])
        
    # --- RECORDING ---
    if settings.get("record", False):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}.mp4"
        cmd.extend(["--record", filename])

    # --- RENDERER & WINDOW ---
    renderer = settings.get("renderer", "auto")
    if renderer != "auto":
        cmd.extend(["--render-driver", renderer])
        
    orient = settings.get("orientation", "Auto (Rotate with Phone)")
    if "Portrait (@0)" in orient: cmd.extend(["--capture-orientation=@0"])
    elif "Landscape (@90)" in orient: cmd.extend(["--capture-orientation=@90"])
    elif "Portrait Reversed (@180)" in orient: cmd.extend(["--capture-orientation=@180"])
    elif "Landscape Reversed (@270)" in orient: cmd.extend(["--capture-orientation=@270"])
    
    if settings.get("always_on_top", False): cmd.append("--always-on-top")
    if settings.get("borderless", False): cmd.append("--window-borderless")
    if settings.get("fullscreen", False) and not is_mic_only: cmd.append("--fullscreen")
    
    # --- DEVICE BEHAVIOR ---
    if not is_camera and not is_mic_only:
        if settings.get("stay_awake", True): cmd.append("--stay-awake")
        if settings.get("screen_off", False): cmd.append("--turn-screen-off")
        if settings.get("show_touches", False): cmd.append("--show-touches")
        if settings.get("no_control", False): cmd.append("--no-control")
    
    if not is_camera and not is_mic_only and settings.get("no_audio", False):
        cmd.append("--no-audio")

    return cmd
