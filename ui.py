import tkinter as tk
import tkinter.font as tkfont
import customtkinter as ctk
from tkinter import messagebox
import subprocess
import threading
import os
import sys
import re
import urllib.request
import urllib.error
import urllib.parse
import webbrowser
import tempfile
from datetime import datetime

import config
from assets import AssetManager
from console import ConsoleManager
from adb import AdbManager
from scrcpy_command import build_scrcpy_command

# --- CONFIGURATION ---
PROGRAM_TITLE = "Scrcpy GUI Pro"
CURRENT_VERSION = "4.0.0"
UPDATE_URL = "https://exposureee.in/wp-content/uploads/2024/08/Scrcpy_GUI_by_EXPOSUREEE-Version.txt"
DOWNLOAD_URL = "https://exposureee.in/scrcpy-gui-by-exposureee/"
TUTORIAL_URL = "https://www.youtube.com/watch?v=pWKY_dntX5c"
UPI_ID = "exposureee@upi"
PAYEE_NAME = "Abhishek Mishra"

# --- UI THEME ---
APP_BG = "#050816"
SHELL_BG = "#09102a"
SIDEBAR_BG = "#0b1333"
PANEL_BG = "#10183d"
CARD_BG = "#151f4f"
CARD_HOVER = "#1c2860"
FIELD_BG = "#0b1331"
BORDER = "#28366c"
TEXT = "#f7f9ff"
MUTED_TEXT = "#9faddf"
ACCENT = "#7d5cff"
ACCENT_HOVER = "#9277ff"
ACCENT_ALT = "#35d6ff"
GUIDE_BG = "#0A2E1F"
GUIDE_BORDER = "#145239"
SUCCESS = "#28d78a"
SUCCESS_HOVER = "#1fb977"
WARNING = "#ff8b6b"
CONSOLE_INFO = "#9faddf"
CONSOLE_OUT = "#f7f9ff"
CONSOLE_WARN = "#ffcf66"
CONSOLE_ERR = "#ff8b6b"
CONSOLE_HINT = "#35d6ff"

def version_tuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v))

class ScrcpyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{PROGRAM_TITLE} v{CURRENT_VERSION}")
        self.root.geometry("1360x860")
        self.root.minsize(1080, 680)

        if getattr(sys, 'frozen', False):
            self.script_dir = os.path.dirname(sys.executable)
        else:
            self.script_dir = os.path.dirname(os.path.abspath(__file__))

        self.scrcpy_exe = os.path.join(self.script_dir, "scrcpy.exe")
        self.adb_exe = os.path.join(self.script_dir, "adb.exe")
        self.config_file = os.path.join(self.script_dir, "config.json")
        self.assets_dir = os.path.join(self.script_dir, "assets")
        self.font_dir = os.path.join(self.script_dir, "fonts")
        
        if not os.path.exists(self.scrcpy_exe):
            self.scrcpy_exe = "scrcpy"
        if not os.path.exists(self.adb_exe):
            self.adb_exe = "adb"

        self.asset_mgr = AssetManager(self.root, self.script_dir, self.assets_dir)
        self.console_mgr = ConsoleManager(self.append_console, self.script_dir)
        self.adb = AdbManager(self.adb_exe, self.script_dir, self.console_mgr)

        self.init_theme()

        # Variables
        config.init_config_vars(self)
        self.status_var = ctk.StringVar(value="Ready for a fresh mirror session.")
        self.connection_summary_var = ctk.StringVar(value="Waiting for your first device scan")
        self.guidance_step_var = ctk.StringVar(value="Step 1 of 5")
        self.guidance_title_var = ctk.StringVar(value="Connect your phone by USB")
        self.guidance_detail_var = ctk.StringVar(value="Unlock the phone, allow USB debugging, then scan for devices.")
        self.source_summary_var = ctk.StringVar()
        self.quality_summary_var = ctk.StringVar()
        self.audio_summary_var = ctk.StringVar()
        self.window_summary_var = ctk.StringVar()
        self.extras_summary_var = ctk.StringVar()
        self.device_count_var = ctk.StringVar(value="0")
        self.source_metric_var = ctk.StringVar(value="Screen")
        self.source_metric_detail_var = ctk.StringVar(value="Software renderer")
        self.recording_status_var = ctk.StringVar(value="Off")
        self.recording_detail_var = ctk.StringVar(value="MP4 capture idle")
        
        self.workflow_tcpip_enabled = False
        self.workflow_wireless_ready = False
        self.workflow_issue_message = ""
        self.workflow_issue_hint = ""
        self.workflow_issue_action = None
        self.workflow_issue_action_label = ""
        self.active_processes = []
        
        config.load_config(self, self.config_file)
        self.attach_variable_traces()
        self.create_widgets()
        self.refresh_dashboard_state()
        self.refresh_devices()
        
        threading.Thread(target=self.check_for_updates, daemon=True).start()

    def init_theme(self):
        self.root.configure(fg_color=APP_BG)
        self.root.configure(bg=APP_BG)
        self.load_local_fonts()
        self.font_family = self.pick_font("Nunito", "Nunito Medium", "Segoe UI Variable Text", "Segoe UI", "Arial")
        self.font_title_family = self.pick_font("Quicksand", "Nunito ExtraBold", "Nunito Black", "Nunito", "Segoe UI Variable Display", self.font_family)
        self.font_metric_family = self.pick_font("Nunito Black", "Nunito ExtraBold", "Nunito", self.font_title_family)
        self.font_ui_accent_family = self.pick_font("Quicksand", "Nunito SemiBold", "Nunito", "Segoe UI Variable Text", self.font_family)
        self.font_caption_family = self.pick_font("Nunito Medium", "Nunito", self.font_family)
        self.font_mono_family = self.pick_font("Cascadia Code", "Consolas", "Courier New", self.font_family)
        self.root.option_add("*Font", f"{{{self.font_family}}} 12")
        self.fonts = {
            "hero": ctk.CTkFont(family=self.font_title_family, size=34, weight="bold"),
            "title": ctk.CTkFont(family=self.font_title_family, size=26, weight="bold"),
            "section": ctk.CTkFont(family=self.font_title_family, size=20, weight="bold"),
            "body": ctk.CTkFont(family=self.font_family, size=13),
            "body_bold": ctk.CTkFont(family=self.font_ui_accent_family, size=13, weight="bold"),
            "metric": ctk.CTkFont(family=self.font_metric_family, size=28, weight="bold"),
            "caption": ctk.CTkFont(family=self.font_caption_family, size=11),
            "caption_bold": ctk.CTkFont(family=self.font_ui_accent_family, size=11, weight="bold"),
            "console": ctk.CTkFont(family=self.font_mono_family, size=10),
            "button": ctk.CTkFont(family=self.font_ui_accent_family, size=13, weight="bold"),
            "button_large": ctk.CTkFont(family=self.font_ui_accent_family, size=15, weight="bold"),
        }
        self.apply_windows_chrome()

    def load_local_fonts(self):
        if not os.path.isdir(self.font_dir):
            return
        for font_name in os.listdir(self.font_dir):
            font_path = os.path.join(self.font_dir, font_name)
            if os.path.isfile(font_path) and font_name.lower().endswith((".ttf", ".otf")):
                self.register_windows_font(font_path)

    def register_windows_font(self, font_path):
        try:
            from ctypes import windll
            FR_PRIVATE = 0x10
            windll.gdi32.AddFontResourceExW(font_path, FR_PRIVATE, 0)
        except Exception:
            pass

    def pick_font(self, *candidates):
        available_fonts = set(tkfont.families(self.root))
        for font_name in candidates:
            if font_name in available_fonts:
                return font_name
        return "Arial"

    def apply_windows_chrome(self):
        try:
            from ctypes import byref, c_int, sizeof, windll
            self.root.update_idletasks()
            hwnd = self.root.winfo_id()
            value = c_int(1)
            for attribute in (20, 19):
                result = windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, byref(value), sizeof(value))
                if result == 0:
                    break
        except Exception:
            pass

    def resolve_tk_bg(self, widget):
        current = widget
        while current is not None:
            try:
                color = current.cget("fg_color")
            except Exception:
                current = getattr(current, "master", None)
                continue
            if isinstance(color, (tuple, list)):
                try:
                    color = current._apply_appearance_mode(color)
                except Exception:
                    color = color[0]
            if color and color != "transparent":
                return color
            current = getattr(current, "master", None)
        return APP_BG

    def create_logo_widget(self, parent, key, size=None):
        if self.asset_mgr.ctk_logo_images.get(key):
            return ctk.CTkLabel(parent, text="", image=self.asset_mgr.ctk_logo_images[key])
        if self.asset_mgr.logo_images.get(key):
            label = tk.Label(
                parent,
                image=self.asset_mgr.logo_images[key],
                bg=self.resolve_tk_bg(parent),
                bd=0,
                highlightthickness=0
            )
            return label
        fallback_text = "SE" if size is None or size >= 40 else ""
        return ctk.CTkLabel(parent, text=fallback_text, text_color=TEXT, font=self.fonts["button_large"])

    def attach_variable_traces(self):
        for var_name, _, _ in config.CONFIG_FIELDS.values():
            getattr(self, var_name).trace_add("write", lambda *_: self.refresh_dashboard_state())

    def refresh_dashboard_state(self):
        config.save_config(self, self.config_file)
        source_labels = {
            "screen": "Screen mirror",
            "camera_back": "Back camera",
            "camera_front": "Front camera",
            "mic_only": "Microphone only",
        }
        source_label = source_labels.get(self.var_source.get(), "Screen mirror")
        self.source_summary_var.set(f"{source_label} | Renderer {self.renderer_combo_val.get()}")
        self.source_metric_var.set({"screen": "Screen", "camera_back": "Back Cam", "camera_front": "Front Cam", "mic_only": "Mic Only"}.get(self.var_source.get(), "Screen"))
        self.source_metric_detail_var.set(f"{self.renderer_combo_val.get().title()} renderer")

        bitrate = self.var_bitrate.get().strip() or "8"
        fps = self.var_max_fps.get().strip()
        size = self.var_max_size.get().strip()
        fps_label = "Auto FPS" if not fps or fps == "0" else f"{fps} FPS"
        size_label = "Native size" if not size or size == "0" else f"{size}px max"
        self.quality_summary_var.set(f"{bitrate} Mbps | {fps_label} | {size_label} | {self.var_video_codec.get().upper()}")

        if self.var_source.get() in ("camera_back", "camera_front"):
            audio_label = "Audio muted for camera mode"
        elif self.var_source.get() == "mic_only":
            audio_label = f"Mic capture | {self.var_audio_codec.get().upper()}"
        elif self.var_no_audio.get():
            audio_label = "No audio"
        else:
            audio_label = f"Phone audio | {self.var_audio_codec.get().upper()}"
        self.audio_summary_var.set(audio_label)

        window_flags = []
        if self.var_fullscreen.get(): window_flags.append("Fullscreen")
        if self.var_borderless.get(): window_flags.append("Borderless")
        if self.var_always_on_top.get(): window_flags.append("Always on top")
        if self.var_no_control.get(): window_flags.append("View only")
        self.window_summary_var.set(", ".join(window_flags) if window_flags else "Standard interactive window")

        extras = []
        if self.var_record.get(): extras.append("MP4 recording armed")
        if self.var_debug_mode.get(): extras.append("Debug console on")
        if self.var_screen_off.get(): extras.append("Phone screen off")
        if self.var_show_touches.get(): extras.append("Touch trail on")
        self.extras_summary_var.set(" | ".join(extras) if extras else "Balanced preset with clean defaults")
        self.recording_status_var.set("Armed" if self.var_record.get() else "Off")
        self.recording_detail_var.set("MP4 on next launch" if self.var_record.get() else "MP4 capture idle")
        self.update_next_step_guidance()

    def set_status(self, message):
        self.status_var.set(message)

    def get_selected_device(self):
        if not hasattr(self, "device_combo"): return ""
        try: serial = self.device_combo.get().strip()
        except Exception: return ""
        if not serial or serial == "No devices found": return ""
        return serial

    def set_workflow_issue(self, message, hint="", action=None, action_label="Review next step"):
        self.workflow_issue_message = message
        self.workflow_issue_hint = hint
        self.workflow_issue_action = action
        self.workflow_issue_action_label = action_label
        self.update_next_step_guidance()

    def clear_workflow_issue(self):
        self.workflow_issue_message = ""
        self.workflow_issue_hint = ""
        self.workflow_issue_action = None
        self.workflow_issue_action_label = ""
        self.update_next_step_guidance()

    def run_guidance_action(self):
        action = getattr(self, "workflow_guidance_action", None)
        if callable(action): action()

    def run_guidance_action_2(self):
        action = getattr(self, "workflow_guidance_action_2", None)
        if callable(action): action()

    def update_next_step_guidance(self):
        serial = self.get_selected_device()
        ip = self.var_ip.get().strip()
        usb_ready = bool(serial)
        wireless_serial = f"{ip}:5555" if ip else ""
        wireless_ready = self.workflow_wireless_ready or (bool(serial) and ":" in serial) or (wireless_serial and wireless_serial == serial)

        if self.workflow_issue_message:
            detail = self.workflow_issue_message
            if self.workflow_issue_hint: detail = f"{detail}\n{self.workflow_issue_hint}"
            payload = {
                "step": "Needs attention", "title": "Something needs your input", "detail": detail,
                "action_label": self.workflow_issue_action_label or "Open Console",
                "action": self.workflow_issue_action or (lambda: self.switch_tab("Console")),
            }
        elif not usb_ready:
            payload = {
                "step": "Step 1 of 5", "title": "Connect your phone by USB",
                "detail": "1. Spam tap 'Build number' in Settings to unlock Developer Options.\n2. Enable 'USB debugging'.\n3. Connect via USB and click Scan devices.",
                "action_label": "Scan devices", "action": self.refresh_devices,
            }
        elif not ip:
            payload = {
                "step": "Step 2 of 5", "title": "USB Connected",
                "detail": "You can start mirroring over USB right now, or continue the setup for wireless mirroring.",
                "action_label": "Start USB Mirror", "action": self.start_scrcpy,
                "action_2_label": "Continue Wireless", "action_2": self.get_device_ip,
            }
        elif not self.workflow_tcpip_enabled:
            payload = {
                "step": "Step 3 of 5", "title": "Enable ADB over TCP/IP",
                "detail": "The phone IP is ready. Enable TCP/IP on port 5555 before switching away from USB.",
                "action_label": "Enable TCP/IP", "action": self.enable_tcpip,
            }
        elif not wireless_ready:
            payload = {
                "step": "Step 4 of 5", "title": "Connect wirelessly",
                "detail": "ADB is prepared for Wi-Fi. Click Connect Wi-Fi, wait for success, then you can unplug USB.",
                "action_label": "Connect Wi-Fi", "action": self.connect_wireless,
            }
        else:
            payload = {
                "step": "Step 5 of 5", "title": "Start mirroring",
                "detail": "Wireless ADB is ready. You can start mirroring now.",
                "action_label": "Start Mirroring", "action": self.start_scrcpy,
            }

        self.guidance_step_var.set(payload["step"])
        self.guidance_title_var.set(payload["title"])
        self.guidance_detail_var.set(payload["detail"])
        self.workflow_guidance_action = payload["action"]
        if hasattr(self, "guidance_button"):
            self.guidance_button.configure(text=payload["action_label"], command=self.run_guidance_action, state="normal")
            if "action_2" in payload:
                self.workflow_guidance_action_2 = payload["action_2"]
                self.guidance_button_2.configure(text=payload["action_2_label"], command=self.run_guidance_action_2, state="normal")
                self.guidance_button_2.pack(fill="x", pady=(8, 0))
            else:
                self.workflow_guidance_action_2 = None
                if hasattr(self, "guidance_button_2"):
                    self.guidance_button_2.pack_forget()

    def append_console(self, line, level="OUT"):
        if hasattr(self, "console_textbox") and self.console_textbox.winfo_exists():
            self.root.after(0, lambda: self._append_console_ui(line, level))

    def _append_console_ui(self, line, level):
        self.console_textbox.configure(state="normal")
        try: self.console_textbox.insert("end", line, level)
        except Exception: self.console_textbox.insert("end", line)
        self.console_textbox.see("end")
        self.console_textbox.configure(state="disabled")

    def clear_console(self):
        if not hasattr(self, "console_textbox"): return
        self.console_textbox.configure(state="normal")
        self.console_textbox.delete("1.0", "end")
        self.console_textbox.configure(state="disabled")
        self.console_mgr.log("INFO", "Console cleared.")

    def execute_console_command(self, event=None):
        if not hasattr(self, "console_command_var"): return "break"
        command_text = self.console_command_var.get().strip()
        if not command_text:
            self.console_mgr.log("WARN", "No command entered.")
            return "break"
        self.console_command_var.set("")
        self.console_mgr.run_command_async(command_text)
        return "break"

    def setup_console_tags(self):
        if not hasattr(self, "console_textbox"): return
        try: text_widget = self.console_textbox._textbox
        except Exception: return
        text_widget.tag_config("INFO", foreground=CONSOLE_INFO)
        text_widget.tag_config("OUT", foreground=CONSOLE_OUT)
        text_widget.tag_config("WARN", foreground=CONSOLE_WARN)
        text_widget.tag_config("ERR", foreground=CONSOLE_ERR)
        text_widget.tag_config("ERROR", foreground=CONSOLE_ERR)
        text_widget.tag_config("HINT", foreground=CONSOLE_HINT)

    def setup_console_scroll_isolation(self):
        if not hasattr(self, "console_textbox"): return
        try: text_widget = self.console_textbox._textbox
        except Exception: return
        text_widget.bind("<MouseWheel>", self.on_console_mousewheel, add="+")
        text_widget.bind("<Button-4>", self.on_console_mousewheel, add="+")
        text_widget.bind("<Button-5>", self.on_console_mousewheel, add="+")

    def on_console_mousewheel(self, event):
        try: text_widget = self.console_textbox._textbox
        except Exception: return "break"
        if getattr(event, "num", None) == 4: step = -1
        elif getattr(event, "num", None) == 5: step = 1
        else:
            delta = getattr(event, "delta", 0)
            if delta == 0: return "break"
            step = -1 if delta > 0 else 1
        text_widget.yview_scroll(step, "units")
        return "break"

    # UI Helpers
    def make_section_label(self, parent, title, subtitle=None):
        ctk.CTkLabel(parent, text=title, font=self.fonts["section"], text_color=TEXT).pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(parent, text=subtitle, font=self.fonts["body"], text_color=MUTED_TEXT).pack(anchor="w", pady=(4, 0))

    def make_info_row(self, parent, label, value_var, accent=False):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=6)
        row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(row, text=label, width=78, anchor="w", font=self.fonts["caption_bold"], text_color=MUTED_TEXT).grid(row=0, column=0, sticky="nw", padx=(0, 12))
        ctk.CTkLabel(row, textvariable=value_var, font=self.fonts["body_bold"], text_color=ACCENT_ALT if accent else TEXT, justify="left", anchor="w", wraplength=195).grid(row=0, column=1, sticky="nw")
        return row

    def make_primary_button(self, parent, text, command, height=42):
        return ctk.CTkButton(parent, text=text, command=command, fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color=TEXT, corner_radius=8, height=height, font=self.fonts["button"])

    def make_sidebar_button(self, parent, text, command, active=False):
        return ctk.CTkButton(parent, text=text, command=command, fg_color=CARD_BG if active else "transparent", hover_color=CARD_HOVER, border_color=BORDER, border_width=1 if active else 0, text_color=TEXT if active else MUTED_TEXT, corner_radius=8, height=42, anchor="w", font=self.fonts["button"])

    def set_sidebar_button_state(self, button, active):
        button.configure(fg_color=CARD_BG if active else "transparent", hover_color=CARD_HOVER, border_color=BORDER, border_width=1 if active else 0, text_color=TEXT if active else MUTED_TEXT)

    def switch_tab(self, tab_name):
        self.tabview.set(tab_name)
        self.sync_sidebar_tab_state(tab_name)

    def sync_sidebar_tab_state(self, active_tab=None, *_):
        if not hasattr(self, "sidebar_nav_buttons"): return
        active_tab = active_tab or self.tabview.get()
        for tab_name, button in self.sidebar_nav_buttons.items():
            self.set_sidebar_button_state(button, tab_name == active_tab)

    def make_card(self, parent, title, subtitle=None, fg_color=CARD_BG, border_color=BORDER):
        card = ctk.CTkFrame(parent, fg_color=fg_color, border_color=border_color, border_width=1, corner_radius=10)
        title_label = ctk.CTkLabel(card, text=title, font=self.fonts["section"], text_color=TEXT, justify="left", anchor="w")
        title_label.pack(fill="x", padx=20, pady=(18, 0))
        if subtitle:
            subtitle_label = ctk.CTkLabel(card, text=subtitle, font=self.fonts["body"], text_color=MUTED_TEXT, justify="left", anchor="w")
            subtitle_label.pack(fill="x", padx=20, pady=(4, 10))
            card.bind("<Configure>", lambda e, title_widget=title_label, subtitle_widget=subtitle_label: self.update_card_text_wrap(e.width, title_widget, subtitle_widget), add="+")
        else:
            card.bind("<Configure>", lambda e, title_widget=title_label: self.update_card_text_wrap(e.width, title_widget), add="+")
        return card

    def update_card_text_wrap(self, card_width, title_widget, subtitle_widget=None):
        wrap = max(120, card_width - 40)
        title_widget.configure(wraplength=wrap)
        if subtitle_widget is not None: subtitle_widget.configure(wraplength=wrap)

    def make_action_button(self, parent, text, command, width=132):
        return ctk.CTkButton(parent, text=text, width=width, height=38, command=command, fg_color=FIELD_BG, hover_color=CARD_HOVER, border_color=BORDER, border_width=1, text_color=TEXT, corner_radius=8, font=self.fonts["button"])

    def make_input(self, parent, **kwargs):
        return ctk.CTkEntry(parent, fg_color=FIELD_BG, border_color=BORDER, text_color=TEXT, placeholder_text_color=MUTED_TEXT, corner_radius=8, height=40, font=self.fonts["body"], **kwargs)

    def make_combo(self, parent, **kwargs):
        return ctk.CTkComboBox(parent, fg_color=FIELD_BG, border_color=BORDER, button_color=ACCENT, button_hover_color=ACCENT_HOVER, text_color=TEXT, dropdown_fg_color=PANEL_BG, dropdown_hover_color=CARD_HOVER, dropdown_text_color=TEXT, corner_radius=8, height=40, font=self.fonts["body"], **kwargs)

    def make_checkbox(self, parent, text, variable):
        return ctk.CTkCheckBox(parent, text=text, variable=variable, fg_color=ACCENT, hover_color=ACCENT_HOVER, border_color=BORDER, text_color=TEXT, corner_radius=4, font=self.fonts["body"])

    def make_radio(self, parent, text, value):
        return ctk.CTkRadioButton(parent, text=text, variable=self.var_source, value=value, fg_color=ACCENT, hover_color=ACCENT_HOVER, border_color=BORDER, text_color=TEXT, font=self.fonts["body"])

    def make_labeled_input_row(self, parent, label_text, variable, placeholder="", width=90, label_width=120, extra_text=""):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(row, text=label_text, width=label_width, anchor="w", text_color=MUTED_TEXT, font=self.fonts["body"]).pack(side="left")
        self.make_input(row, textvariable=variable, width=width, placeholder_text=placeholder).pack(side="left")
        if extra_text:
            ctk.CTkLabel(row, text=extra_text, text_color=MUTED_TEXT, font=self.fonts["caption"]).pack(side="left", padx=(12, 0))
        return row

    def make_labeled_combo_row(self, parent, label_text, variable, values, width=110, label_width=110):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(row, text=label_text, width=label_width, anchor="w", text_color=MUTED_TEXT, font=self.fonts["body"]).pack(side="left")
        self.make_combo(row, variable=variable, values=values, width=width).pack(side="left")
        return row

    def make_checkbox_group(self, parent, checks_list):
        for i, (text, var) in enumerate(checks_list):
            if i % 2 == 0:
                row = ctk.CTkFrame(parent, fg_color="transparent")
                row.pack(fill="x", pady=(8 if i == 0 else 4))
                row.grid_columnconfigure((0, 1), weight=1)
            self.make_checkbox(row, text, var).grid(row=0, column=i % 2, sticky="w", padx=4, pady=4)

    def create_widgets(self):
        shell = ctk.CTkFrame(self.root, fg_color=SHELL_BG, border_color=BORDER, border_width=1, corner_radius=12)
        shell.pack(fill="both", expand=True, padx=12, pady=12)
        shell.grid_rowconfigure(0, weight=1)
        shell.grid_columnconfigure(1, weight=1)

        sidebar = ctk.CTkFrame(shell, width=120, fg_color=SIDEBAR_BG, corner_radius=12)
        sidebar.grid(row=0, column=0, sticky="ns", padx=(12, 10), pady=12)
        sidebar.grid_propagate(False)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=18, pady=(24, 18))
        badge = ctk.CTkFrame(brand, fg_color="transparent")
        badge.pack(anchor="w", pady=(0, 4))
        badge_label = self.create_logo_widget(badge, "badge", size=60)
        badge_label.pack(anchor="w")
        ctk.CTkLabel(brand, text="Scrcpy Deck", font=self.fonts["section"], text_color=TEXT).pack(anchor="w", pady=(14, 2))
        ctk.CTkLabel(brand, text="Mirror faster", font=self.fonts["caption"], text_color=MUTED_TEXT).pack(anchor="w")

        nav = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav.pack(fill="x", padx=14, pady=(10, 0))
        self.sidebar_nav_buttons = {}
        for tab in ["Connection", "Video & Audio", "Advanced", "Console"]:
            btn = self.make_sidebar_button(nav, tab, lambda t=tab: self.switch_tab(t), active=(tab=="Connection"))
            btn.pack(fill="x", pady=4)
            self.sidebar_nav_buttons[tab] = btn
        self.make_sidebar_button(nav, "Tutorial", self.open_tutorial).pack(fill="x", pady=4)

        sidebar_footer = ctk.CTkFrame(sidebar, fg_color="transparent")
        sidebar_footer.pack(side="bottom", fill="x", padx=18, pady=18)
        ctk.CTkLabel(sidebar_footer, text=f"v{CURRENT_VERSION}", font=self.fonts["caption"], text_color=MUTED_TEXT).pack(anchor="w")
        ctk.CTkLabel(sidebar_footer, text="by EXPOSUREEE", font=self.fonts["caption"], text_color=MUTED_TEXT).pack(anchor="w", pady=(2, 0))

        center = ctk.CTkFrame(shell, fg_color="transparent")
        center.grid(row=0, column=1, sticky="nsew", pady=12)
        center.grid_columnconfigure(0, weight=1)

        right_rail = ctk.CTkFrame(shell, width=340, fg_color=PANEL_BG, corner_radius=12)
        right_rail.grid(row=0, column=2, sticky="ns", padx=(10, 12), pady=12)
        right_rail.grid_propagate(False)
        right_rail_content = ctk.CTkScrollableFrame(right_rail, width=308, fg_color="transparent", corner_radius=0)
        right_rail_content.pack(fill="both", expand=True, padx=0, pady=0)

        workspace = ctk.CTkFrame(center, fg_color=PANEL_BG, border_color=BORDER, border_width=1, corner_radius=12)
        workspace.pack(fill="both", expand=True)

        workspace_header = ctk.CTkFrame(workspace, fg_color="transparent")
        workspace_header.pack(fill="x", padx=24, pady=(20, 8))
        header_copy = ctk.CTkFrame(workspace_header, fg_color="transparent")
        header_copy.pack(side="left", fill="x", expand=True)
        header_logo = self.create_logo_widget(header_copy, "header", size=24)
        header_logo.pack(anchor="w", pady=(0, 6))
        self.make_section_label(header_copy, "Control Workspace", "Everything below is still functional, just easier to scan and operate.")
        header_actions = ctk.CTkFrame(workspace_header, fg_color="transparent")
        header_actions.pack(side="right")
        self.make_action_button(header_actions, "Watch tutorial", self.open_tutorial, width=140).pack(side="left", padx=(0, 10))
        self.btn_start = self.make_primary_button(header_actions, "Start Mirroring", self.start_scrcpy, height=42)
        self.btn_start.pack(side="left")

        self.tabview = ctk.CTkTabview(workspace, fg_color=PANEL_BG, segmented_button_fg_color=FIELD_BG, segmented_button_selected_color=ACCENT, segmented_button_selected_hover_color=ACCENT_HOVER, segmented_button_unselected_color=FIELD_BG, segmented_button_unselected_hover_color=CARD_HOVER, text_color=TEXT, corner_radius=12, border_width=0, command=self.sync_sidebar_tab_state)
        self.tabview.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        for tab in ["Connection", "Video & Audio", "Advanced", "Console"]: self.tabview.add(tab)

        self.build_connection_tab(self.tabview.tab("Connection"))
        self.build_video_tab(self.tabview.tab("Video & Audio"))
        self.build_advanced_tab(self.tabview.tab("Advanced"))
        self.build_console_tab(self.tabview.tab("Console"))
        self.sync_sidebar_tab_state("Connection")
        self.build_right_rail(right_rail_content)

    def build_right_rail(self, parent):
        session_card = self.make_card(parent, "Current Session", "Live device and launch feedback.")
        session_card.pack(fill="x", padx=16, pady=(18, 14))
        ctk.CTkLabel(session_card, textvariable=self.status_var, font=self.fonts["body_bold"], text_color=TEXT, justify="left", wraplength=230).pack(anchor="w", padx=20, pady=(0, 14))
        self.make_info_row(session_card, "Connection", self.connection_summary_var, accent=True)
        self.make_info_row(session_card, "Quality", self.quality_summary_var)
        self.make_info_row(session_card, "Audio", self.audio_summary_var)

        guidance_card = self.make_card(parent, "Next Step", "A guided flow so the app can tell the user what should happen next.", fg_color=GUIDE_BG, border_color=GUIDE_BORDER)
        guidance_card.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkLabel(guidance_card, textvariable=self.guidance_step_var, font=self.fonts["caption_bold"], text_color=ACCENT_ALT, justify="left", anchor="w").pack(fill="x", padx=20, pady=(4, 2))
        ctk.CTkLabel(guidance_card, textvariable=self.guidance_title_var, font=self.fonts["body_bold"], text_color=TEXT, justify="left", anchor="w").pack(fill="x", padx=20, pady=(0, 6))
        ctk.CTkLabel(guidance_card, textvariable=self.guidance_detail_var, font=self.fonts["body"], text_color=MUTED_TEXT, justify="left", anchor="w", wraplength=230).pack(fill="x", padx=20, pady=(0, 14))
        self.guidance_action_frame = ctk.CTkFrame(guidance_card, fg_color="transparent")
        self.guidance_action_frame.pack(fill="x", padx=20, pady=(0, 18))

        self.guidance_button = self.make_primary_button(self.guidance_action_frame, "Scan devices", self.run_guidance_action, height=40)
        self.guidance_button.pack(fill="x")

        self.guidance_button_2 = self.make_action_button(self.guidance_action_frame, "Secondary", self.run_guidance_action_2)
        self.guidance_button_2.pack(fill="x", pady=(8, 0))
        self.guidance_button_2.pack_forget()

        quick_card = self.make_card(parent, "Quick Actions", "High-frequency tools without opening another tab.")
        quick_card.pack(fill="x", padx=16, pady=(0, 14))
        quick_grid = ctk.CTkFrame(quick_card, fg_color="transparent")
        quick_grid.pack(fill="x", padx=18, pady=(8, 18))
        quick_grid.grid_columnconfigure((0, 1), weight=1)
        self.make_action_button(quick_grid, "Scan devices", self.refresh_devices, width=120).grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=6)
        self.make_action_button(quick_grid, "Auto get IP", self.get_device_ip, width=120).grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=6)
        self.make_action_button(quick_grid, "Enable TCP/IP", self.enable_tcpip, width=120).grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=6)
        self.make_action_button(quick_grid, "Connect Wi-Fi", self.connect_wireless, width=120).grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=6)
        self.make_action_button(quick_grid, "Kill ADB", self.kill_adb_server, width=120).grid(row=2, column=0, sticky="ew", padx=(0, 6), pady=6)
        self.make_action_button(quick_grid, "Reset pairing", self.reset_device_connection, width=120).grid(row=2, column=1, sticky="ew", padx=(6, 0), pady=6)

        summary_card = self.make_card(parent, "Launch Summary", "A compact readout of the options that will shape the next run.")
        summary_card.pack(fill="x", padx=16, pady=(0, 14))
        self.make_info_row(summary_card, "Source", self.source_summary_var)
        self.make_info_row(summary_card, "Window", self.window_summary_var)
        self.make_info_row(summary_card, "Extras", self.extras_summary_var)

        support_card = self.make_card(parent, "Support & Updates", "Keep the tool current or support the project.")
        support_card.pack(fill="x", padx=16, pady=(0, 16))
        support_actions = ctk.CTkFrame(support_card, fg_color="transparent")
        support_actions.pack(fill="x", padx=18, pady=(8, 10))
        self.make_primary_button(support_actions, "Support via UPI", self.donate_upi).pack(fill="x", pady=(0, 10))
        self.make_action_button(support_actions, "Project page", self.open_download, width=140).pack(fill="x")
        self.btn_update = ctk.CTkButton(support_card, text="Update available", fg_color=SUCCESS, hover_color=SUCCESS_HOVER, text_color=TEXT, font=self.fonts["button"], corner_radius=10, command=self.open_download)
        self.btn_update.pack(fill="x", padx=18, pady=(0, 18))
        self.btn_update.pack_forget()

    def build_console_tab(self, parent):
        console_frame = ctk.CTkFrame(parent, fg_color="transparent")
        console_frame.pack(fill="both", expand=True, padx=6, pady=10)
        console_card = self.make_card(console_frame, "Console", "Run commands directly and inspect exact stdout, stderr, and quick fix hints.")
        console_card.pack(fill="both", expand=True, padx=6)
        console_actions = ctk.CTkFrame(console_card, fg_color="transparent")
        console_actions.pack(fill="x", padx=18, pady=(8, 10))
        self.console_command_var = ctk.StringVar()
        self.console_command_entry = self.make_input(console_actions, textvariable=self.console_command_var, placeholder_text="Type a command, e.g. adb devices or scrcpy --version")
        self.console_command_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.console_command_entry.bind("<Return>", self.execute_console_command)
        self.make_action_button(console_actions, "Run", self.execute_console_command, width=90).pack(side="left", padx=(0, 8))
        self.make_action_button(console_actions, "Clear log", self.clear_console, width=120).pack(side="left")

        hint_row = ctk.CTkFrame(console_card, fg_color="transparent")
        hint_row.pack(fill="x", padx=18, pady=(0, 10))
        ctk.CTkLabel(hint_row, text="Commands run inside the app folder. You can use adb, scrcpy, PowerShell commands, or regular shell commands.", font=self.fonts["caption"], text_color=MUTED_TEXT, justify="left", anchor="w", wraplength=820).pack(fill="x")

        self.console_textbox = ctk.CTkTextbox(console_card, fg_color=FIELD_BG, border_color=BORDER, border_width=1, text_color=TEXT, corner_radius=8, font=self.fonts["console"], activate_scrollbars=True, wrap="word")
        self.console_textbox.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self.console_textbox.configure(state="disabled")
        self.setup_console_tags()
        self.setup_console_scroll_isolation()
        self.console_mgr.log("INFO", "Console initialized.")

    def build_connection_tab(self, parent):
        canvas = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        canvas.pack(fill="both", expand=True, padx=6, pady=10)

        dev_frame = self.make_card(canvas, "USB Connection", "Choose a connected Android device, then launch from the hero panel or side rail.")
        dev_frame.pack(fill="x", pady=(0, 16), padx=6)
        inner_dev = ctk.CTkFrame(dev_frame, fg_color="transparent")
        inner_dev.pack(fill="x", padx=18, pady=(12, 18))
        self.device_combo = self.make_combo(inner_dev, values=[], command=lambda _: self.refresh_dashboard_state())
        self.device_combo.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.make_action_button(inner_dev, "Scan devices", self.refresh_devices).pack(side="right")

        workflow = self.make_card(canvas, "Wireless Mode", "Use USB once, switch ADB to TCP/IP, then reconnect from the same network.")
        workflow.pack(fill="x", pady=(0, 16), padx=6)
        r_ip = ctk.CTkFrame(workflow, fg_color="transparent")
        r_ip.pack(fill="x", padx=18, pady=(12, 10))
        ctk.CTkLabel(r_ip, text="Device IP", width=100, anchor="w", text_color=MUTED_TEXT, font=self.fonts["body"]).pack(side="left")
        self.make_input(r_ip, textvariable=self.var_ip, placeholder_text="192.168.1.25").pack(side="left", fill="x", expand=True, padx=(10, 10))
        self.make_action_button(r_ip, "Auto get IP", self.get_device_ip).pack(side="right")

        r_wbtn = ctk.CTkFrame(workflow, fg_color="transparent")
        r_wbtn.pack(fill="x", padx=18, pady=(0, 18))
        self.make_action_button(r_wbtn, "Enable TCP/IP", self.enable_tcpip, width=160).pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.make_action_button(r_wbtn, "Connect wirelessly", self.connect_wireless, width=170).pack(side="left", fill="x", expand=True, padx=(6, 0))

        tips = self.make_card(canvas, "Connection Notes", "A short checklist so the wireless flow stays predictable.")
        tips.pack(fill="x", padx=6)
        notes = [
            "Keep the phone unlocked for the first authorization prompt.",
            "If no IP is found, verify the device is on Wi-Fi and still trusted over USB.",
            "Wireless mode typically uses port 5555 unless you changed it manually.",
            "Use Reset pairing when you want ADB to forget this computer and force a fresh authorization flow.",
        ]
        for note in notes:
            ctk.CTkLabel(tips, text=f"- {note}", font=self.fonts["body"], text_color=MUTED_TEXT, justify="left", wraplength=760).pack(anchor="w", padx=20, pady=4)
        ctk.CTkLabel(tips, text="", height=8).pack()

    def build_video_tab(self, parent):
        canvas = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        canvas.pack(fill="both", expand=True, padx=6, pady=10)

        src_frame = self.make_card(canvas, "Source", "Pick what scrcpy should stream from your phone.")
        src_frame.pack(fill="x", pady=(0, 16), padx=6)
        inner_src = ctk.CTkFrame(src_frame, fg_color="transparent")
        inner_src.pack(fill="x", padx=18, pady=(12, 18))
        self.make_radio(inner_src, "Screen", "screen").pack(side="left", padx=(0, 18))
        self.make_radio(inner_src, "Back Camera", "camera_back").pack(side="left", padx=(0, 18))
        self.make_radio(inner_src, "Front Camera", "camera_front").pack(side="left", padx=(0, 18))
        self.make_radio(inner_src, "Only Microphone", "mic_only").pack(side="left")

        qual_frame = self.make_card(canvas, "Quality", "Keep defaults for smooth mirroring, or tune for sharper output.")
        qual_frame.pack(fill="x", pady=(0, 16), padx=6)
        
        row1 = ctk.CTkFrame(qual_frame, fg_color="transparent")
        row1.pack(fill="x", padx=18, pady=(12, 10))
        self.make_labeled_input_row(row1, "Bitrate (Mbps)", self.var_bitrate).pack(side="left")
        self.make_labeled_input_row(row1, "Max FPS", self.var_max_fps, label_width=100).pack(side="left", padx=(30, 0))

        row2 = ctk.CTkFrame(qual_frame, fg_color="transparent")
        row2.pack(fill="x", padx=18, pady=(0, 18))
        self.make_labeled_input_row(row2, "Max size", self.var_max_size, extra_text="0 keeps original size, e.g. 1080 or 720").pack(side="left")

        codec_frame = self.make_card(canvas, "Codecs & Render", "Compatibility-first defaults with quick renderer control.")
        codec_frame.pack(fill="x", padx=6)
        
        row3 = ctk.CTkFrame(codec_frame, fg_color="transparent")
        row3.pack(fill="x", padx=18, pady=(12, 10))
        self.make_labeled_combo_row(row3, "Video codec", self.var_video_codec, ["h264", "h265", "av1"]).pack(side="left")
        self.make_labeled_combo_row(row3, "Audio codec", self.var_audio_codec, ["opus", "aac", "raw"]).pack(side="left", padx=(30, 0))

        row4 = ctk.CTkFrame(codec_frame, fg_color="transparent")
        row4.pack(fill="x", padx=18, pady=(0, 18))
        self.make_labeled_combo_row(row4, "Renderer", self.renderer_combo_val, ["auto", "opengl", "direct3d", "software"], width=120).pack(side="left")
        self.make_labeled_combo_row(row4, "Camera ratio", self.cam_ar_combo_val, ["Full Sensor (Default)", "16:9", "4:3", "1:1"], width=180).pack(side="left", padx=(30, 0))

    def build_advanced_tab(self, parent):
        canvas = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        canvas.pack(fill="both", expand=True, padx=6, pady=10)

        win_frame = self.make_card(canvas, "Window & Display", "Useful launch flags for screen behavior and interaction.")
        win_frame.pack(fill="x", pady=(0, 16), padx=6)
        
        inner_win = ctk.CTkFrame(win_frame, fg_color="transparent")
        inner_win.pack(fill="x", padx=18, pady=(12, 10))
        
        checks = [
            ("Always on top", self.var_always_on_top),
            ("Borderless window", self.var_borderless),
            ("Fullscreen", self.var_fullscreen),
            ("Stay Awake", self.var_stay_awake),
            ("Turn Screen Off", self.var_screen_off),
            ("Show Touches", self.var_show_touches),
            ("View only", self.var_no_control),
            ("Disable audio", self.var_no_audio),
        ]
        self.make_checkbox_group(inner_win, checks)

        r_orient = ctk.CTkFrame(win_frame, fg_color="transparent")
        r_orient.pack(fill="x", padx=18, pady=(4, 18))
        self.make_labeled_combo_row(r_orient, "Orientation", self.orientation_combo_val, ["Auto (Rotate with Phone)", "Portrait (@0)", "Landscape (@90)", "Portrait Reversed (@180)", "Landscape Reversed (@270)"], width=230, label_width=100).pack(side="left")

        extra_frame = self.make_card(canvas, "Extras", "Recording and debugging options for power users.")
        extra_frame.pack(fill="x", padx=6)
        
        inner_extra = ctk.CTkFrame(extra_frame, fg_color="transparent")
        inner_extra.pack(fill="x", padx=18, pady=12)
        self.make_checkbox_group(inner_extra, [("Record output to MP4", self.var_record), ("Enable debug console", self.var_debug_mode)])

    # ADB Interaction callbacks
    def clear_connected_device_state(self, connection_text="Waiting for your first device scan"):
        self.var_ip.set("")
        self.device_count_var.set("0")
        self.connection_summary_var.set(connection_text)
        self.workflow_tcpip_enabled = False
        self.workflow_wireless_ready = False
        if hasattr(self, "device_combo"):
            try:
                self.device_combo.configure(values=["No devices found"])
                self.device_combo.set("No devices found")
            except Exception: pass
        self.clear_workflow_issue()

    def refresh_devices(self):
        self.set_status("Scanning connected Android devices...")
        self.root.update_idletasks()

        def on_success(devices):
            self.root.after(0, self._refresh_devices_success, devices)
        def on_error(reason):
            self.root.after(0, self._refresh_devices_error, reason)

        self.adb.refresh_devices(on_success, on_error)

    def _refresh_devices_success(self, devices):
        preferred_wireless = f"{self.var_ip.get().strip()}:5555" if self.var_ip.get().strip() else ""
        selected_device = preferred_wireless if preferred_wireless in devices else devices[0]
        self.device_combo.configure(values=devices)
        self.device_combo.set(selected_device)
        self.device_count_var.set(str(len(devices)))
        self.workflow_wireless_ready = ":" in selected_device
        if self.workflow_wireless_ready:
            self.connection_summary_var.set(f"Wireless ready on {selected_device}")
            self.set_status(f"Wireless device detected: {selected_device}")
        else:
            self.connection_summary_var.set(f"USB ready on {selected_device}")
            self.set_status(f"Connected device detected: {selected_device}")
        self.console_mgr.log("INFO", f"Selected device: {selected_device}")
        self.clear_workflow_issue()

    def _refresh_devices_error(self, reason):
        self.device_count_var.set("0")
        self.workflow_wireless_ready = False
        if reason == "no_devices":
            self.device_combo.configure(values=["No devices found"])
            self.device_combo.set("No devices found")
            self.connection_summary_var.set("No active ADB devices")
            self.set_status("No devices found.")
            self.set_workflow_issue("No Android device is available right now.", "\n1. Spam tap 'Build number' in \nSettings > About Phone to unlock 'Developer Options'.\n\n2. Enable 'USB debugging' \n inside 'Developer Options'.\n\n3. Connect via USB and click Scan devices.", self.refresh_devices, "Scan devices")
        else:
            self.connection_summary_var.set("ADB is not responding")
            self.set_status("ADB Error.")
            self.set_workflow_issue("ADB did not answer the device scan.", "Make sure adb is available, then try Scan devices or Kill ADB if the server is stuck.", self.kill_adb_server, "Kill ADB")

    def get_device_ip(self):
        serial = self.device_combo.get()
        if not serial or serial == "No devices found":
            messagebox.showwarning("Error", "Select a device connected via USB first.")
            self.console_mgr.log("WARN", "Cannot fetch IP without a selected USB device.")
            self.set_workflow_issue("The app needs a USB-connected device before it can fetch the Wi-Fi IP.", "Connect the phone with USB, then scan devices again.", self.refresh_devices, "Scan devices")
            return
        self.set_status("Fetching Wi-Fi IP from the selected device...")

        def on_success(ip):
            self.root.after(0, self._get_device_ip_success, ip)
        def on_error():
            self.root.after(0, self._get_device_ip_error)

        self.adb.get_device_ip(serial, on_success, on_error)

    def _get_device_ip_success(self, ip):
        self.var_ip.set(ip)
        self.connection_summary_var.set(f"Wireless target ready: {ip}:5555")
        self.set_status(f"Found device IP: {ip}")
        self.console_mgr.log("INFO", f"Detected wireless IP: {ip}")
        self.clear_workflow_issue()

    def _get_device_ip_error(self):
        self.set_status("Could not find IP (is Wi-Fi on?)")
        self.console_mgr.log("ERROR", "Could not extract a Wi-Fi IP address from wlan0.")
        self.set_workflow_issue("The phone Wi-Fi address could not be detected.", "Turn on Wi-Fi for the phone, keep the USB cable connected, then try Auto get IP again.", self.get_device_ip, "Auto get IP")
        messagebox.showinfo("Info", "Could not automatically find IP.\nPlease check if Wi-Fi is connected on the phone.")

    def enable_tcpip(self):
        serial = self.device_combo.get()
        if not serial or serial == "No devices found":
            messagebox.showwarning("Error", "Select a device connected via USB first.")
            self.console_mgr.log("WARN", "Cannot enable TCP/IP without a selected USB device.")
            self.set_workflow_issue("ADB over Wi-Fi cannot be enabled until a USB device is selected.", "Connect the phone over USB and scan devices first.", self.refresh_devices, "Scan devices")
            return
        self.set_status("Enabling ADB over TCP/IP on port 5555...")

        def on_success():
            self.root.after(0, self._enable_tcpip_success, serial)
        def on_error():
            self.root.after(0, self._enable_tcpip_error)

        self.adb.enable_tcpip(serial, on_success, on_error)

    def _enable_tcpip_success(self, serial):
        messagebox.showinfo("Success", "Wi-Fi mode enabled.\n\nNow you can unplug USB and click 'Connect'.")
        self.connection_summary_var.set("TCP/IP enabled on port 5555")
        self.set_status("Wi-Fi mode enabled on port 5555.")
        self.console_mgr.log("INFO", f"ADB TCP/IP enabled for {serial}.")
        self.workflow_tcpip_enabled = True
        self.clear_workflow_issue()

    def _enable_tcpip_error(self):
        self.set_status("Failed to enable Wi-Fi mode.")
        self.console_mgr.log("ERROR", "ADB TCP/IP mode could not be enabled.")
        self.workflow_tcpip_enabled = False
        self.set_workflow_issue("ADB could not switch the phone into TCP/IP mode.", "Keep USB connected, confirm USB debugging is allowed, then try Enable TCP/IP again.", self.enable_tcpip, "Enable TCP/IP")

    def connect_wireless(self):
        ip = self.var_ip.get().strip()
        if not ip:
            messagebox.showwarning("Error", "Please enter the Device IP address.")
            self.console_mgr.log("WARN", "Wireless connect skipped because the IP field is empty.")
            self.set_workflow_issue("A phone IP address is required before wireless ADB can connect.", "Use Auto get IP first, or type the phone's Wi-Fi IP manually.", self.get_device_ip, "Auto get IP")
            return
        self.set_status(f"Connecting wirelessly to {ip}:5555...")

        def on_success():
            self.root.after(0, self._connect_wireless_success, ip)
        def on_error(reason):
            self.root.after(0, self._connect_wireless_error, ip, reason)

        self.adb.connect_wireless(ip, on_success, on_error)

    def _connect_wireless_success(self, ip):
        self.connection_summary_var.set(f"Wireless ADB linked to {ip}:5555")
        self.set_status(f"Successfully connected to {ip}")
        self.workflow_wireless_ready = True
        self.clear_workflow_issue()
        self.refresh_devices()

    def _connect_wireless_error(self, ip, reason):
        self.connection_summary_var.set(f"Wireless connection failed for {ip}:5555")
        self.set_status("Connection failed.")
        self.console_mgr.log("ERROR", f"Wireless connection to {ip}:5555 failed.")
        self.workflow_wireless_ready = False
        self.set_workflow_issue(f"Wireless ADB could not connect to {ip}:5555.", "Check that the phone and PC are on the same Wi-Fi and that Enable TCP/IP completed successfully.", self.connect_wireless, "Connect Wi-Fi")
        messagebox.showerror("Error", f"Failed to connect.\nADB says: {reason or 'No response'}")

    def kill_adb_server(self):
        self.set_status("Stopping the ADB server...")
        def on_success():
            self.root.after(0, self._kill_adb_server_success)
        def on_error():
            self.root.after(0, self._kill_adb_server_error)
        self.adb.kill_server(on_success, on_error)

    def _kill_adb_server_success(self):
        self.clear_connected_device_state("ADB server stopped")
        self.set_status("ADB server stopped. Scan again when you are ready.")
        self.console_mgr.log("INFO", "ADB server stopped successfully.")

    def _kill_adb_server_error(self):
        self.set_status("Could not stop the ADB server.")
        self.console_mgr.log("ERROR", "ADB kill-server did not complete successfully.")

    def reset_device_connection(self):
        confirmed = messagebox.askyesno("Reset Device Pairing", "This will disconnect wireless ADB, clear the saved device IP, remove local ADB keys, and make you authorize or pair again from scratch.\n\nDo you want to continue?")
        if not confirmed: return

        self.console_mgr.log("WARN", "Full device connection reset requested.")
        self.set_status("Resetting the saved device connection state...")

        def on_success():
            self.root.after(0, self._reset_device_connection_success)
        def on_error():
            pass

        self.adb.reset_connection(self.var_ip.get().strip(), on_success, on_error)

    def _reset_device_connection_success(self):
        self.clear_connected_device_state("Pair again from scratch")
        self.set_status("Connection state reset. Reconnect USB and accept the new debugging prompt.")
        self.console_mgr.log("HINT", "Reconnect the phone by USB, allow the new USB debugging prompt, then enable TCP/IP again if you want wireless mode.")
        self.refresh_devices()
        messagebox.showinfo("Reset Complete", "The saved connection state was cleared.\n\nReconnect the phone by USB and approve the new debugging prompt.")

    def stream_process_output(self, process, stream, label):
        try:
            for line in iter(stream.readline, ''):
                if line:
                    self.append_console(line.rstrip(), label)
        finally:
            try: stream.close()
            except Exception: pass

    def watch_process(self, process, context):
        return_code = process.wait()
        summary = f"{context} exited with code {return_code}."
        if return_code == 0:
            self.append_console(summary, "INFO")
        else:
            self.append_console(summary, "ERROR")
            self.console_mgr.log_hint_for_message(summary)
        self.active_processes = [p for p in self.active_processes if p.poll() is None]

    def start_scrcpy(self):
        if not self.device_combo.get() or self.device_combo.get() == "No devices found":
            self.set_workflow_issue("Mirroring cannot start until a device is available.", "Scan for a USB device first, or finish the wireless connection flow before launching scrcpy.", self.refresh_devices, "Scan devices")
            messagebox.showwarning("No Device", "Please select a device first.")
            return

        settings = {key: getattr(self, var_name).get() for key, (var_name, _, _) in config.CONFIG_FIELDS.items()}
        settings["device_serial"] = self.device_combo.get()
        settings["scrcpy_exe"] = self.scrcpy_exe

        cmd = build_scrcpy_command(settings)

        if not settings.get("record", False):
            self.set_status(f"Running scrcpy with {settings.get('renderer', 'auto')} renderer...")
        
        try:
            self.console_mgr.log("INFO", f"scrcpy launch | Executing: {subprocess.list2cmdline(cmd)}")
            self.clear_workflow_issue()
            if self.var_debug_mode.get():
                self.console_mgr.log("INFO", "Debug console mode is enabled; runtime logs will appear in the external process window.")
                subprocess.Popen(cmd, cwd=self.script_dir)
            else:
                CREATE_NO_WINDOW = 0x08000000 
                process = subprocess.Popen(
                    cmd, cwd=self.script_dir, creationflags=CREATE_NO_WINDOW,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
                )
                self.active_processes.append(process)
                threading.Thread(target=self.stream_process_output, args=(process, process.stdout, "OUT"), daemon=True).start()
                threading.Thread(target=self.stream_process_output, args=(process, process.stderr, "ERR"), daemon=True).start()
                threading.Thread(target=self.watch_process, args=(process, "scrcpy"), daemon=True).start()
        except Exception as e:
            self.set_status("Could not launch scrcpy.")
            self.console_mgr.log("ERROR", f"scrcpy failed before launch: {e}")
            self.set_workflow_issue("scrcpy could not be launched from the current setup.", "Open the Console tab to review the exact error, then retry once the problem is fixed.", lambda: self.switch_tab("Console"), "Open Console")
            messagebox.showerror("Execution Error", str(e))

    def check_for_updates(self):
        try:
            with urllib.request.urlopen(UPDATE_URL, timeout=4) as response:
                remote_version_str = response.read().decode('utf-8').strip()
            
            local_ver = version_tuple(CURRENT_VERSION)
            remote_ver = version_tuple(remote_version_str)
            update_available = remote_ver > local_ver
            
            if update_available:
                self.root.after(0, lambda: self.reveal_update_button(remote_version_str))
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            return

    def reveal_update_button(self, new_version):
        self.btn_update.configure(text=f"Update available: v{new_version}")
        self.btn_update.pack(fill="x", padx=18, pady=(0, 18), ipady=8)

    def open_download(self): webbrowser.open(DOWNLOAD_URL)
    def open_tutorial(self): webbrowser.open(TUTORIAL_URL)

    def donate_upi(self):
        try:
            upi_payload = f"upi://pay?pa={UPI_ID}&pn={urllib.parse.quote(PAYEE_NAME)}&cu=INR"
            encoded_data = urllib.parse.quote(upi_payload)
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&bgcolor=ffffff&data={encoded_data}"
            
            html_content = f'''
            <!DOCTYPE html>
            <html><head><title>Donate to EXPOSUREEE</title><meta charset="UTF-8">
            <style>
                body {{ background-color: #1e1e1e; color: #ffffff; font-family: 'Segoe UI', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
                .card {{ background-color: #2d2d30; padding: 40px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; width: 350px; border-top: 5px solid #4a4a4a; }}
                h1 {{ color: #ffffff; margin: 0 0 5px 0; font-size: 28px; letter-spacing: 1px; text-transform: uppercase; }}
                h2 {{ color: #a0a0a0; margin: 0 0 25px 0; font-size: 16px; font-weight: normal; }}
                .qr-box {{ background: white; padding: 15px; border-radius: 10px; display: inline-block; margin-bottom: 20px; }}
                img {{ display: block; width: 100%; height: auto; }}
                .label {{ font-size: 12px; color: #888; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px; }}
                .upi-box {{ background: #3e3e42; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 16px; color: #fff; border: 1px solid #444; word-break: break-all; user-select: all; }}
                .footer {{ color: #666; font-size: 13px; margin-top: 25px; line-height: 1.5; }}
            </style></head><body>
            <div class="card">
                <h1>EXPOSUREEE</h1><h2>{PAYEE_NAME}</h2>
                <div class="qr-box"><img src="{qr_url}" alt="UPI QR Code" width="250" height="250"></div>
                <div class="label">UPI ID</div><div class="upi-box">{UPI_ID}</div>
                <div class="footer">Scan with GPay, PhonePe, or Paytm.<br>Thank you for your support!</div>
            </div></body></html>
            '''
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html', encoding='utf-8') as f:
                f.write(html_content)
                temp_path = f.name
            webbrowser.open('file://' + temp_path)
        except Exception as e:
            messagebox.showerror("Error", f"Could not generate donation page: {e}")
