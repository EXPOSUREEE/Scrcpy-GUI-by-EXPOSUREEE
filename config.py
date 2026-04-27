import json
import os
import customtkinter as ctk

CONFIG_FIELDS = {
    "ip": ("var_ip", "StringVar", ""),
    "source": ("var_source", "StringVar", "screen"),
    "bitrate": ("var_bitrate", "StringVar", "8"),
    "max_fps": ("var_max_fps", "StringVar", "0"),
    "max_size": ("var_max_size", "StringVar", "0"),
    "video_codec": ("var_video_codec", "StringVar", "h264"),
    "audio_codec": ("var_audio_codec", "StringVar", "opus"),
    "cam_ar": ("cam_ar_combo_val", "StringVar", "Full Sensor (Default)"),
    "renderer": ("renderer_combo_val", "StringVar", "software"),
    "orientation": ("orientation_combo_val", "StringVar", "Auto (Rotate with Phone)"),
    "always_on_top": ("var_always_on_top", "BooleanVar", False),
    "stay_awake": ("var_stay_awake", "BooleanVar", True),
    "screen_off": ("var_screen_off", "BooleanVar", False),
    "show_touches": ("var_show_touches", "BooleanVar", False),
    "no_audio": ("var_no_audio", "BooleanVar", False),
    "fullscreen": ("var_fullscreen", "BooleanVar", False),
    "borderless": ("var_borderless", "BooleanVar", False),
    "no_control": ("var_no_control", "BooleanVar", False),
    "record": ("var_record", "BooleanVar", False),
    "debug_mode": ("var_debug_mode", "BooleanVar", False)
}

def init_config_vars(target_obj):
    """Initializes Tkinter variables on the target object."""
    for key, (var_name, var_type, default_val) in CONFIG_FIELDS.items():
        if var_type == "StringVar":
            setattr(target_obj, var_name, ctk.StringVar(value=default_val))
        elif var_type == "BooleanVar":
            setattr(target_obj, var_name, ctk.BooleanVar(value=default_val))

def load_config(target_obj, config_file):
    """Loads configuration from file into the target object's variables."""
    if not os.path.exists(config_file):
        return
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        for key, (var_name, _, _) in CONFIG_FIELDS.items():
            if key in config:
                getattr(target_obj, var_name).set(config[key])
    except Exception as e:
        print(f"Error loading config: {e}")

def save_config(target_obj, config_file):
    """Saves the target object's variables to the configuration file."""
    config = {}
    for key, (var_name, _, _) in CONFIG_FIELDS.items():
        config[key] = getattr(target_obj, var_name).get()
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f)
    except Exception as e:
        print(f"Error saving config: {e}")
