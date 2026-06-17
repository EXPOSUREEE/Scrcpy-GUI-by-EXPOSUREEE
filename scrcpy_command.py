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
    
    # --- Check for OTG mode first ---
    if settings.get("screen_mode") == "OTG":
        cmd = [scrcpy_exe, "--otg"]
        if device_serial:
            cmd.extend(["-s", device_serial])
        return cmd

    cmd = [scrcpy_exe]
    if device_serial:
        cmd.extend(["-s", device_serial])
        
    source = settings.get("source", "screen")
    is_camera = (source == "camera_back" or source == "camera_front" or source == "camera")
    is_mic_only = (source == "mic_only")

    # --- SOURCE LOGIC ---
    if is_mic_only:
        cmd.extend(["--no-video", "--audio-source=mic"])
    elif is_camera:
        cmd.append("--video-source=camera")
        
        # Check camera lens ID selection
        camera_id_setting = settings.get("camera_id", "Default")
        if camera_id_setting and camera_id_setting != "Default":
            if camera_id_setting.startswith("ID "):
                try:
                    camera_id = camera_id_setting.split(":")[0].replace("ID ", "").strip()
                except Exception:
                    camera_id = camera_id_setting
            else:
                camera_id = camera_id_setting
            cmd.append(f"--camera-id={camera_id}")
        else:
            if source == "camera_back":
                cmd.append("--camera-facing=back")
            elif source == "camera_front":
                cmd.append("--camera-facing=front")
                
        cmd.append("--no-audio") 
        
        cam_ar = settings.get("cam_ar", "Full Sensor (Default)")
        if cam_ar != "Full Sensor (Default)":
            cmd.append(f"--camera-ar={cam_ar}")
            
        cam_orient = settings.get("cam_orientation", "0° (Default)")
        if "90" in cam_orient:
            cmd.append("--orientation=90")
        elif "180" in cam_orient:
            cmd.append("--orientation=180")
        elif "270" in cam_orient:
            cmd.append("--orientation=270")

        # Camera Torch
        if settings.get("camera_torch", False):
            cmd.append("--camera-torch")

        # Camera Zoom
        cam_zoom = settings.get("camera_zoom", "1.0").strip()
        if cam_zoom and cam_zoom != "1.0":
            cmd.extend(["--camera-zoom", cam_zoom])

        # Camera Resolution Limit
        cam_max_size = settings.get("camera_max_size", "0").strip()
        if cam_max_size and cam_max_size != "0":
            cmd.extend(["--max-size", cam_max_size])

        # Camera FPS Limit
        cam_fps = settings.get("camera_fps", "30").strip()
        if cam_fps and cam_fps != "0":
            cmd.extend(["--max-fps", cam_fps])

        # Camera Bitrate
        bitrate = settings.get("bitrate", "8").strip()
        if bitrate: cmd.extend(["--video-bit-rate", f"{bitrate}M"])
    
    # --- VIDEO & AUDIO SETTINGS ---
    if not is_mic_only and not is_camera: 
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
