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
import queue
import math
from datetime import datetime

import config
from assets import AssetManager
from console import ConsoleManager
from adb import AdbManager
from scrcpy_command import build_scrcpy_command

# --- CONFIGURATION ---
PROGRAM_TITLE = "Scrcpy Deck"
CURRENT_VERSION = "4.0.0"
UPDATE_URL = "https://exposureee.in/wp-content/uploads/2024/08/Scrcpy_GUI_by_EXPOSUREEE-Version.txt"
DOWNLOAD_URL = "https://exposureee.in/scrcpy-gui-by-exposureee/"
TUTORIAL_URL = "https://www.youtube.com/watch?v=pWKY_dntX5c"
UPI_ID = "exposureee@upi"
PAYEE_NAME = "Abhishek Mishra"

# --- MODERN UI THEME COLOR PALETTE (Obsidian & Electric Violet) ---
COLOR_WINDOW_BG = "#0B0B0F"       # Pitch dark canvas background
COLOR_TITLE_BAR_BG = "#000000"    # Solid black for custom title bar
COLOR_SIDEBAR_BG = "#111116"      # Sleek dark sidebar
COLOR_CARD_BG = "#161622"         # Obsidian card surface
COLOR_CARD_HOVER = "#1E1E2F"      # Tactile hover highlight
COLOR_BORDER = "#232333"          # Subtle thin border line
COLOR_ACCENT = "#8B5CF6"          # Electric violet / Neon purple accent
COLOR_ACCENT_HOVER = "#A78BFA"    # Glowing light purple
COLOR_SUCCESS = "#10B981"         # Emerald green for connected / active
COLOR_SUCCESS_HOVER = "#059669"   # Darker success hover
COLOR_WARNING = "#F59E0B"         # Vibrant amber for warnings
COLOR_DANGER = "#EF4444"          # Coral red for errors / alerts
COLOR_TEXT_PRIMARY = "#FFFFFF"    # Crisp white headers
COLOR_TEXT_MUTED = "#8B8B9F"      # Slate grey for details / labels
COLOR_FIELD_BG = "#0D0D14"        # Deeper dark for inputs / dropdowns
COLOR_CONSOLE_BG = "#06060A"      # Pitch-black command line canvas background

# --- BACKWARD COMPATIBLE GLOBALS (Mapped to new theme) ---
APP_BG = COLOR_WINDOW_BG
SHELL_BG = COLOR_SIDEBAR_BG
SIDEBAR_BG = COLOR_SIDEBAR_BG
PANEL_BG = COLOR_WINDOW_BG
CARD_BG = COLOR_CARD_BG
CARD_HOVER = COLOR_CARD_HOVER
FIELD_BG = COLOR_FIELD_BG
BORDER = COLOR_BORDER
TEXT = COLOR_TEXT_PRIMARY
MUTED_TEXT = COLOR_TEXT_MUTED
ACCENT = COLOR_ACCENT
ACCENT_HOVER = COLOR_ACCENT_HOVER
ACCENT_ALT = "#35d6ff"            # Cyan highlight
GUIDE_BG = COLOR_CARD_BG
GUIDE_BORDER = COLOR_ACCENT
SUCCESS = COLOR_SUCCESS
SUCCESS_HOVER = COLOR_SUCCESS_HOVER
WARNING = COLOR_WARNING
CONSOLE_INFO = COLOR_TEXT_MUTED
CONSOLE_OUT = COLOR_TEXT_PRIMARY
CONSOLE_WARN = COLOR_WARNING
CONSOLE_ERR = COLOR_DANGER
CONSOLE_HINT = COLOR_ACCENT_HOVER

def version_tuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v))


# --- DYNAMIC PIL VECTOR ICON GENERATOR ---
def create_vector_icon(icon_type, size=(24, 24), color="#FFFFFF"):
    """
    Generates transparent high-resolution PNG shapes in memory using PIL.
    Renders high-quality Lucide-style outline icons with rounded joints and caps.
    """
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None

    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    w, h = size
    
    # Calculate stroke width dynamically based on icon size (Lucide style is ~2px on 24x24)
    stroke_width = max(1.5, min(w, h) / 12.0)
    
    if icon_type == "connection":  # Lightning bolt (Lucide 'zap' style)
        points = [
            (w * 0.58, h * 0.08),
            (w * 0.25, h * 0.52),
            (w * 0.50, h * 0.52),
            (w * 0.42, h * 0.92),
            (w * 0.75, h * 0.48),
            (w * 0.50, h * 0.48),
            (w * 0.58, h * 0.08)  # Close path
        ]
        draw.line(points, fill=color, width=int(stroke_width), joint="round")
        
    elif icon_type == "devices":  # Smartphone outline (Lucide 'smartphone' style)
        x1, y1 = w * 0.25, h * 0.08
        x2, y2 = w * 0.75, h * 0.92
        radius = int(min(w, h) * 0.08)
        draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, outline=color, width=int(stroke_width))
        
        # Speaker grill at top
        draw.line([(w * 0.44, h * 0.18), (w * 0.56, h * 0.18)], fill=color, width=int(stroke_width), joint="round")
        
        # Home button at bottom
        draw.line([(w * 0.46, h * 0.82), (w * 0.54, h * 0.82)], fill=color, width=int(stroke_width), joint="round")
        
    elif icon_type == "display":  # Monitor/Screen (Lucide 'monitor' style)
        x1, y1 = w * 0.12, h * 0.15
        x2, y2 = w * 0.88, h * 0.70
        radius = int(min(w, h) * 0.06)
        draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, outline=color, width=int(stroke_width))
        
        # Neck
        draw.line([(w * 0.50, h * 0.70), (w * 0.50, h * 0.85)], fill=color, width=int(stroke_width))
        
        # Base
        draw.line([(w * 0.32, h * 0.85), (w * 0.68, h * 0.85)], fill=color, width=int(stroke_width), joint="round")
        
    elif icon_type == "advanced":  # Cog/Gear (Lucide 'settings' style)
        cx, cy = w / 2.0, h / 2.0
        r_out = w * 0.24
        r_in = w * 0.09
        
        # Outer circle
        draw.ellipse([cx - r_out, cy - r_out, cx + r_out, cy + r_out], outline=color, width=int(stroke_width))
        
        # Inner circle (center hole)
        draw.ellipse([cx - r_in, cy - r_in, cx + r_in, cy + r_in], outline=color, width=int(stroke_width))
        
        # 8 teeth/bumps around the outer wheel
        for i in range(8):
            angle = i * math.pi / 4.0
            x1 = cx + (r_out - 1) * math.cos(angle)
            y1 = cy + (r_out - 1) * math.sin(angle)
            x2 = cx + (r_out + w * 0.10) * math.cos(angle)
            y2 = cy + (r_out + w * 0.10) * math.sin(angle)
            draw.line([(x1, y1), (x2, y2)], fill=color, width=int(stroke_width * 1.5), joint="round")
            
    elif icon_type == "console":  # Prompt `>_` (Lucide 'terminal' style)
        # Greater-than prompt
        draw.line([
            (w * 0.18, h * 0.25),
            (w * 0.44, h * 0.50),
            (w * 0.18, h * 0.75)
        ], fill=color, width=int(stroke_width), joint="round")
        
        # Cursor line
        draw.line([
            (w * 0.52, h * 0.75),
            (w * 0.82, h * 0.75)
        ], fill=color, width=int(stroke_width), joint="round")
        
    elif icon_type == "help":  # Book Open (Lucide 'book-open' style)
        # Left page
        draw.line([
            (w * 0.50, h * 0.82),
            (w * 0.15, h * 0.76),
            (w * 0.15, h * 0.22),
            (w * 0.50, h * 0.28),
            (w * 0.50, h * 0.82)
        ], fill=color, width=int(stroke_width), joint="round")
        
        # Right page
        draw.line([
            (w * 0.50, h * 0.82),
            (w * 0.85, h * 0.76),
            (w * 0.85, h * 0.22),
            (w * 0.50, h * 0.28),
            (w * 0.50, h * 0.82)
        ], fill=color, width=int(stroke_width), joint="round")
        
    else:  # Generic bullet dot
        draw.ellipse([w * 0.35, h * 0.35, w * 0.65, h * 0.65], fill=color)

    return img


def get_ctk_icon(icon_type, accent_color=COLOR_ACCENT, muted_color=COLOR_TEXT_MUTED, size=(20, 20)):
    """Creates a transparent, multi-state CustomTkinter icon from vector assets."""
    img_inactive = create_vector_icon(icon_type, size=size, color=muted_color)
    img_active = create_vector_icon(icon_type, size=size, color=accent_color)
    if img_inactive and img_active:
        return ctk.CTkImage(light_image=img_inactive, dark_image=img_active, size=size)
    return None


# --- CUSTOM MODULAR RE-USABLE CARDS ---
class DashboardCard(ctk.CTkFrame):
    """
    A rounded-corner container module that responds to mouse entry/exit transitions
    to glow subtly, improving tactile interaction feedback.
    """
    def __init__(self, master, title="", subtitle=None, fg_color=COLOR_CARD_BG, border_color=COLOR_BORDER, border_width=1, corner_radius=16, **kwargs):
        super().__init__(master, fg_color=fg_color, border_color=border_color, border_width=border_width, corner_radius=corner_radius, **kwargs)
        
        # Hover state bindings
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        
        # Text wrapping adjustments
        self.bind("<Configure>", self.on_resize)
        
        self.title_label = None
        self.subtitle_label = None
        
        if title:
            self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
            self.header_frame.pack(fill="x", padx=20, pady=(18, 8))
            self.header_frame.bind("<Enter>", self.on_enter)
            self.header_frame.bind("<Leave>", self.on_leave)
            
            self.title_label = ctk.CTkLabel(
                self.header_frame,
                text=title,
                font=master.fonts["section"] if hasattr(master, "fonts") else ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                text_color=COLOR_TEXT_PRIMARY,
                anchor="w"
            )
            self.title_label.pack(fill="x")
            self.title_label.bind("<Enter>", self.on_enter)
            self.title_label.bind("<Leave>", self.on_leave)
            
            if subtitle:
                self.subtitle_label = ctk.CTkLabel(
                    self.header_frame,
                    text=subtitle,
                    font=master.fonts["caption"] if hasattr(master, "fonts") else ctk.CTkFont(family="Segoe UI", size=11),
                    text_color=COLOR_TEXT_MUTED,
                    anchor="w",
                    justify="left"
                )
                self.subtitle_label.pack(fill="x", pady=(2, 0))
                self.subtitle_label.bind("<Enter>", self.on_enter)
                self.subtitle_label.bind("<Leave>", self.on_leave)

    def on_enter(self, event=None):
        self.configure(fg_color=COLOR_CARD_HOVER)

    def on_leave(self, event=None):
        if event:
            # Check if the mouse cursor coordinates are actually outside the widget boundaries
            x, y = event.x_root, event.y_root
            containing = self.winfo_containing(x, y)
            current = containing
            while current:
                if current == self:
                    return  # Mouse is still inside the card or its children
                current = getattr(current, "master", None)
        self.configure(fg_color=COLOR_CARD_BG)

    def on_resize(self, event):
        if hasattr(self, "_resize_after_id") and self._resize_after_id:
            try:
                self.after_cancel(self._resize_after_id)
            except Exception:
                pass
        
        new_width = event.width
        self._resize_after_id = self.after(100, lambda: self._do_resize(new_width))

    def _do_resize(self, card_width):
        self._resize_after_id = None
        pad = 40
        if self.title_label and self.title_label.winfo_exists():
            try: self.title_label.configure(wraplength=max(100, card_width - pad))
            except Exception: pass
        if self.subtitle_label and self.subtitle_label.winfo_exists():
            try: self.subtitle_label.configure(wraplength=max(100, card_width - pad))
            except Exception: pass


# --- CUSTOM SIDEBAR NAVIGATION BUTTON ---
class SidebarNavItem(ctk.CTkFrame):
    """
    Left sidebar item with minimalist icon alignment and a vertical accent line indicator.
    Designed to mimic Spotify's slim playlist navigation items with maximized density.
    """
    def __init__(self, master, text, icon_type, command, ctk_gui, **kwargs):
        # Ultra-tight vertical spacing: height=22 (Spotify style)
        super().__init__(master, fg_color="transparent", height=22, **kwargs)
        self.ctk_gui = ctk_gui
        self.command = command
        self.text = text
        
        # Left neon indicator strip (extremely thin and centered vertically)
        self.indicator = ctk.CTkFrame(self, width=2, height=32, fg_color="transparent", corner_radius=1)
        self.indicator.pack(side="left", fill="y", padx=(0, 6), pady=3)
        
        # Crisp 16x16 vector icon for slim profile
        self.icon = get_ctk_icon(icon_type, COLOR_ACCENT, COLOR_TEXT_MUTED, size=(16, 16))
        
        self.button = ctk.CTkButton(
            self,
            text=text,
            image=self.icon,
            compound="left",
            anchor="w",
            fg_color="transparent",
            hover_color=COLOR_CARD_HOVER,
            text_color=COLOR_TEXT_MUTED,
            # Crisp, compact font: 10pt
            font=ctk.CTkFont(family=self.ctk_gui.font_family, size=10, weight="bold"),
            corner_radius=4,
            command=self.on_click,
            height=20,
            border_spacing=2
        )
        self.button.pack(side="left", fill="both", expand=True)

    def set_active(self, active):
        if active:
            self.indicator.configure(fg_color=COLOR_ACCENT)
            self.button.configure(
                text_color=COLOR_TEXT_PRIMARY,
                fg_color=COLOR_CARD_HOVER
            )
        else:
            self.indicator.configure(fg_color="transparent")
            self.button.configure(
                text_color=COLOR_TEXT_MUTED,
                fg_color="transparent"
            )

    def on_click(self):
        self.command()



# --- DIALOG TO EDIT SAVED DEVICE DETAILS ---
class SavedDeviceDialog(ctk.CTkToplevel):
    def __init__(self, parent, device, on_save):
        super().__init__(parent.root)
        self.device = device
        self.on_save = on_save
        
        self.title("Edit Saved Device")
        self.configure(fg_color=COLOR_WINDOW_BG)
        
        self.width = 400
        self.height = 300 if device.get("type") == "wireless" else 240
        self.geometry(f"{self.width}x{self.height}")
        self.resizable(False, False)
        
        # Modal configuration
        self.transient(parent.root)
        self.grab_set()
        
        # Center coordinates
        parent_x = parent.root.winfo_rootx()
        parent_y = parent.root.winfo_rooty()
        parent_w = parent.root.winfo_width()
        parent_h = parent.root.winfo_height()
        x = parent_x + (parent_w - self.width) // 2
        y = parent_y + (parent_h - self.height) // 2
        self.geometry(f"+{x}+{y}")
        
        title_label = ctk.CTkLabel(self, text="Edit Device Details", font=parent.fonts["section"], text_color=COLOR_TEXT_PRIMARY)
        title_label.pack(fill="x", padx=24, pady=(20, 10))
        
        nick_frame = ctk.CTkFrame(self, fg_color="transparent")
        nick_frame.pack(fill="x", padx=24, pady=8)
        
        nick_label = ctk.CTkLabel(nick_frame, text="Nickname", font=parent.fonts["body_bold"], text_color=COLOR_TEXT_MUTED)
        nick_label.pack(anchor="w", pady=(0, 4))
        
        self.nick_entry = ctk.CTkEntry(
            nick_frame, fg_color=COLOR_FIELD_BG, border_color=COLOR_BORDER,
            text_color=COLOR_TEXT_PRIMARY, placeholder_text="e.g. Primary Phone",
            corner_radius=8, height=40, font=parent.fonts["body"]
        )
        self.nick_entry.pack(fill="x")
        self.nick_entry.insert(0, device.get("nickname", ""))
        
        self.ip_entry = None
        if device.get("type") == "wireless":
            ip_frame = ctk.CTkFrame(self, fg_color="transparent")
            ip_frame.pack(fill="x", padx=24, pady=8)
            
            ip_label = ctk.CTkLabel(ip_frame, text="IP Address", font=parent.fonts["body_bold"], text_color=COLOR_TEXT_MUTED)
            ip_label.pack(anchor="w", pady=(0, 4))
            
            self.ip_entry = ctk.CTkEntry(
                ip_frame, fg_color=COLOR_FIELD_BG, border_color=COLOR_BORDER,
                text_color=COLOR_TEXT_PRIMARY, corner_radius=8, height=40, font=parent.fonts["body"]
            )
            self.ip_entry.pack(fill="x")
            self.ip_entry.insert(0, device.get("ip", ""))
            
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(20, 10), side="bottom")
        
        cancel_btn = ctk.CTkButton(
            btn_frame, text="Cancel", width=100, height=38, command=self.destroy,
            fg_color=COLOR_FIELD_BG, hover_color=COLOR_CARD_HOVER, border_color=COLOR_BORDER,
            border_width=1, text_color=COLOR_TEXT_PRIMARY, corner_radius=8, font=parent.fonts["button"]
        )
        cancel_btn.pack(side="left", padx=(0, 10))
        
        save_btn = ctk.CTkButton(
            btn_frame, text="Save Changes", height=38, command=self.save,
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT_PRIMARY, corner_radius=8, font=parent.fonts["button"]
        )
        save_btn.pack(side="right", fill="x", expand=True)
        
        self.nick_entry.focus()


# --- QUICK CONFIGURATION SETTINGS DIALOG ---
class QuickSettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent.root)
        self.parent = parent
        
        self.title("Quick Mirroring Settings")
        self.configure(fg_color=COLOR_WINDOW_BG)
        
        self.width = 500
        self.height = 580
        self.geometry(f"{self.width}x{self.height}")
        self.resizable(False, False)
        
        # Modal configuration
        self.transient(parent.root)
        self.grab_set()
        
        # Center coordinates
        parent_x = parent.root.winfo_rootx()
        parent_y = parent.root.winfo_rooty()
        parent_w = parent.root.winfo_width()
        parent_h = parent.root.winfo_height()
        x = parent_x + (parent_w - self.width) // 2
        y = parent_y + (parent_h - self.height) // 2
        self.geometry(f"+{x}+{y}")
        
        title_label = ctk.CTkLabel(self, text="Quick Mirror Settings", font=parent.fonts["section"], text_color=COLOR_TEXT_PRIMARY)
        title_label.pack(fill="x", padx=24, pady=(20, 10))
        
        # Segmented button for switching tabs
        self.tab_var = ctk.StringVar(value="Screen")
        self.tab_segmented = ctk.CTkSegmentedButton(
            self,
            values=["Screen", "Camera", "Mic"],
            variable=self.tab_var,
            font=parent.fonts["body_bold"],
            fg_color=COLOR_FIELD_BG,
            selected_color=COLOR_ACCENT,
            selected_hover_color=COLOR_ACCENT_HOVER,
            unselected_color=COLOR_FIELD_BG,
            unselected_hover_color=COLOR_CARD_HOVER,
            command=self.switch_quick_tab
        )
        self.tab_segmented.pack(fill="x", padx=24, pady=(0, 16))
        
        # Bottom apply & close button (packed first at the bottom so it is always visible)
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(16, 20), side="bottom")
        
        close_btn = ctk.CTkButton(
            btn_frame, text="Apply & Close", height=40, command=self.apply_and_close,
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT_PRIMARY, corner_radius=8, font=parent.fonts["button"]
        )
        close_btn.pack(fill="x")
        
        # Tab Container (packed second to fill remaining vertical space)
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=24)
        
        self.tab_frames = {}
        for tab_name in ["Screen", "Camera", "Mic"]:
            frame = ctk.CTkScrollableFrame(self.container, fg_color="transparent")
            self.tab_frames[tab_name] = frame
            
        self.build_screen_tab()
        self.build_camera_tab()
        self.build_mic_tab()
        
        # Set active tab based on parent's current source
        source = parent.var_source.get()
        if source in ("camera_back", "camera_front", "camera"):
            init_tab = "Camera"
        elif source == "mic_only":
            init_tab = "Mic"
        else:
            init_tab = "Screen"
            
        self.tab_var.set(init_tab)
        self.switch_quick_tab(init_tab)

    def switch_quick_tab(self, tab_name):
        for name, frame in self.tab_frames.items():
            frame.pack_forget()
        self.tab_frames[tab_name].pack(fill="both", expand=True)
        
        # Auto scan lenses on camera tab enter
        if tab_name == "Camera":
            self.detect_lenses()

    def build_screen_tab(self):
        frame = self.tab_frames["Screen"]
        
        # 1. Connection Mode (HID vs OTG)
        mode_card = self.parent.make_card(frame, "Connection Mode", "Choose how control and display are managed.")
        mode_card.pack(fill="x", pady=(0, 12))
        
        inner_mode = ctk.CTkFrame(mode_card, fg_color="transparent")
        inner_mode.pack(fill="x", padx=20, pady=(6, 12))
        
        self.screen_mode_segmented = ctk.CTkSegmentedButton(
            inner_mode,
            values=["HID (Mirror + Control)", "OTG (Control Only)"],
            variable=self.parent.var_screen_mode,
            font=self.parent.fonts["body_bold"],
            fg_color=COLOR_FIELD_BG,
            selected_color=COLOR_ACCENT,
            selected_hover_color=COLOR_ACCENT_HOVER,
            unselected_color=COLOR_FIELD_BG,
            unselected_hover_color=COLOR_CARD_HOVER
        )
        self.screen_mode_segmented.pack(fill="x", pady=4)
        
        # 2. Quality options
        param_card = self.parent.make_card(frame, "Screen Parameters", "Tune the video rendering properties.")
        param_card.pack(fill="x")
        
        inner_params = ctk.CTkFrame(param_card, fg_color="transparent")
        inner_params.pack(fill="x", padx=20, pady=(6, 12))
        
        self.parent.make_labeled_slider(inner_params, "Stream Bitrate", self.parent.var_bitrate, 1, 64, lambda v: f"{v} Mbps").pack(fill="x", pady=6)
        self.parent.make_labeled_slider(inner_params, "Max FPS Limit", self.parent.var_max_fps, 0, 120, lambda v: "Auto" if v == 0 else f"{v} FPS").pack(fill="x", pady=6)
        self.parent.make_labeled_slider(inner_params, "Max Resolution Size", self.parent.var_max_size, 0, 2560, lambda v: "Native Size" if v == 0 else f"{v}px").pack(fill="x", pady=6)
        
        r_orient = ctk.CTkFrame(inner_params, fg_color="transparent")
        r_orient.pack(fill="x", pady=6)
        self.parent.make_labeled_combo_row(
            r_orient, "Orientation", self.parent.orientation_combo_val,
            ["Auto (Rotate with Phone)", "Portrait (@0)", "Landscape (@90)", "Portrait Reversed (@180)", "Landscape Reversed (@270)"],
            width=210, label_width=100
        ).pack(side="left")

    def build_camera_tab(self):
        frame = self.tab_frames["Camera"]
        
        # 1. Lens Selector Card
        lens_card = self.parent.make_card(frame, "Camera Input", "Detect and target a specific physical camera sensor.")
        lens_card.pack(fill="x", pady=(0, 12))
        
        inner_lens = ctk.CTkFrame(lens_card, fg_color="transparent")
        inner_lens.pack(fill="x", padx=20, pady=(6, 12))
        
        r_lens = ctk.CTkFrame(inner_lens, fg_color="transparent")
        r_lens.pack(fill="x", pady=4)
        
        ctk.CTkLabel(r_lens, text="Camera Lens", width=90, anchor="w", text_color=COLOR_TEXT_MUTED, font=self.parent.fonts["body_bold"]).pack(side="left")
        
        self.camera_lens_combo = self.parent.make_combo(r_lens, values=["Default"], variable=self.parent.var_camera_id, width=220)
        self.camera_lens_combo.pack(side="left", padx=(10, 10))
        
        self.btn_refresh_lenses = self.parent.make_action_button(r_lens, "🔄 Detect", self.detect_lenses, width=80)
        self.btn_refresh_lenses.pack(side="left")
        
        # 2. Camera Settings Card
        cam_settings_card = self.parent.make_card(frame, "Camera Settings", "Override settings for camera streaming.")
        cam_settings_card.pack(fill="x")
        
        inner_cam = ctk.CTkFrame(cam_settings_card, fg_color="transparent")
        inner_cam.pack(fill="x", padx=20, pady=(6, 12))
        
        r_switches = ctk.CTkFrame(inner_cam, fg_color="transparent")
        r_switches.pack(fill="x", pady=6)
        self.parent.make_checkbox(r_switches, "Enable Camera Torch (Flashlight)", self.parent.var_camera_torch).pack(side="left")
        
        r_combos = ctk.CTkFrame(inner_cam, fg_color="transparent")
        r_combos.pack(fill="x", pady=6)
        self.parent.make_labeled_combo_row(r_combos, "Aspect Ratio", self.parent.cam_ar_combo_val, ["Full Sensor (Default)", "4:3", "16:9"], width=130, label_width=90).pack(side="left")
        self.parent.make_labeled_combo_row(r_combos, "Orientation", self.parent.cam_orientation_combo_val, ["0° (Default)", "90°", "180°", "270°"], width=130, label_width=90).pack(side="left", padx=(20, 0))
        
        self.parent.make_labeled_slider(inner_cam, "Max Resolution Size", self.parent.var_camera_max_size, 0, 2560, lambda v: "Native Size" if v == 0 else f"{v}px").pack(fill="x", pady=6)
        self.parent.make_labeled_slider(inner_cam, "Max FPS Limit", self.parent.var_camera_fps, 0, 60, lambda v: "Auto" if v == 0 else f"{v} FPS").pack(fill="x", pady=6)
        self.parent.make_labeled_slider(inner_cam, "Camera Zoom", self.parent.var_camera_zoom, 1, 8, lambda v: f"{v}.0x" if v == int(v) else f"{v}x").pack(fill="x", pady=6)

    def build_mic_tab(self):
        frame = self.tab_frames["Mic"]
        
        mic_card = self.parent.make_card(frame, "Audio Settings", "Configure options when capturing microphone audio.")
        mic_card.pack(fill="x")
        
        inner_mic = ctk.CTkFrame(mic_card, fg_color="transparent")
        inner_mic.pack(fill="x", padx=20, pady=(6, 12))
        
        r_codec = ctk.CTkFrame(inner_mic, fg_color="transparent")
        r_codec.pack(fill="x", pady=6)
        self.parent.make_labeled_combo_row(r_codec, "Audio Codec", self.parent.var_audio_codec, ["opus", "aac", "raw"], width=180, label_width=120).pack(side="left")
        
        self.parent.make_checkbox(inner_mic, "Mute Device Audio Forwarding", self.parent.var_no_audio).pack(anchor="w", pady=12)

    def detect_lenses(self):
        self.btn_refresh_lenses.configure(text="⏳ Scanning...", state="disabled")
        
        def run_detect():
            serial = self.parent.get_selected_device()
            cmd = [self.parent.scrcpy_exe, "--list-cameras"]
            if serial:
                cmd.extend(["-s", serial])
            
            self.parent.console_mgr.log("INFO", f"Lens scan | Executing: {subprocess.list2cmdline(cmd)}")
            
            try:
                CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
                process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5, creationflags=CREATE_NO_WINDOW)
                output = process.stdout + "\n" + process.stderr
                
                lenses = []
                for line in output.splitlines():
                    match = re.search(r"--camera-id=(\d+)\s*\(([^)]+)\)", line)
                    if match:
                        cam_id = match.group(1)
                        desc = match.group(2)
                        lenses.append(f"ID {cam_id}: {desc}")
                        
                if not lenses:
                    lenses = ["Default"]
                else:
                    lenses.insert(0, "Default")
                
                # Check current value, if not in list, set to Default
                curr_val = self.parent.var_camera_id.get()
                if curr_val not in lenses:
                    found = False
                    for l in lenses:
                        if l.startswith(f"ID {curr_val}:") or l == curr_val:
                            self.parent.var_camera_id.set(l)
                            found = True
                            break
                    if not found:
                        self.parent.var_camera_id.set("Default")
                        
                if not self.winfo_exists():
                    return
                self.after(0, lambda: self.update_lens_combo(lenses))
            except Exception as e:
                self.parent.console_mgr.log("ERROR", f"Lens scan failed: {e}")
                if self.winfo_exists():
                    self.after(0, lambda: self.update_lens_combo(["Default"]))
                
        threading.Thread(target=run_detect, daemon=True).start()

    def update_lens_combo(self, lenses):
        if not self.winfo_exists():
            return
        try:
            if self.camera_lens_combo.winfo_exists():
                self.camera_lens_combo.configure(values=lenses)
            if self.btn_refresh_lenses.winfo_exists():
                self.btn_refresh_lenses.configure(text="🔄 Detect", state="normal")
        except Exception:
            pass

    def apply_and_close(self):
        active_tab = self.tab_var.get()
        if active_tab == "Screen":
            self.parent.var_source.set("screen")
        elif active_tab == "Camera":
            self.parent.var_source.set("camera")
        elif active_tab == "Mic":
            self.parent.var_source.set("mic_only")
            
        config.save_config(self.parent, self.parent.config_file)
        self.parent.refresh_dashboard_state()
        self.destroy()


# --- CUSTOM TITLE BAR ---
class TitleBar(ctk.CTkFrame):
    """
    Custom macOS-style frameless window Title Bar.
    Features red, yellow, and green window control circles on the far left,
    and a centered application title.
    Supports smooth dragging/repositioning.
    """
    def __init__(self, master, ctk_gui, title_text="Scrcpy Deck v4.0.0", **kwargs):
        super().__init__(master, fg_color=COLOR_TITLE_BAR_BG, height=18, corner_radius=0, **kwargs)
        self.pack_propagate(False)
        self.ctk_gui = ctk_gui
        self.root = ctk_gui.root
        
        self.drag_data = {"x": 0, "y": 0}
        
        # Right circular window control buttons container
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.place(relx=1.0, rely=0.33, anchor="e", x=-16)
        
        # Window control colors (Windows order: Minimize, Maximize, Close)
        self.btn_minimize = self.create_circle_button(self.controls_frame, "#FFBD2E", "#FFD066", self.on_minimize)
        self.btn_minimize.pack(side="left", padx=4)
        
        self.btn_maximize = self.create_circle_button(self.controls_frame, "#27C93F", "#4AE260", self.on_maximize)
        self.btn_maximize.pack(side="left", padx=4)
        
        self.btn_close = self.create_circle_button(self.controls_frame, "#FF5F56", "#FF7B72", self.on_close)
        self.btn_close.pack(side="left", padx=4)
        
        # Title Label Centered
        self.title_label = ctk.CTkLabel(
            self,
            text=title_text,
            font=ctk.CTkFont(family=self.ctk_gui.font_family, size=11, weight="bold"),
            text_color="#FFFFFF"
        )
        self.title_label.place(relx=0.5, rely=0.33, anchor="center")
        
        # Bind dragging & double-click maximize
        self.bind("<Button-1>", self.start_drag)
        self.bind("<B1-Motion>", self.drag_window)
        self.bind("<Double-Button-1>", self.on_maximize)
        
        self.title_label.bind("<Button-1>", self.start_drag)
        self.title_label.bind("<B1-Motion>", self.drag_window)
        self.title_label.bind("<Double-Button-1>", self.on_maximize)

    def create_smooth_circle_image(self, color, size=(12, 12), scale=4):
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            return None
        w, h = size
        large_w, large_h = w * scale, h * scale
        
        img = Image.new("RGBA", (large_w, large_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        margin = scale // 2
        draw.ellipse([margin, margin, large_w - margin, large_h - margin], fill=color)
        
        try:
            resample_filter = Image.Resampling.LANCZOS
        except AttributeError:
            try:
                resample_filter = Image.LANCZOS
            except AttributeError:
                resample_filter = Image.ANTIALIAS
                
        img_smooth = img.resize((w * 3, h * 3), resample=resample_filter)
        return ctk.CTkImage(light_image=img_smooth, dark_image=img_smooth, size=size)

    def create_circle_button(self, parent, color, hover_color, command):
        img_normal = self.create_smooth_circle_image(color, (12, 12))
        img_hover = self.create_smooth_circle_image(hover_color, (12, 12))
        
        if img_normal and img_hover:
            label = ctk.CTkLabel(parent, text="", image=img_normal, width=12, height=12, fg_color="transparent", cursor="hand2")
            label.image_normal = img_normal
            label.image_hover = img_hover
            
            label.bind("<Button-1>", lambda event: command())
            label.bind("<Enter>", lambda event: label.configure(image=label.image_hover))
            label.bind("<Leave>", lambda event: label.configure(image=label.image_normal))
            return label
        else:
            canvas = tk.Canvas(parent, width=12, height=12, bg=COLOR_TITLE_BAR_BG, highlightthickness=0, bd=0, cursor="hand2")
            canvas.create_oval(1, 1, 11, 11, fill=color, outline="")
            canvas.bind("<Button-1>", lambda event: command())
            return canvas

    def start_drag(self, event):
        try:
            from ctypes import windll
            # Release mouse capture from Tkinter so Windows can take over dragging
            windll.user32.ReleaseCapture()
            
            # Send WM_NCLBUTTONDOWN with HTCAPTION asynchronously to the parent window
            # using PostMessageW to prevent GIL release and modal blocking crashes.
            hwnd = windll.user32.GetParent(self.root.winfo_id())
            WM_NCLBUTTONDOWN = 0x00A1
            HTCAPTION = 2
            windll.user32.PostMessageW(hwnd, WM_NCLBUTTONDOWN, HTCAPTION, 0)
        except Exception:
            # Fallback to manual drag coordinates
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

    def drag_window(self, event):
        try:
            # Fallback manual drag calculation (only runs if Windows drag didn't take over)
            deltax = event.x - self.drag_data["x"]
            deltay = event.y - self.drag_data["y"]
            x = self.root.winfo_x() + deltax
            y = self.root.winfo_y() + deltay
            self.root.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def on_close(self):
        self.root.destroy()

    def on_minimize(self):
        # Natively minimize standard window
        self.root.state("iconic")

    def on_maximize(self, event=None):
        if self.root.state() == "zoomed":
            self.root.state("normal")
        else:
            self.root.state("zoomed")


    def save(self):
        new_nick = self.nick_entry.get().strip()
        new_ip = self.ip_entry.get().strip() if self.ip_entry else None
        self.on_save(new_nick, new_ip)
        self.destroy()


# --- MAIN APPLICATION VIEW ---
class ScrcpyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{PROGRAM_TITLE} v{CURRENT_VERSION}")
        self.root.geometry("1200x700")
        self.root.minsize(1050, 620)

        # Window configuration (Standard window with custom captionless styling)
        self.root.overrideredirect(False)
        self.root.after(10, self.apply_frameless_style)

        # Set strict premium dark mode
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

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

        # Managers initialization
        self.asset_mgr = AssetManager(self.root, self.script_dir, self.assets_dir)
        self.console_mgr = ConsoleManager(self.append_console, self.script_dir)
        self.adb = AdbManager(self.adb_exe, self.script_dir, self.console_mgr)

        # Thread-safe logging queue engine
        self.log_queue = queue.Queue()
        self.root.after(50, self._queue_polling_loop)

        self.init_theme()

        # Shared Configuration Variables Initialization
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
        
        self.var_pair_port = ctk.StringVar(value="")
        self.var_pair_code = ctk.StringVar(value="")
        self.var_connect_port = ctk.StringVar(value="")
        
        self.workflow_tcpip_enabled = False
        self.workflow_wireless_ready = False
        self.workflow_issue_message = ""
        self.workflow_issue_hint = ""
        self.workflow_issue_action = None
        self.workflow_issue_action_label = ""
        self.active_processes = []
        self.device_label_to_serial = {}
        self.device_serial_to_label = {}
        self.device_infos = []

        config.load_config(self, self.config_file)
        self.attach_variable_traces()
        self.create_widgets()
        self.refresh_dashboard_state()
        self.refresh_devices()
        
        threading.Thread(target=self.check_for_updates, daemon=True).start()

    def apply_frameless_style(self):
        try:
            from ctypes import windll
            GWL_STYLE = -16
            WS_CAPTION = 0x00C00000
            WS_THICKFRAME = 0x00040000
            
            SWP_FRAMECHANGED = 0x0020
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            
            hwnd = windll.user32.GetParent(self.root.winfo_id())
            style = windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
            
            # Remove title bar/caption borders but retain thick resizing border
            new_style = (style & ~WS_CAPTION) | WS_THICKFRAME
            windll.user32.SetWindowLongW(hwnd, GWL_STYLE, new_style)
            
            # Force the frame style change to take effect immediately
            windll.user32.SetWindowPos(
                hwnd, 0, 0, 0, 0, 0,
                SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER
            )
        except Exception:
            pass

    def init_theme(self):
        self.root.configure(fg_color=COLOR_WINDOW_BG)
        self.root.configure(bg=COLOR_WINDOW_BG)
        self.load_local_fonts()
        
        self.font_family = self.pick_font("Nunito", "Nunito Medium", "Segoe UI Variable Text", "Segoe UI", "Arial")
        self.font_title_family = self.pick_font("Quicksand", "Nunito ExtraBold", "Nunito Black", "Nunito", "Segoe UI Variable Display", self.font_family)
        self.font_metric_family = self.pick_font("Nunito Black", "Nunito ExtraBold", "Nunito", self.font_title_family)
        self.font_ui_accent_family = self.pick_font("Quicksand", "Nunito SemiBold", "Nunito", "Segoe UI Variable Text", self.font_family)
        self.font_caption_family = self.pick_font("Nunito Medium", "Nunito", self.font_family)
        self.font_mono_family = self.pick_font("Cascadia Code", "Consolas", "Courier New", self.font_family)
        
        self.root.option_add("*Font", f"{{{self.font_family}}} 12")
        self.fonts = {
            "hero": ctk.CTkFont(family=self.font_title_family, size=30, weight="bold"),
            "title": ctk.CTkFont(family=self.font_title_family, size=24, weight="bold"),
            "section": ctk.CTkFont(family=self.font_title_family, size=18, weight="bold"),
            "body": ctk.CTkFont(family=self.font_family, size=13),
            "body_bold": ctk.CTkFont(family=self.font_ui_accent_family, size=13, weight="bold"),
            "metric": ctk.CTkFont(family=self.font_metric_family, size=26, weight="bold"),
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
        return COLOR_WINDOW_BG

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
        fallback_text = "SD" if size is None or size >= 40 else ""
        return ctk.CTkLabel(parent, text=fallback_text, text_color=COLOR_TEXT_PRIMARY, font=self.fonts["button_large"])

    def attach_variable_traces(self):
        for var_name, _, _ in config.CONFIG_FIELDS.values():
            getattr(self, var_name).trace_add("write", lambda *_: self.refresh_dashboard_state())

    def refresh_dashboard_state(self):
        config.save_config(self, self.config_file)
        
        source_labels = {
            "screen": "Screen mirror",
            "camera_back": "Back camera",
            "camera_front": "Front camera",
            "camera": "Camera lens",
            "mic_only": "Microphone only",
        }
        source_label = source_labels.get(self.var_source.get(), "Screen mirror")
        self.source_summary_var.set(f"{source_label} | Renderer {self.renderer_combo_val.get()}")
        
        self.source_metric_var.set({"screen": "Screen", "camera_back": "Back Cam", "camera_front": "Front Cam", "camera": "Camera", "mic_only": "Mic Only"}.get(self.var_source.get(), "Screen"))
        self.source_metric_detail_var.set(f"{self.renderer_combo_val.get().title()} renderer")

        bitrate = self.var_bitrate.get().strip() or "8"
        
        if self.var_screen_mode.get() == "OTG" and self.var_source.get() == "screen":
            self.quality_summary_var.set("OTG Mode (No Video/Audio)")
        elif self.var_source.get() in ("camera_back", "camera_front", "camera"):
            fps = self.var_camera_fps.get().strip()
            size = self.var_camera_max_size.get().strip()
            fps_label = "Auto FPS" if not fps or fps == "0" else f"{fps} FPS"
            size_label = "Native size" if not size or size == "0" else f"{size}px max"
            self.quality_summary_var.set(f"{bitrate} Mbps | {fps_label} | {size_label} | CAMERA")
        else:
            fps = self.var_max_fps.get().strip()
            size = self.var_max_size.get().strip()
            fps_label = "Auto FPS" if not fps or fps == "0" else f"{fps} FPS"
            size_label = "Native size" if not size or size == "0" else f"{size}px max"
            self.quality_summary_var.set(f"{bitrate} Mbps | {fps_label} | {size_label} | {self.var_video_codec.get().upper()}")

        if self.var_source.get() in ("camera_back", "camera_front", "camera"):
            audio_label = "Audio muted for camera mode"
        else:
            audio_label = "Audio Muted" if self.var_no_audio.get() else f"Audio: {self.var_audio_codec.get().upper()}"
        self.audio_summary_var.set(audio_label)

        orientation_labels = {
            "Auto (Rotate with Phone)": "Rotate with Phone",
            "Portrait (@0)": "Portrait (0°)",
            "Landscape (@90)": "Landscape (90°)",
            "Portrait Reversed (@180)": "Portrait Reversed (180°)",
            "Landscape Reversed (@270)": "Landscape Reversed (270°)",
        }
        orient = orientation_labels.get(self.orientation_combo_val.get(), "Auto")
        opts = []
        if self.var_always_on_top.get(): opts.append("Top")
        if self.var_borderless.get(): opts.append("Borderless")
        if self.var_fullscreen.get(): opts.append("Fullscreen")
        opts_label = f" | {', '.join(opts)}" if opts else ""
        self.window_summary_var.set(f"{orient}{opts_label}")

        behaviors = []
        if self.var_stay_awake.get(): behaviors.append("Stay Awake")
        if self.var_screen_off.get(): behaviors.append("Turn Screen Off")
        if self.var_show_touches.get(): behaviors.append("Show Touches")
        if self.var_no_control.get(): behaviors.append("Read-Only")
        self.extras_summary_var.set(", ".join(behaviors) or "Standard behavior")

        if self.var_record.get():
            self.recording_status_var.set("Active")
            self.recording_detail_var.set("Recording active next run")
        else:
            self.recording_status_var.set("Off")
            self.recording_detail_var.set("MP4 capture idle")

        self.update_next_step_guidance()

    def set_status(self, message):
        self.status_var.set(message)

    def get_selected_device(self):
        label = self.device_combo.get()
        if not label or label == "No devices found":
            return ""
        return self.device_label_to_serial.get(label, "")

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
        if getattr(self, "workflow_guidance_action", None):
            self.workflow_guidance_action()

    def run_guidance_action_2(self):
        if getattr(self, "workflow_guidance_action_2", None):
            self.workflow_guidance_action_2()

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
                "step": "Attention Needed", "title": "Setup Warning", "detail": detail,
                "action_label": self.workflow_issue_action_label or "Open Console",
                "action": self.workflow_issue_action or (lambda: self.switch_tab("Terminal Console")),
            }
        elif not usb_ready:
            payload = {
                "step": "Step 1 of 5", "title": "Plug in your Phone",
                "detail": "1. Go to settings > About Phone.\n2. Spam tap 'Build number' to unlock Developer options.\n3. Turn on 'USB debugging' inside Developer options.\n4. Connect with a USB cable and scan.",
                "action_label": "Scan for Devices", "action": self.refresh_devices,
            }
        elif not ip:
            payload = {
                "step": "Step 2 of 5", "title": "USB Link Active",
                "detail": "Device detected over USB! You can start mirroring over the cable right now, or continue setting up Wi-Fi.",
                "action_label": "Start Cable Mirror", "action": self.start_scrcpy,
                "action_2_label": "Setup Wi-Fi IP", "action_2": self.get_device_ip,
            }
        elif not self.workflow_tcpip_enabled:
            payload = {
                "step": "Step 3 of 5", "title": "Configure Port 5555",
                "detail": "Click Enable TCP/IP below. This instructs ADB on the phone to allow connections over the network.",
                "action_label": "Enable TCP/IP", "action": self.enable_tcpip,
            }
        elif not wireless_ready:
            payload = {
                "step": "Step 4 of 5", "title": "Connect Wirelessly",
                "detail": "Disconnect your USB cable. Enter the IP address and click Connect Wi-Fi.",
                "action_label": "Connect Wi-Fi", "action": self.connect_wireless,
            }
        else:
            payload = {
                "step": "Step 5 of 5", "title": "Wi-Fi Link Ready",
                "detail": "Your phone is connected wirelessly over Wi-Fi! You can now launch mirroring.",
                "action_label": "Start Wireless Mirror", "action": self.start_scrcpy,
            }

        self.guidance_step_var.set(payload["step"])
        self.guidance_title_var.set(payload["title"])
        self.guidance_detail_var.set(payload["detail"])
        self.workflow_guidance_action = payload["action"]
        
        if hasattr(self, "guidance_button") and self.guidance_button.winfo_exists():
            self.guidance_button.configure(text=payload["action_label"], state="normal")
            if "action_2" in payload:
                self.workflow_guidance_action_2 = payload["action_2"]
                self.guidance_button_2.configure(text=payload["action_2_label"], state="normal")
                self.guidance_button_2.pack(fill="x", pady=(8, 0))
            else:
                self.workflow_guidance_action_2 = None
                self.guidance_button_2.pack_forget()

    # --- THREAD-SAFE NON-BLOCKING QUEUE POLLING ---
    def _queue_polling_loop(self):
        try:
            while True:
                line, level = self.log_queue.get_nowait()
                self._append_console_ui(line, level)
                self.log_queue.task_done()
        except queue.Empty:
            pass
        self.root.after(50, self._queue_polling_loop)

    def append_console(self, line, level="OUT"):
        self.log_queue.put((line, level))

    def _append_console_ui(self, line, level):
        if not hasattr(self, "console_textbox") or not self.console_textbox.winfo_exists():
            return
        self.console_textbox.configure(state="normal")
        try:
            self.console_textbox.insert("end", line + "\n", level)
        except Exception:
            self.console_textbox.insert("end", line + "\n")
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


    # --- COMPONENT STYLING HELPERS (For compatibility) ---
    def make_section_label(self, parent, title, subtitle=None):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(frame, text=title, font=self.fonts["section"], text_color=COLOR_TEXT_PRIMARY, anchor="w").pack(fill="x")
        if subtitle:
            ctk.CTkLabel(frame, text=subtitle, font=self.fonts["caption"], text_color=COLOR_TEXT_MUTED, anchor="w").pack(fill="x")
        return frame

    def make_info_row(self, parent, label, value_var, accent=False):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(row, text=label, font=self.fonts["caption_bold"], text_color=COLOR_TEXT_MUTED).pack(side="left")
        val_lbl = ctk.CTkLabel(row, textvariable=value_var, font=self.fonts["caption"], text_color=COLOR_ACCENT if accent else COLOR_TEXT_PRIMARY)
        val_lbl.pack(side="right")
        return row

    def make_primary_button(self, parent, text, command, height=42):
        return ctk.CTkButton(
            parent, text=text, height=height, command=command,
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT_PRIMARY, font=self.fonts["button_large"],
            corner_radius=12
        )

    def make_action_button(self, parent, text, command, width=132, **kwargs):
        defaults = {
            "fg_color": COLOR_FIELD_BG,
            "hover_color": COLOR_CARD_HOVER,
            "border_color": COLOR_BORDER,
            "border_width": 1,
            "text_color": COLOR_TEXT_PRIMARY,
            "corner_radius": 8,
            "font": self.fonts["button"]
        }
        defaults.update(kwargs)
        return ctk.CTkButton(parent, text=text, width=width, height=38, command=command, **defaults)

    def make_input(self, parent, **kwargs):
        return ctk.CTkEntry(
            parent, fg_color=COLOR_FIELD_BG, border_color=COLOR_BORDER,
            text_color=COLOR_TEXT_PRIMARY, placeholder_text_color=COLOR_TEXT_MUTED,
            corner_radius=8, height=40, font=self.fonts["body"], **kwargs
        )

    def make_combo(self, parent, **kwargs):
        return ctk.CTkComboBox(
            parent, fg_color=COLOR_FIELD_BG, border_color=COLOR_BORDER,
            button_color=COLOR_ACCENT, button_hover_color=COLOR_ACCENT_HOVER,
            text_color=COLOR_TEXT_PRIMARY, dropdown_fg_color=COLOR_CARD_BG,
            dropdown_hover_color=COLOR_CARD_HOVER, dropdown_text_color=COLOR_TEXT_PRIMARY,
            corner_radius=8, height=40, font=self.fonts["body"], **kwargs
        )

    def make_checkbox(self, parent, text, variable):
        """Replaces checkboxes with modern switches matching design specification."""
        return ctk.CTkSwitch(
            parent, text=text, variable=variable,
            progress_color=COLOR_ACCENT, fg_color=COLOR_BORDER,
            text_color=COLOR_TEXT_PRIMARY, font=self.fonts["body"]
        )

    def make_radio(self, parent, text, value):
        return ctk.CTkRadioButton(
            parent, text=text, variable=self.var_source, value=value,
            fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            border_color=COLOR_BORDER, text_color=COLOR_TEXT_PRIMARY, font=self.fonts["body"]
        )

    def make_labeled_input_row(self, parent, label_text, variable, placeholder="", width=90, label_width=120, extra_text=""):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(row, text=label_text, width=label_width, anchor="w", text_color=COLOR_TEXT_MUTED, font=self.fonts["body"]).pack(side="left")
        self.make_input(row, textvariable=variable, placeholder_text=placeholder, width=width).pack(side="left")
        if extra_text:
            ctk.CTkLabel(row, text=extra_text, text_color=COLOR_TEXT_MUTED, font=self.fonts["caption"]).pack(side="left", padx=10)
        return row

    def make_labeled_combo_row(self, parent, label_text, variable, values, width=110, label_width=110):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(row, text=label_text, width=label_width, anchor="w", text_color=COLOR_TEXT_MUTED, font=self.fonts["body"]).pack(side="left")
        self.make_combo(row, variable=variable, values=values, width=width).pack(side="left")
        return row

    def make_checkbox_group(self, parent, checks_list):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        for text, var in checks_list:
            self.make_checkbox(frame, text, var).pack(anchor="w", pady=4)
        return frame

    def make_card(self, parent, title, subtitle=None, fg_color=COLOR_CARD_BG, border_color=COLOR_BORDER):
        card = DashboardCard(parent, title=title, subtitle=subtitle, fg_color=fg_color, border_color=border_color)
        return card

    # --- REACTIVE INTERACTIVE SLIDER CREATOR ---
    def make_labeled_slider(self, parent, label_text, variable, from_, to, value_formatter=None):
        """
        Creates a custom labeled slider with bidirectional data binding:
        Dragging updates variable, and updating variable snaps slider.
        """
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 4))
        
        lbl = ctk.CTkLabel(header, text=label_text, font=self.fonts["body_bold"], text_color=COLOR_TEXT_MUTED)
        lbl.pack(side="left")
        
        val_lbl = ctk.CTkLabel(header, text="", font=self.fonts["body_bold"], text_color=COLOR_ACCENT)
        val_lbl.pack(side="right")
        
        def on_slider_move(val):
            val_int = int(val)
            variable.set(str(val_int))
            disp = value_formatter(val_int) if value_formatter else str(val_int)
            val_lbl.configure(text=disp)
            self.refresh_dashboard_state()
            
        try:
            curr_val = int(variable.get().strip() or "0")
        except ValueError:
            curr_val = 0
            
        slider = ctk.CTkSlider(
            frame, from_=from_, to=to, number_of_steps=to - from_,
            button_color=COLOR_ACCENT, button_hover_color=COLOR_ACCENT_HOVER,
            progress_color=COLOR_ACCENT, fg_color=COLOR_BORDER,
            command=on_slider_move
        )
        slider.set(curr_val)
        slider.pack(fill="x", pady=2)
        
        disp = value_formatter(curr_val) if value_formatter else str(curr_val)
        val_lbl.configure(text=disp)
        
        def on_var_write(*args):
            try:
                new_val = int(variable.get().strip() or "0")
                slider.set(new_val)
                disp_val = value_formatter(new_val) if value_formatter else str(new_val)
                val_lbl.configure(text=disp_val)
            except Exception:
                pass
                
        variable.trace_add("write", on_var_write)
        return frame


    # --- MAIN VIEW SHELL CONSTRUCTION ---
    def create_widgets(self):
        # Custom macOS-style Title Bar
        self.title_bar = TitleBar(self.root, self, title_text=f"Scrcpy Deck v{CURRENT_VERSION}")
        self.title_bar.pack(fill="x", side="top")

        # Shell container grid
        shell = ctk.CTkFrame(self.root, fg_color=COLOR_WINDOW_BG)
        shell.pack(fill="both", expand=True)
        shell.grid_rowconfigure(0, weight=1)
        shell.grid_rowconfigure(1, weight=0)  # Status Bar
        shell.grid_columnconfigure(1, weight=1)

        # Left Sidebar Frame (Spotify playlist style - narrow width and scrollable list)
        sidebar = ctk.CTkFrame(shell, width=190, fg_color=COLOR_SIDEBAR_BG, corner_radius=0, border_color=COLOR_BORDER, border_width=0)
        sidebar.grid(row=0, column=0, rowspan=2, sticky="ns")
        sidebar.grid_propagate(False)

        # Brand / Logo inside Sidebar (Compact horizontal layout)
        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=16, pady=(16, 8))
        badge_label = self.create_logo_widget(brand, "header", size=24)
        badge_label.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(brand, text="Scrcpy Deck", font=self.fonts["section"], text_color=COLOR_TEXT_PRIMARY).pack(side="left")

        # Sidebar Menu items container (Spotify Playlist style - no scrollbar)
        self.sidebar_nav_scroll = ctk.CTkFrame(sidebar, fg_color="transparent", corner_radius=0, border_width=0)
        self.sidebar_nav_scroll.pack(fill="both", expand=True, padx=4, pady=(10, 10))

        self.sidebar_nav_buttons = {}
        tab_mappings = [
            ("Quick Connect", "connection"),
            ("Saved Devices", "devices"),
            ("Display & Quality", "display"),
            ("Advanced Controls", "advanced"),
            ("Terminal Console", "console"),
            ("Guidance & Help", "help")
        ]
        for tab_name, icon_name in tab_mappings:
            btn = SidebarNavItem(self.sidebar_nav_scroll, tab_name, icon_name, lambda t=tab_name: self.switch_tab(t), self)
            btn.pack(fill="x", pady=0)
            self.sidebar_nav_buttons[tab_name] = btn

        # Sidebar footer (Compact, single-line)
        sidebar_footer = ctk.CTkFrame(sidebar, fg_color="transparent")
        sidebar_footer.pack(side="bottom", fill="x", padx=16, pady=10)
        ctk.CTkLabel(sidebar_footer, text=f"v{CURRENT_VERSION} · by EXPOSUREEE", font=self.fonts["caption"], text_color=COLOR_TEXT_MUTED).pack(anchor="w")

        # Main Workspace Panel
        workspace = ctk.CTkFrame(shell, fg_color="transparent")
        workspace.grid(row=0, column=1, sticky="nsew", padx=20, pady=(20, 10))

        # Header Area
        header_bar = ctk.CTkFrame(workspace, fg_color="transparent")
        header_bar.pack(fill="x", pady=(0, 16))
        
        header_text = ctk.CTkFrame(header_bar, fg_color="transparent")
        header_text.pack(side="left", fill="both", expand=True)
        
        self.page_title_label = ctk.CTkLabel(header_text, text="Quick Connect", font=self.fonts["title"], text_color=COLOR_TEXT_PRIMARY, anchor="w")
        self.page_title_label.pack(anchor="w")
        
        self.page_subtitle_label = ctk.CTkLabel(header_text, text="Connect Android devices wirelessly or over USB.", font=self.fonts["caption"], text_color=COLOR_TEXT_MUTED, anchor="w")
        self.page_subtitle_label.pack(anchor="w", pady=(2, 0))

        header_actions = ctk.CTkFrame(header_bar, fg_color="transparent")
        header_actions.pack(side="right", fill="y", anchor="e")
        
        self.btn_start = self.make_primary_button(header_actions, "▶  Start Mirroring", self.start_scrcpy)
        self.btn_start.pack(side="right", padx=(10, 0))
        
        self.btn_gear = ctk.CTkButton(
            header_actions,
            text="",
            image=get_ctk_icon("advanced", size=(20, 20)),
            width=40,
            height=40,
            fg_color=COLOR_FIELD_BG,
            hover_color=COLOR_CARD_HOVER,
            border_color=COLOR_BORDER,
            border_width=1,
            corner_radius=8,
            command=self.open_quick_settings
        )
        self.btn_gear.pack(side="right", padx=(0, 0))

        # Page Frames Container
        self.body_container = ctk.CTkFrame(workspace, fg_color="transparent")
        self.body_container.pack(fill="both", expand=True)

        self.tab_frames = {}
        for tab_name, _ in tab_mappings:
            frame = ctk.CTkFrame(self.body_container, fg_color="transparent")
            self.tab_frames[tab_name] = frame

        # Build each tab layout
        self.build_quick_connect_tab(self.tab_frames["Quick Connect"])
        self.build_saved_devices_tab(self.tab_frames["Saved Devices"])
        self.build_display_quality_tab(self.tab_frames["Display & Quality"])
        self.build_advanced_controls_tab(self.tab_frames["Advanced Controls"])
        self.build_terminal_console_tab(self.tab_frames["Terminal Console"])
        self.build_guidance_help_tab(self.tab_frames["Guidance & Help"])

        # Default Active Tab
        self.switch_tab("Quick Connect")

        # Bottom Status Bar
        status_bar = ctk.CTkFrame(shell, height=36, fg_color=COLOR_SIDEBAR_BG, border_color=COLOR_BORDER, border_width=1)
        status_bar.grid(row=1, column=1, sticky="ew")
        status_bar.grid_propagate(False)

        # Status Led Point & Label
        self.status_led = ctk.CTkFrame(status_bar, width=10, height=10, corner_radius=5, fg_color=COLOR_DANGER)
        self.status_led.pack(side="left", padx=(16, 6))
        
        status_lbl = ctk.CTkLabel(status_bar, textvariable=self.status_var, font=self.fonts["caption_bold"], text_color=COLOR_TEXT_PRIMARY)
        status_lbl.pack(side="left")

        # Session Metrics Preview
        session_lbl = ctk.CTkLabel(status_bar, textvariable=self.connection_summary_var, font=self.fonts["caption"], text_color=COLOR_TEXT_MUTED)
        session_lbl.pack(side="right", padx=16)

    def switch_tab(self, tab_name):
        old_to_new = {
            "Connection": "Quick Connect",
            "Saved Devices": "Saved Devices",
            "Video & Audio": "Display & Quality",
            "Advanced": "Advanced Controls",
            "Console": "Terminal Console",
            "Tutorials": "Guidance & Help"
        }
        tab_name = old_to_new.get(tab_name, tab_name)

        for frame in self.tab_frames.values():
            frame.pack_forget()
        
        if tab_name in self.tab_frames:
            self.tab_frames[tab_name].pack(fill="both", expand=True)

        for name, item in self.sidebar_nav_buttons.items():
            item.set_active(name == tab_name)

        self.page_title_label.configure(text=tab_name)
        
        subtitles = {
            "Quick Connect": "Scan, pair, and connect Android devices over USB or Wi-Fi.",
            "Saved Devices": "Manage and reconnect to previously connected wireless devices.",
            "Display & Quality": "Configure stream bitrate, frame limit, resolution, and codecs.",
            "Advanced Controls": "Control screen state, window properties, and camera options.",
            "Terminal Console": "Execute ADB terminal commands and monitor raw system outputs.",
            "Guidance & Help": "View setup guides, troubleshooting steps, and documentation."
        }
        self.page_subtitle_label.configure(text=subtitles.get(tab_name, "Configure your mirroring session."))


    # --- TAB PAGE 1: QUICK CONNECT ---
    def build_quick_connect_tab(self, parent):
        canvas = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        canvas.pack(fill="both", expand=True)

        # Double column layout
        grid_frame = ctk.CTkFrame(canvas, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True)
        grid_frame.grid_columnconfigure(0, weight=8) # Left column (USB & Wireless Setup)
        grid_frame.grid_columnconfigure(1, weight=1) # Right column (Readouts & Help)

        col1 = ctk.CTkFrame(grid_frame, fg_color="transparent")
        col1.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        col2 = ctk.CTkFrame(grid_frame, fg_color="transparent")
        col2.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # LEFT COLUMN CARDS
        # Card 1: USB Devices Selector
        usb_card = self.make_card(col1, "Active Devices", "Select a connected USB or Wireless ADB target.")
        usb_card.pack(fill="x", pady=(0, 16))
        
        inner_usb = ctk.CTkFrame(usb_card, fg_color="transparent")
        inner_usb.pack(fill="x", padx=20, pady=(10, 20))
        
        self.device_combo = self.make_combo(inner_usb, values=[], command=lambda _: self.refresh_dashboard_state())
        self.device_combo.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.make_action_button(inner_usb, "Scan Devices", self.refresh_devices, width=110).pack(side="left")

        # Card 2: Wireless Mode Setup
        wireless_card = self.make_card(col1, "Wireless ADB (Wi-Fi)", "Pair and connect wirelessly over the local network.")
        wireless_card.pack(fill="x")

        self.wireless_method_var = ctk.StringVar(value="USB Assisted")
        self.wireless_method_segmented = ctk.CTkSegmentedButton(
            wireless_card, values=["USB Assisted", "Direct Pairing (Android 11+)"],
            variable=self.wireless_method_var, font=self.fonts["body_bold"],
            fg_color=COLOR_FIELD_BG, selected_color=COLOR_ACCENT,
            selected_hover_color=COLOR_ACCENT_HOVER, unselected_color=COLOR_FIELD_BG,
            unselected_hover_color=COLOR_CARD_HOVER, command=self.toggle_wireless_method
        )
        self.wireless_method_segmented.pack(fill="x", padx=20, pady=(10, 12))

        # Container with fixed height to prevent card resize stutters
        self.wireless_content_container = ctk.CTkFrame(wireless_card, fg_color="transparent", height=165)
        self.wireless_content_container.pack(fill="x", padx=0, pady=0)
        self.wireless_content_container.pack_propagate(False)

        # USB Assisted wireless frame
        self.usb_wireless_frame = ctk.CTkFrame(self.wireless_content_container, fg_color="transparent")
        self.usb_wireless_frame.pack(side="top", fill="x")
        
        r_ip = ctk.CTkFrame(self.usb_wireless_frame, fg_color="transparent")
        r_ip.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(r_ip, text="Device IP", width=80, anchor="w", text_color=COLOR_TEXT_MUTED, font=self.fonts["body"]).pack(side="left")
        self.make_input(r_ip, textvariable=self.var_ip, placeholder_text="192.168.1.15").pack(side="left", fill="x", expand=True, padx=(10, 10))
        self.make_action_button(r_ip, "Auto get IP", self.get_device_ip, width=100).pack(side="right")

        r_wbtn = ctk.CTkFrame(self.usb_wireless_frame, fg_color="transparent")
        r_wbtn.pack(fill="x", padx=20, pady=(0, 20))
        self.make_action_button(r_wbtn, "Enable TCP/IP Mode", self.enable_tcpip, width=150).pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.make_action_button(r_wbtn, "Connect Wirelessly", self.connect_wireless, width=150).pack(side="left", fill="x", expand=True, padx=(6, 0))

        # Direct wireless pairing frame
        self.direct_wireless_frame = ctk.CTkFrame(self.wireless_content_container, fg_color="transparent")

        r_direct_ip = ctk.CTkFrame(self.direct_wireless_frame, fg_color="transparent")
        r_direct_ip.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(r_direct_ip, text="Device IP", width=80, anchor="w", text_color=COLOR_TEXT_MUTED, font=self.fonts["body"]).pack(side="left")
        self.make_input(r_direct_ip, textvariable=self.var_ip, placeholder_text="192.168.1.15").pack(side="left", fill="x", expand=True, padx=(10, 10))
        ctk.CTkLabel(r_direct_ip, text="Pair Port", width=60, anchor="w", text_color=COLOR_TEXT_MUTED, font=self.fonts["body"]).pack(side="left")
        self.make_input(r_direct_ip, textvariable=self.var_pair_port, placeholder_text="37283", width=70).pack(side="left", padx=(10, 0))
        
        r_direct_code = ctk.CTkFrame(self.direct_wireless_frame, fg_color="transparent")
        r_direct_code.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(r_direct_code, text="Pair Code", width=80, anchor="w", text_color=COLOR_TEXT_MUTED, font=self.fonts["body"]).pack(side="left")
        self.make_input(r_direct_code, textvariable=self.var_pair_code, placeholder_text="123456").pack(side="left", fill="x", expand=True, padx=(10, 10))
        self.make_action_button(r_direct_code, "Pair Device", self.pair_wireless, width=100).pack(side="right")
        
        r_direct_connect = ctk.CTkFrame(self.direct_wireless_frame, fg_color="transparent")
        r_direct_connect.pack(fill="x", padx=20, pady=(0, 20))
        ctk.CTkLabel(r_direct_connect, text="Connect Port", width=80, anchor="w", text_color=COLOR_TEXT_MUTED, font=self.fonts["body"]).pack(side="left")
        self.make_input(r_direct_connect, textvariable=self.var_connect_port, placeholder_text="42911").pack(side="left", fill="x", expand=True, padx=(10, 10))
        self.make_action_button(r_direct_connect, "Auto-detect", self.auto_detect_port, width=100).pack(side="left")
        self.make_action_button(r_direct_connect, "Connect", self.connect_wireless_direct, width=100, fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER).pack(side="right", padx=(10, 0))

        # RIGHT COLUMN CARDS
        # Card 1: Session Stats / Readouts
        stats_card = self.make_card(col2, "Session Readouts", "Live updates on current configurations.")
        stats_card.pack(fill="x", pady=(0, 16))
        
        self.make_info_row(stats_card, "ADB Connection", self.connection_summary_var, accent=True)
        self.make_info_row(stats_card, "Source Format", self.source_summary_var)
        self.make_info_row(stats_card, "Stream Quality", self.quality_summary_var)
        self.make_info_row(stats_card, "Audio Settings", self.audio_summary_var)
        self.make_info_row(stats_card, "Window Mode", self.window_summary_var)
        self.make_info_row(stats_card, "Recording Capture", self.recording_detail_var)
        ctk.CTkLabel(stats_card, text="", height=4).pack()

        # Card 2: Interactive Next-Step Guidance
        self.guidance_card = self.make_card(col2, "Interactive Setup Guide", "Step-by-step assistant for new mirroring sessions.")
        self.guidance_card.configure(border_color=COLOR_ACCENT, border_width=1.5)
        self.guidance_card.pack(fill="x", pady=(0, 16))
        
        ctk.CTkLabel(self.guidance_card, textvariable=self.guidance_step_var, font=self.fonts["caption_bold"], text_color=COLOR_ACCENT_HOVER, justify="left", anchor="w").pack(fill="x", padx=20, pady=(4, 2))
        ctk.CTkLabel(self.guidance_card, textvariable=self.guidance_title_var, font=self.fonts["body_bold"], text_color=COLOR_TEXT_PRIMARY, justify="left", anchor="w").pack(fill="x", padx=20, pady=(0, 6))
        ctk.CTkLabel(self.guidance_card, textvariable=self.guidance_detail_var, font=self.fonts["body"], text_color=COLOR_TEXT_MUTED, justify="left", anchor="w", wraplength=340).pack(fill="x", padx=20, pady=(0, 14))
        
        self.guidance_action_frame = ctk.CTkFrame(self.guidance_card, fg_color="transparent")
        self.guidance_action_frame.pack(fill="x", padx=20, pady=(0, 18))
        
        self.guidance_button = self.make_primary_button(self.guidance_action_frame, "Scan Devices", self.run_guidance_action, height=40)
        self.guidance_button.pack(fill="x")
        
        self.guidance_button_2 = self.make_action_button(self.guidance_action_frame, "Secondary Action", self.run_guidance_action_2)
        self.guidance_button_2.pack(fill="x", pady=(8, 0))
        self.guidance_button_2.pack_forget()

        # Card 3: Quick Utilities panel
        utils_card = self.make_card(col2, "ADB Controls", "Quick utility commands for host configuration.")
        utils_card.pack(fill="x")
        
        grid_utils = ctk.CTkFrame(utils_card, fg_color="transparent")
        grid_utils.pack(fill="x", padx=20, pady=(8, 20))
        grid_utils.grid_columnconfigure((0, 1), weight=1)
        
        self.make_action_button(grid_utils, "Kill ADB Server", self.kill_adb_server, width=120).grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=6)
        self.make_action_button(grid_utils, "Reset Connections", self.reset_device_connection, width=120).grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=6)
        self.make_action_button(grid_utils, "Project Page", self.open_download, width=120).grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=6)
        self.make_action_button(grid_utils, "Support Creator", self.donate_upi, width=120, fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER).grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=6)

    def toggle_wireless_method(self, method):
        if method == "USB Assisted":
            if hasattr(self, "direct_wireless_frame"):
                self.direct_wireless_frame.pack_forget()
            if hasattr(self, "usb_wireless_frame"):
                self.usb_wireless_frame.pack(side="top", fill="x")
        else:
            if hasattr(self, "usb_wireless_frame"):
                self.usb_wireless_frame.pack_forget()
            if hasattr(self, "direct_wireless_frame"):
                self.direct_wireless_frame.pack(side="top", fill="x")


    # --- TAB PAGE 2: SAVED DEVICES ---
    def build_saved_devices_tab(self, parent):
        self.saved_devices_scroll_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.saved_devices_scroll_frame.pack(fill="both", expand=True)
        self.refresh_saved_devices_ui()

    def refresh_saved_devices_ui(self):
        if not hasattr(self, "saved_devices_scroll_frame"):
            return
            
        for widget in self.saved_devices_scroll_frame.winfo_children():
            widget.destroy()
            
        if not getattr(self, "saved_devices", []):
            empty_card = self.make_card(
                self.saved_devices_scroll_frame, "No Saved Devices Yet",
                "Your paired devices will automatically save here once connected wirelessly or over USB."
            )
            empty_card.pack(fill="x", pady=10)
            return
            
        for dev in self.saved_devices:
            dev_type = dev.get("type", "usb")
            icon_char = "🔌" if dev_type == "usb" else "📶"
            nickname = dev.get("nickname", "")
            brand = dev.get("brand", "")
            model = dev.get("model", "")
            serial = dev.get("serial", "")
            ip = dev.get("ip", "")
            
            title = nickname if nickname else f"{brand} {model}".strip() or "Android Device"
            subtitle = f"{brand} {model}".strip() if nickname else ""
            
            card = ctk.CTkFrame(self.saved_devices_scroll_frame, fg_color=COLOR_CARD_BG, border_color=COLOR_BORDER, border_width=1, corner_radius=12)
            card.pack(fill="x", pady=6)
            
            left_frame = ctk.CTkFrame(card, fg_color="transparent")
            left_frame.pack(side="left", fill="both", expand=True, padx=16, pady=12)
            
            icon_lbl = ctk.CTkLabel(left_frame, text=icon_char, font=self.fonts["section"], width=32)
            icon_lbl.pack(side="left", padx=(0, 12))
            
            info_subframe = ctk.CTkFrame(left_frame, fg_color="transparent")
            info_subframe.pack(side="left", fill="y", expand=True)
            
            title_lbl = ctk.CTkLabel(info_subframe, text=title, font=self.fonts["body_bold"], text_color=COLOR_TEXT_PRIMARY, anchor="w")
            title_lbl.pack(anchor="w")
            
            sub_lbl_text = ""
            if dev_type == "wireless":
                sub_lbl_text = f"IP: {ip}"
                if subtitle: sub_lbl_text = f"{subtitle} • IP: {ip}"
            else:
                sub_lbl_text = f"USB Serial: {serial}"
                if subtitle: sub_lbl_text = f"{subtitle} • Serial: {serial}"
                    
            sub_lbl = ctk.CTkLabel(info_subframe, text=sub_lbl_text, font=self.fonts["caption"], text_color=COLOR_TEXT_MUTED, anchor="w")
            sub_lbl.pack(anchor="w", pady=(2, 0))
            
            right_frame = ctk.CTkFrame(card, fg_color="transparent")
            right_frame.pack(side="right", padx=16, pady=12)
            
            remove_btn = self.make_action_button(right_frame, "❌", lambda d=dev: self.remove_saved_device(d), width=40, fg_color="#bf3b3b", hover_color="#9e2e2e")
            remove_btn.pack(side="right", padx=(8, 0))
            
            edit_btn = self.make_action_button(right_frame, "✏️ Edit", lambda d=dev: self.edit_saved_device(d), width=70)
            edit_btn.pack(side="right", padx=(8, 0))
            
            connect_btn = self.make_action_button(right_frame, "⚡ Connect", lambda d=dev: self.connect_saved_device(d), width=100, fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER)
            connect_btn.pack(side="right")


    # --- TAB PAGE 3: DISPLAY & QUALITY ---
    def build_display_quality_tab(self, parent):
        canvas = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        canvas.pack(fill="both", expand=True)

        # Card 1: Sliders for Bitrate, FPS, Max Resolution
        slider_card = self.make_card(canvas, "Quality Sliders", "Set limits for video stream output bandwidth and frame rates.")
        slider_card.pack(fill="x", pady=(0, 16))
        
        inner_sliders = ctk.CTkFrame(slider_card, fg_color="transparent")
        inner_sliders.pack(fill="x", padx=20, pady=(10, 20))
        
        self.make_labeled_slider(inner_sliders, "Stream Bitrate", self.var_bitrate, 1, 64, lambda v: f"{v} Mbps").pack(fill="x", pady=8)
        self.make_labeled_slider(inner_sliders, "Max FPS Limit", self.var_max_fps, 0, 120, lambda v: "Auto" if v == 0 else f"{v} FPS").pack(fill="x", pady=8)
        self.make_labeled_slider(inner_sliders, "Max Resolution Size", self.var_max_size, 0, 2560, lambda v: "Native Size" if v == 0 else f"{v}px").pack(fill="x", pady=8)

        # Card 2: Codecs and Renderer Selection
        codecs_card = self.make_card(canvas, "Codecs & Rendering", "Select system render driver and encoding formats.")
        codecs_card.pack(fill="x", pady=(0, 16))
        
        inner_codecs = ctk.CTkFrame(codecs_card, fg_color="transparent")
        inner_codecs.pack(fill="x", padx=20, pady=(10, 20))
        
        r_vid = ctk.CTkFrame(inner_codecs, fg_color="transparent")
        r_vid.pack(fill="x", pady=6)
        self.make_labeled_combo_row(r_vid, "Video Codec", self.var_video_codec, ["h264", "h265", "av1"], width=150, label_width=120).pack(side="left")
        self.make_labeled_combo_row(r_vid, "Audio Codec", self.var_audio_codec, ["opus", "aac", "raw"], width=150, label_width=120).pack(side="left", padx=(40, 0))

        r_rend = ctk.CTkFrame(inner_codecs, fg_color="transparent")
        r_rend.pack(fill="x", pady=6)
        self.make_labeled_combo_row(r_rend, "Render Driver", self.renderer_combo_val, ["auto", "direct3d", "opengl", "metal", "software"], width=150, label_width=120).pack(side="left")

        # Card 3: Audio Switches
        audio_card = self.make_card(canvas, "Audio Options", "Configure hardware audio forwarding flags.")
        audio_card.pack(fill="x")
        
        inner_audio = ctk.CTkFrame(audio_card, fg_color="transparent")
        inner_audio.pack(fill="x", padx=20, pady=(10, 20))
        
        self.make_checkbox(inner_audio, "Mute Device Audio Forwarding", self.var_no_audio).pack(anchor="w", pady=4)


    # --- TAB PAGE 4: ADVANCED CONTROLS ---
    def build_advanced_controls_tab(self, parent):
        canvas = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        canvas.pack(fill="both", expand=True)

        # Card 1: Window Behavior switches
        win_card = self.make_card(canvas, "Window Options", "Manage viewport styles and positioning.")
        win_card.pack(fill="x", pady=(0, 16))
        
        inner_win = ctk.CTkFrame(win_card, fg_color="transparent")
        inner_win.pack(fill="x", padx=20, pady=(10, 12))
        
        self.make_checkbox(inner_win, "Keep Mirror Window Always on Top", self.var_always_on_top).pack(anchor="w", pady=4)
        self.make_checkbox(inner_win, "Start in Fullscreen Mode", self.var_fullscreen).pack(anchor="w", pady=4)
        self.make_checkbox(inner_win, "Borderless Window Frame", self.var_borderless).pack(anchor="w", pady=4)
        
        r_orient = ctk.CTkFrame(win_card, fg_color="transparent")
        r_orient.pack(fill="x", padx=20, pady=(4, 20))
        self.make_labeled_combo_row(
            r_orient, "Orientation", self.orientation_combo_val,
            ["Auto (Rotate with Phone)", "Portrait (@0)", "Landscape (@90)", "Portrait Reversed (@180)", "Landscape Reversed (@270)"],
            width=230, label_width=100
        ).pack(side="left")

        # Card 2: Device control behaviors
        dev_behav_card = self.make_card(canvas, "Device Controls", "Configure physical hardware states during sessions.")
        dev_behav_card.pack(fill="x", pady=(0, 16))
        
        inner_dev_behav = ctk.CTkFrame(dev_behav_card, fg_color="transparent")
        inner_dev_behav.pack(fill="x", padx=20, pady=(10, 20))
        
        self.make_checkbox(inner_dev_behav, "Prevent Device from Sleeping (Stay Awake)", self.var_stay_awake).pack(anchor="w", pady=4)
        self.make_checkbox(inner_dev_behav, "Turn Physical Device Screen OFF while mirroring", self.var_screen_off).pack(anchor="w", pady=4)
        self.make_checkbox(inner_dev_behav, "Show Touch Points on screen", self.var_show_touches).pack(anchor="w", pady=4)
        self.make_checkbox(inner_dev_behav, "Read-Only View (Disable Keyboard/Mouse control)", self.var_no_control).pack(anchor="w", pady=4)

        # Card 3: Camera mode settings
        cam_card = self.make_card(canvas, "Scrcpy Camera Options", "Configure parameters for using phone as desktop camera input.")
        cam_card.pack(fill="x", pady=(0, 16))
        
        inner_cam = ctk.CTkFrame(cam_card, fg_color="transparent")
        inner_cam.pack(fill="x", padx=20, pady=(10, 20))
        
        r_src = ctk.CTkFrame(inner_cam, fg_color="transparent")
        r_src.pack(fill="x", pady=6)
        ctk.CTkLabel(r_src, text="Mirror Source", width=120, anchor="w", text_color=COLOR_TEXT_MUTED, font=self.fonts["body_bold"]).pack(side="left")
        self.make_radio(r_src, "Screen", "screen").pack(side="left", padx=(10, 18))
        self.make_radio(r_src, "Back Camera", "camera_back").pack(side="left", padx=(0, 18))
        self.make_radio(r_src, "Front Camera", "camera_front").pack(side="left", padx=(0, 18))
        self.make_radio(r_src, "Microphone Only", "mic_only").pack(side="left")

        r_cam_ar = ctk.CTkFrame(inner_cam, fg_color="transparent")
        r_cam_ar.pack(fill="x", pady=6)
        self.make_labeled_combo_row(r_cam_ar, "Camera Aspect Ratio", self.cam_ar_combo_val, ["Full Sensor (Default)", "4:3", "16:9"], width=180, label_width=140).pack(side="left")
        self.make_labeled_combo_row(r_cam_ar, "Camera Orientation", self.cam_orientation_combo_val, ["0° (Default)", "90°", "180°", "270°"], width=180, label_width=140).pack(side="left", padx=(40, 0))

        # Card 4: Extras (Record / Debug Console)
        extras_card = self.make_card(canvas, "Record & Debug Extras", "Capture mirroring sessions and output detailed logs.")
        extras_card.pack(fill="x")
        
        inner_extras = ctk.CTkFrame(extras_card, fg_color="transparent")
        inner_extras.pack(fill="x", padx=20, pady=(10, 20))
        
        self.make_checkbox(inner_extras, "Record stream output to MP4 file", self.var_record).pack(anchor="w", pady=4)
        self.make_checkbox(inner_extras, "Enable ADB debug console window", self.var_debug_mode).pack(anchor="w", pady=4)


    # --- TAB PAGE 5: TERMINAL CONSOLE ---
    def build_terminal_console_tab(self, parent):
        console_frame = ctk.CTkFrame(parent, fg_color="transparent")
        console_frame.pack(fill="both", expand=True)
        
        console_card = self.make_card(console_frame, "ADB Terminal Shell", "Submit direct ADB or console commands. Inspect standard outputs.")
        console_card.pack(fill="both", expand=True)
        
        console_actions = ctk.CTkFrame(console_card, fg_color="transparent")
        console_actions.pack(fill="x", padx=20, pady=(10, 10))
        
        self.console_command_var = ctk.StringVar()
        self.console_command_entry = self.make_input(console_actions, textvariable=self.console_command_var, placeholder_text="e.g. adb devices or scrcpy --version")
        self.console_command_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.console_command_entry.bind("<Return>", self.execute_console_command)
        
        self.make_action_button(console_actions, "Run", self.execute_console_command, width=90).pack(side="left", padx=(0, 8))
        self.make_action_button(console_actions, "Clear Log", self.clear_console, width=110).pack(side="left")

        ctk.CTkLabel(
            console_card,
            text="💡 Commands execute within application workspace directory. Supports PowerShell, ADB, and Scrcpy runtime arguments.",
            font=self.fonts["caption"], text_color=COLOR_TEXT_MUTED, anchor="w"
        ).pack(fill="x", padx=20, pady=(0, 8))

        self.console_textbox = ctk.CTkTextbox(
            console_card, fg_color=COLOR_CONSOLE_BG, border_color=COLOR_BORDER,
            border_width=1, text_color=COLOR_TEXT_PRIMARY, corner_radius=12,
            font=self.fonts["console"], activate_scrollbars=True, wrap="word"
        )
        self.console_textbox.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.console_textbox.configure(state="disabled")
        
        self.setup_console_tags()
        self.setup_console_scroll_isolation()
        self.console_mgr.log("INFO", "Console initialized.")


    # --- TAB PAGE 6: GUIDANCE & HELP ---
    def build_guidance_help_tab(self, parent):
        content_area = ctk.CTkFrame(parent, fg_color="transparent")
        content_area.pack(fill="both", expand=True)

        self.tutorial_nav_var = ctk.StringVar(value="USB Debugging")
        self.tutorial_nav_segmented = ctk.CTkSegmentedButton(
            content_area, values=["USB Debugging", "Docs & Website", "Videos", "faQs"],
            variable=self.tutorial_nav_var, font=self.fonts["body_bold"],
            fg_color=COLOR_FIELD_BG, selected_color=COLOR_ACCENT,
            selected_hover_color=COLOR_ACCENT_HOVER, unselected_color=COLOR_FIELD_BG,
            unselected_hover_color=COLOR_CARD_HOVER, command=self.switch_subtab
        )
        self.tutorial_nav_segmented.pack(fill="x", pady=(0, 12))

        self.subtab_container = ctk.CTkFrame(content_area, fg_color="transparent")
        self.subtab_container.pack(fill="both", expand=True)

        self.subtab_frames = {}
        for sub in ["USB Debugging", "Docs & Website", "Videos", "faQs"]:
            self.subtab_frames[sub] = ctk.CTkScrollableFrame(self.subtab_container, fg_color="transparent")

        # 1. USB Debugging Brand Instructions
        usb_frame = self.subtab_frames["USB Debugging"]
        brands_card = self.make_card(usb_frame, "Smartphones Brand Guides", "Find configuration options for your specific phone manufacturer.")
        brands_card.pack(fill="x", pady=(0, 16))
        
        grid_brands = ctk.CTkFrame(brands_card, fg_color="transparent")
        grid_brands.pack(fill="x", padx=20, pady=(10, 12))
        
        brand_names = ["Samsung", "Xiaomi", "OnePlus", "Oppo", "Vivo", "Realme", "Motorola", "Others"]
        self.links_container = ctk.CTkFrame(brands_card, fg_color=COLOR_FIELD_BG, corner_radius=12)
        
        for i, brand in enumerate(brand_names):
            row = i // 4
            col = i % 4
            grid_brands.grid_columnconfigure(col, weight=1)
            btn = ctk.CTkButton(
                grid_brands, text=brand, command=lambda b=brand: self.show_brand_videos(b),
                fg_color=COLOR_FIELD_BG, hover_color=COLOR_CARD_HOVER, border_color=COLOR_BORDER,
                border_width=1, text_color=COLOR_TEXT_PRIMARY, font=self.fonts["body"]
            )
            btn.grid(row=row, column=col, sticky="ew", padx=4, pady=4)

        # 2. Written Documentation
        docs_frame = self.subtab_frames["Docs & Website"]
        docs_card = self.make_card(docs_frame, "Written Documentation & GitHub", "Access official resources and source codes.")
        docs_card.pack(fill="x", pady=(0, 16))
        
        inner_docs = ctk.CTkFrame(docs_card, fg_color="transparent")
        inner_docs.pack(fill="x", padx=20, pady=(10, 20))
        
        self.make_action_button(inner_docs, "GitHub Repository", lambda: webbrowser.open("https://github.com/EXPOSUREEE"), width=200).pack(side="left", padx=(0, 12))
        self.make_action_button(inner_docs, "Official Website & Downloads", lambda: webbrowser.open("https://exposureee.in/scrcpy-gui-by-exposureee/"), width=240).pack(side="left")

        # 3. Video Guides
        videos_frame = self.subtab_frames["Videos"]
        video_card = self.make_card(videos_frame, "Video tutorials by EXPOSUREEE", "Step-by-step video instructions from the creator.")
        video_card.pack(fill="x", pady=(0, 16))
        
        inner_video = ctk.CTkFrame(video_card, fg_color="transparent")
        inner_video.pack(fill="x", padx=20, pady=(10, 20))
        
        videos = [
            ("I Updated Scrcpy GUI: Now It's Perfect for Android Screen Mirroring", "https://youtu.be/U7byl9CLkU4"),
            ("Best Free Android to PC Screen Mirroring Software in 2025", "https://youtu.be/pWKY_dntX5c"),
            ("Screen Mirroring of BGMI & Free Fire : Mic / Audio Problem Fixed", "https://youtu.be/I8-rieyx7h8"),
            ("I Updated My Android to PC Screen Mirroring Software - No More Errors", "https://youtu.be/-4pRCRFoCZg"),
            ("New Android to PC Screen Mirroring Software with Amazing Features", "https://youtu.be/dWj5Mw2k3BE"),
            ("Free Android to PC Screen Mirroring Software just for You", "https://youtu.be/WHUsT8Hekoc"),
            ("SCRCPY have MORE FEATURES than ApowerMirror & Douwan", "https://youtu.be/smVw6w8bTKk"),
        ]
        for title, url in videos:
            btn = self.make_action_button(inner_video, f"▶  {title}", lambda u=url: webbrowser.open(u), width=500)
            btn.pack(fill="x", pady=6)
            btn.configure(anchor="w")

        # 4. Frequently Asked Questions
        faqs_frame = self.subtab_frames["faQs"]
        faq_card = self.make_card(faqs_frame, "Frequently Asked Questions", "Quick solutions to common configuration problems.")
        faq_card.pack(fill="x", pady=(0, 16))
        
        inner_faq = ctk.CTkFrame(faq_card, fg_color="transparent")
        inner_faq.pack(fill="x", padx=20, pady=(10, 20))
        
        faqs = [
            ("Q: My phone is not detected when I scan?", "A: Make sure Developer Options are unlocked and 'USB debugging' is enabled on your phone. Re-plug the USB and check for an authorization prompt on your phone's screen."),
            ("Q: How do I connect wirelessly?", "A: First connect via USB. Wait for it to show 'USB Connected' in the Next Step guide, then click 'Continue Wireless' -> 'Enable TCP/IP' -> 'Connect Wi-Fi'."),
            ("Q: Why is there no audio playing?", "A: Audio forwarding is only supported on Android 11+. Ensure you haven't checked 'Disable audio' in the Advanced tab."),
            ("Q: The stream is lagging or pixelated?", "A: In the Video & Audio tab, lower the Bitrate (e.g. 4 Mbps) or set a Max Size (e.g. 1080) to reduce the network/USB load.")
        ]
        for q, a in faqs:
            ctk.CTkLabel(inner_faq, text=q, font=self.fonts["body_bold"], text_color=COLOR_TEXT_PRIMARY, justify="left", anchor="w").pack(fill="x", pady=(8, 2))
            ctk.CTkLabel(inner_faq, text=a, font=self.fonts["body"], text_color=COLOR_TEXT_MUTED, justify="left", anchor="w", wraplength=720).pack(fill="x", pady=(0, 12))

        # Default Active Subtab
        self.switch_subtab("USB Debugging")

    def switch_subtab(self, subtab_name):
        for frame in self.subtab_frames.values():
            frame.pack_forget()
        if subtab_name in self.subtab_frames:
            self.subtab_frames[subtab_name].pack(fill="both", expand=True)

    def show_brand_videos(self, brand):
        for widget in self.links_container.winfo_children():
            widget.destroy()
        
        self.links_container.pack(fill="x", padx=20, pady=(0, 18))
        ctk.CTkLabel(self.links_container, text=f"Written Checklist for {brand}", font=self.fonts["body_bold"], text_color=COLOR_TEXT_PRIMARY).pack(anchor="w", padx=16, pady=(12, 8))
        
        steps = {
            "Samsung": ["Settings > About Phone > Software Info > Tap Build number 7 times.", "Settings > Developer Options > Enable USB Debugging."],
            "Xiaomi": ["Settings > About Phone > Tap MIUI version 7 times.", "Settings > Additional Settings > Developer Options > Enable USB Debugging & Install via USB & USB Debugging (Security Settings)."],
            "OnePlus": ["Settings > About Device > Version > Tap Build number 7 times.", "Settings > System/Additional Settings > Developer options > Enable USB debugging."],
            "Oppo": ["Settings > About Device > Version > Tap Build number 7 times.", "Settings > Additional Settings > Developer Options > Enable USB Debugging."],
            "Vivo": ["Settings > About Phone > Software info > Tap Build number 7 times.", "Settings > System management > Developer options > Enable USB debugging."],
            "Realme": ["Settings > About Device > Version > Tap Build number 7 times.", "Settings > Additional Settings > Developer Options > Enable USB Debugging."],
            "Motorola": ["Settings > About Phone > Tap Build number 7 times.", "Settings > System > Developer options > Enable USB debugging."],
            "Others": ["Check settings for 'Build number' or 'Software version'.", "Find Developer Options, and toggle USB Debugging ON."]
        }
        
        brand_steps = steps.get(brand, ["Connect via USB.", "Enable USB Debugging in Developer Options."])
        for i, step in enumerate(brand_steps, 1):
            ctk.CTkLabel(self.links_container, text=f"{i}. {step}", font=self.fonts["body"], text_color=COLOR_TEXT_MUTED, justify="left", anchor="w").pack(anchor="w", padx=20, pady=4)
        
        # Link to youtube search
        brand_query = urllib.parse.quote(f"how to enable usb debugging {brand}")
        search_url = f"https://www.youtube.com/results?search_query={brand_query}"
        self.make_action_button(self.links_container, f"🔍 Find {brand} video on YouTube", lambda: webbrowser.open(search_url), width=280).pack(anchor="w", padx=20, pady=(10, 14))


    # --- ADB AND SCRCPY CALLBACK HOOKS (Fully Synchronous/Asynchronous) ---
    def clear_connected_device_state(self, connection_text="Waiting for your first device scan"):
        self.var_ip.set("")
        self.device_count_var.set("0")
        self.connection_summary_var.set(connection_text)
        self.workflow_tcpip_enabled = False
        self.workflow_wireless_ready = False
        self.update_status_led("disconnected")
        if hasattr(self, "device_combo"):
            try:
                self.device_combo.configure(values=["No devices found"])
                self.device_combo.set("No devices found")
            except Exception: pass
        self.clear_workflow_issue()

    def update_status_led(self, state):
        if not hasattr(self, "status_led") or not self.status_led.winfo_exists():
            return
        if state == "connected":
            self.status_led.configure(fg_color=COLOR_SUCCESS)
        elif state == "scanning":
            self.status_led.configure(fg_color=COLOR_WARNING)
        else:
            self.status_led.configure(fg_color=COLOR_DANGER)

    def refresh_devices(self):
        self.set_status("Scanning connected Android devices...")
        self.update_status_led("scanning")
        self.root.update_idletasks()

        def on_success(devices):
            self.root.after(0, self._refresh_devices_success, devices)
        def on_error(reason):
            self.root.after(0, self._refresh_devices_error, reason)

        self.adb.refresh_devices(on_success, on_error)

    def _refresh_devices_success(self, devices):
        self.device_infos = devices
        self.device_label_to_serial = {}
        self.device_serial_to_label = {}
        
        display_names = []
        name_counts = {}
        for d in devices:
            name_counts[d.display_name] = name_counts.get(d.display_name, 0) + 1
            
        for d in devices:
            label = d.display_name
            if name_counts[d.display_name] > 1:
                label = f"{d.display_name} · {d.serial[:6]}"
            display_names.append(label)
            self.device_label_to_serial[label] = d.serial
            self.device_serial_to_label[d.serial] = label
            self.auto_save_device(d)

        preferred_wireless_serial = f"{self.var_ip.get().strip()}:5555" if self.var_ip.get().strip() else ""
        selected_serial = preferred_wireless_serial if preferred_wireless_serial in self.device_serial_to_label else devices[0].serial
        selected_label = self.device_serial_to_label[selected_serial]
        
        self.device_combo.configure(values=display_names)
        self.device_combo.set(selected_label)
        self.device_count_var.set(str(len(devices)))
        self.workflow_wireless_ready = ":" in selected_serial
        
        self.update_status_led("connected")
        if self.workflow_wireless_ready:
            self.connection_summary_var.set(f"Wireless ready on {selected_label}")
            self.set_status(f"Wireless device detected: {selected_label}")
        else:
            self.connection_summary_var.set(f"USB ready on {selected_label}")
            self.set_status(f"Connected device detected: {selected_label}")
        self.console_mgr.log("INFO", f"Selected device: {selected_label} [{selected_serial[:6]}]")
        self.clear_workflow_issue()

    def _refresh_devices_error(self, reason):
        self.device_count_var.set("0")
        self.workflow_wireless_ready = False
        self.update_status_led("disconnected")
        if reason == "no_devices":
            self.device_combo.configure(values=["No devices found"])
            self.device_combo.set("No devices found")
            self.connection_summary_var.set("No active ADB devices")
            self.set_status("No devices found.")
            self.set_workflow_issue(
                "No Android device is available right now.",
                "1. Connect via USB\n2. Turn ON USB debugging in Developer Options\n3. Click Scan devices.",
                self.refresh_devices, "Scan Devices"
            )
        else:
            self.connection_summary_var.set("ADB is not responding")
            self.set_status("ADB Error.")
            self.set_workflow_issue(
                "ADB did not answer the device scan request.",
                "Make sure adb is available, then retry or reset adb server.",
                self.kill_adb_server, "Kill ADB"
            )

    def get_device_ip(self):
        serial = self.get_selected_device()
        if not serial or serial == "No devices found":
            messagebox.showwarning("Error", "Select a device connected via USB first.")
            self.console_mgr.log("WARN", "Cannot fetch IP without a selected USB device.")
            self.set_workflow_issue(
                "The app needs a USB-connected device before it can fetch the Wi-Fi IP.",
                "Connect the phone with USB, then scan devices again.",
                self.refresh_devices, "Scan Devices"
            )
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
        self.set_workflow_issue(
            "The phone Wi-Fi address could not be detected.",
            "Turn on Wi-Fi for the phone, keep the USB connection active while fetching the address.",
            self.get_device_ip, "Auto get IP"
        )
        messagebox.showinfo("Info", "Could not automatically find IP.\nPlease check if Wi-Fi is connected on the phone.")

    def enable_tcpip(self):
        serial = self.get_selected_device()
        if not serial or serial == "No devices found":
            messagebox.showwarning("Error", "Select a device connected via USB first.")
            self.console_mgr.log("WARN", "Cannot enable TCP/IP without a selected USB device.")
            self.set_workflow_issue(
                "ADB over Wi-Fi cannot be enabled until a USB device is selected.",
                "Connect the phone over USB and scan devices first.",
                self.refresh_devices, "Scan Devices"
            )
            return
        self.set_status("Enabling ADB over TCP/IP on port 5555...")

        def on_success():
            self.root.after(0, self._enable_tcpip_success, serial)
        def on_error():
            self.root.after(0, self._enable_tcpip_error)

        self.adb.enable_tcpip(serial, on_success, on_error)

    def _enable_tcpip_success(self, serial):
        messagebox.showinfo("Success", "Wi-Fi mode enabled.\n\nNow you can unplug USB and click 'Connect Wirelessly'.")
        self.connection_summary_var.set("TCP/IP enabled on port 5555")
        self.set_status("Wi-Fi mode enabled on port 5555.")
        self.console_mgr.log("INFO", f"ADB TCP/IP enabled for {serial}.")
        self.workflow_tcpip_enabled = True
        self.clear_workflow_issue()

    def _enable_tcpip_error(self):
        self.set_status("Failed to enable Wi-Fi mode.")
        self.console_mgr.log("ERROR", "ADB TCP/IP mode could not be enabled.")
        self.workflow_tcpip_enabled = False
        self.set_workflow_issue(
            "ADB could not switch the phone into TCP/IP mode.",
            "Keep USB connected, confirm USB debugging is allowed, then try Enable TCP/IP again.",
            self.enable_tcpip, "Enable TCP/IP"
        )

    def connect_wireless(self):
        ip = self.var_ip.get().strip()
        if not ip:
            messagebox.showwarning("Error", "Please enter the Device IP address first.")
            return
        target = ip if ":" in ip else f"{ip}:5555"
        self.set_status(f"Connecting wirelessly to {target}...")

        def on_success():
            self.root.after(0, self._connect_wireless_success, target)
        def on_error(reason):
            self.root.after(0, self._connect_wireless_error, target, reason)

        self.adb.connect_wireless(target, on_success, on_error)

    def pair_wireless(self):
        ip = self.var_ip.get().strip()
        port = self.var_pair_port.get().strip()
        code = self.var_pair_code.get().strip()
        if not ip:
            messagebox.showwarning("Error", "Please enter the Device IP address first.")
            return
        if not port:
            messagebox.showwarning("Error", "Please enter the Pairing Port.")
            return
        if not code:
            messagebox.showwarning("Error", "Please enter the 6-digit Pairing Code.")
            return
        
        ip_port = f"{ip}:{port}"
        self.set_status(f"Pairing wirelessly with {ip_port}...")

        def on_success():
            self.root.after(0, self._pair_wireless_success, ip_port)
        def on_error(reason):
            self.root.after(0, self._pair_wireless_error, ip_port, reason)

        self.adb.pair_wireless(ip_port, code, on_success, on_error)
        
    def _pair_wireless_success(self, ip_port):
        self.set_status(f"Successfully paired with {ip_port}!")
        self.console_mgr.log("INFO", f"Successfully paired with {ip_port}.")
        
        success_msg = (
            f"Successfully paired with {ip_port}!\n\n"
            "Next Steps:\n"
            "1. Close the pairing dialog on your phone.\n"
            "2. Find the active connection 'IP address & Port' under Wireless debugging on your phone.\n"
            "3. Enter that port in the Connect Port field, and click Connect.\n\n"
            "⚠️ CRITICAL REMINDER:\n"
            "Please ensure that standard 'USB Debugging' remains ENABLED in your phone's Developer Options alongside 'Wireless Debugging'.\n"
            "This is required so that the fallback TCP/IP (port 5555) connection works seamlessly next time Wireless Debugging is turned off!"
        )
        messagebox.showinfo("Success", success_msg)
        self.clear_workflow_issue()
        
    def _pair_wireless_error(self, ip_port, reason):
        self.set_status(f"Pairing with {ip_port} failed.")
        self.console_mgr.log("ERROR", f"Wireless pairing with {ip_port} failed: {reason}")
        messagebox.showerror("Error", f"Failed to pair with {ip_port}.\nADB says: {reason or 'No response'}")

    def connect_wireless_direct(self):
        ip = self.var_ip.get().strip()
        port = self.var_connect_port.get().strip()
        if not ip:
            messagebox.showwarning("Error", "Please enter the Device IP address.")
            return
        if not port:
            messagebox.showwarning("Error", "Please enter the Connection Port.")
            return
        
        ip_port = f"{ip}:{port}"
        self.set_status(f"Connecting wirelessly to {ip_port}...")
        
        def on_success():
            self.root.after(0, self._connect_wireless_success, ip_port)
        def on_error(reason):
            self.root.after(0, self._connect_wireless_error, ip_port, reason)
            
        self.adb.connect_wireless(ip_port, on_success, on_error)

    def _connect_wireless_success(self, ip):
        display_target = ip if ":" in ip else f"{ip}:5555"
        
        # Try to transition dynamical port to port 5555 automatically
        if ":" in display_target and not display_target.endswith(":5555"):
            raw_ip = display_target.split(":")[0]
            self.set_status("Connected! Enabling stable TCP/IP port 5555...")
            
            def on_tcpip_success():
                self.console_mgr.log("INFO", f"TCP/IP enabled on port 5555 for {raw_ip}. Transitioning connection...")
                
                def on_stable_connect():
                    self.set_status(f"Successfully connected to stable port {raw_ip}:5555!")
                    self.var_connect_port.set("5555")
                    self.connection_summary_var.set(f"Wireless ADB linked to {raw_ip}:5555")
                    self.workflow_wireless_ready = True
                    self.clear_workflow_issue()
                    self.refresh_devices()
                    
                def on_stable_error(err):
                    self.console_mgr.log("WARN", f"Could not transition to port 5555: {err}. Remaining on dynamic port.")
                    self.connection_summary_var.set(f"Wireless ADB linked to {display_target}")
                    self.workflow_wireless_ready = True
                    self.clear_workflow_issue()
                    self.refresh_devices()
                    
                self.adb.connect_wireless(f"{raw_ip}:5555",
                    lambda: self.root.after(0, on_stable_connect),
                    lambda err: self.root.after(0, on_stable_error, err)
                )
                
            def on_tcpip_error():
                self.console_mgr.log("WARN", f"Could not enable TCP/IP on port 5555 for {raw_ip}. Remaining on dynamic port.")
                self.connection_summary_var.set(f"Wireless ADB linked to {display_target}")
                self.workflow_wireless_ready = True
                self.clear_workflow_issue()
                self.refresh_devices()
                
            self.adb.enable_tcpip(display_target,
                lambda: self.root.after(0, on_tcpip_success),
                lambda: self.root.after(0, on_tcpip_error)
            )
        else:
            self.connection_summary_var.set(f"Wireless ADB linked to {display_target}")
            self.set_status(f"Successfully connected to {display_target}")
            self.workflow_wireless_ready = True
            self.clear_workflow_issue()
            self.refresh_devices()

    def _connect_wireless_error(self, ip, reason):
        display_target = ip if ":" in ip else f"{ip}:5555"
        self.connection_summary_var.set(f"Wireless connection failed for {display_target}")
        self.set_status("Connection failed.")
        self.console_mgr.log("ERROR", f"Wireless connection to {display_target} failed.")
        self.workflow_wireless_ready = False
        self.set_workflow_issue(
            f"Wireless ADB could not connect to {display_target}.",
            "Check that the phone and PC are on the same Wi-Fi and that the connection port is correct.",
            self.connect_wireless, "Connect Wi-Fi"
        )
        messagebox.showerror("Error", f"Failed to connect.\nADB says: {reason or 'No response'}")

    def auto_detect_port(self):
        ip = self.var_ip.get().strip()
        if not ip:
            messagebox.showwarning("Error", "Please enter the Device IP address first so we can scan for it.")
            return
            
        self.set_status("Scanning local network for Wireless Debugging ports...")
        self.console_mgr.log("INFO", f"Scanning for dynamic wireless ports matching IP: {ip}...")
        
        def on_success(discovered):
            self.root.after(0, self._auto_detect_port_success, ip, discovered)
            
        def on_error(reason):
            self.root.after(0, self._auto_detect_port_error, reason)
            
        self.adb.discover_mdns_ports(on_success, on_error)

    def _auto_detect_port_success(self, target_ip, discovered):
        if target_ip in discovered:
            port = discovered[target_ip]
            self.var_connect_port.set(port)
            self.set_status(f"Auto-detected active port for {target_ip}: {port}!")
            self.console_mgr.log("INFO", f"Successfully auto-detected active port for {target_ip}: {port}.")
            messagebox.showinfo("Success", f"⚡ Auto-detected active port: {port}!\n\nIt has been automatically entered. Click Connect to start mirroring!")
        else:
            self.set_status("Auto-detect failed. Device not found in scan.")
            msg = (
                f"Could not find any active wireless debugging service for IP '{target_ip}' in the mDNS scan.\n\n"
                "To resolve this, please:\n"
                "1. Go to Developer options > Wireless debugging on your phone.\n"
                "2. Turn Wireless debugging OFF, then turn it back ON.\n"
                "3. Verify your phone is connected to the SAME Wi-Fi network as this PC.\n"
                "4. Wait a few seconds and try clicking Auto-detect again."
            )
            messagebox.showwarning("Device Not Found", msg)

    def _auto_detect_port_error(self, reason):
        self.set_status("Auto-detect scan failed.")
        self.console_mgr.log("ERROR", f"mDNS service scan failed: {reason}")
        msg = (
            "Failed to scan local network for wireless debugging services.\n\n"
            f"ADB reported:\n{reason}\n\n"
            "Please check that your Wi-Fi is active and that ADB is running properly. "
            "You can always enter the Connect Port manually from your phone's screen."
        )
        messagebox.showerror("Scan Failed", msg)

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
            if context == "scrcpy":
                self.root.after(0, lambda: self.set_status("Mirroring stopped."))
        else:
            self.append_console(summary, "ERROR")
            self.console_mgr.log_hint_for_message(summary)
            if context == "scrcpy":
                self.root.after(0, lambda: self.set_status(f"Mirroring exited with code {return_code}."))
        self.active_processes = [p for p in self.active_processes if p.poll() is None]


    def open_quick_settings(self):
        QuickSettingsDialog(self)

    # --- SCRCPY LAUNCH PROCESS ---
    def start_scrcpy(self):
        if not self.device_combo.get() or self.device_combo.get() == "No devices found":
            self.set_workflow_issue(
                "Mirroring cannot start until a device is available.",
                "Scan for a USB device first, or finish the wireless connection flow before launching scrcpy.",
                self.refresh_devices, "Scan Devices"
            )
            messagebox.showwarning("No Device", "Please select a device first.")
            return

        settings = {key: getattr(self, var_name).get() for key, (var_name, _, _) in config.CONFIG_FIELDS.items()}
        settings["device_serial"] = self.get_selected_device()
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
            self.set_workflow_issue(
                "scrcpy could not be launched from the current setup.",
                "Open the Console tab to review the exact error, then retry once the problem is fixed.",
                lambda: self.switch_tab("Terminal Console"), "Open Console"
            )
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
        if hasattr(self, "btn_update") and self.btn_update.winfo_exists():
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
                body {{ background-color: #0b0b0f; color: #ffffff; font-family: 'Segoe UI', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
                .card {{ background-color: #161622; padding: 40px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; width: 350px; border: 1px solid #232333; }}
                h1 {{ color: #ffffff; margin: 0 0 5px 0; font-size: 28px; letter-spacing: 1px; text-transform: uppercase; }}
                h2 {{ color: #8b8b9f; margin: 0 0 25px 0; font-size: 16px; font-weight: normal; }}
                .qr-box {{ background: white; padding: 15px; border-radius: 10px; display: inline-block; margin-bottom: 20px; }}
                img {{ display: block; width: 100%; height: auto; }}
                .label {{ font-size: 12px; color: #8b8b9f; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px; }}
                .upi-box {{ background: #0d0d14; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 16px; color: #8b5cf6; border: 1px solid #232333; word-break: break-all; user-select: all; }}
                .footer {{ color: #8b8b9f; font-size: 13px; margin-top: 25px; line-height: 1.5; }}
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

    def auto_save_device(self, d):
        is_wireless = (d.transport == "wireless" or ":" in d.serial)
        if is_wireless:
            ip = d.serial.split(':')[0]
            dev_type = "wireless"
        else:
            ip = ""
            dev_type = "usb"
            
        existing_dev = None
        hw_serial = getattr(d, "hardware_serial", "")
        for sd in getattr(self, "saved_devices", []):
            if sd.get("type") == dev_type:
                if hw_serial and sd.get("hardware_serial") == hw_serial:
                    existing_dev = sd
                    break
                elif dev_type == "wireless" and sd.get("ip") == ip:
                    existing_dev = sd
                    break
                elif dev_type == "usb" and sd.get("serial") == d.serial:
                    existing_dev = sd
                    break

        if existing_dev:
            existing_dev["brand"] = d.brand
            existing_dev["model"] = d.model
            existing_dev["display_name"] = d.display_name
            if hw_serial:
                existing_dev["hardware_serial"] = hw_serial
            if dev_type == "wireless":
                existing_dev["serial"] = d.serial
                existing_dev["ip"] = ip
        else:
            new_dev = {
                "serial": d.serial,
                "hardware_serial": hw_serial,
                "ip": ip,
                "type": dev_type,
                "brand": d.brand,
                "model": d.model,
                "nickname": "",
                "display_name": d.display_name
            }
            if not hasattr(self, "saved_devices"):
                self.saved_devices = []
            self.saved_devices.append(new_dev)
        
        config.save_config(self, self.config_file)
        self.refresh_saved_devices_ui()

    def edit_saved_device(self, dev):
        def on_save(new_nick, new_ip):
            dev["nickname"] = new_nick
            if new_ip is not None:
                dev["ip"] = new_ip
                if ":" in dev.get("serial", ""):
                    port = dev["serial"].split(":")[1]
                    dev["serial"] = f"{new_ip}:{port}"
                else:
                    dev["serial"] = f"{new_ip}:5555"
            config.save_config(self, self.config_file)
            self.refresh_saved_devices_ui()
            self.console_mgr.log("INFO", f"Saved device updated: {dev.get('display_name')}")
            
        dialog = SavedDeviceDialog(self, dev, on_save)

    def remove_saved_device(self, dev):
        name = dev.get("nickname") or dev.get("display_name")
        confirm = messagebox.askyesno("Remove Saved Device", f"Are you sure you want to forget the device '{name}'?")
        if confirm:
            if dev in self.saved_devices:
                self.saved_devices.remove(dev)
            config.save_config(self, self.config_file)
            self.refresh_saved_devices_ui()
            self.console_mgr.log("INFO", f"Removed device from saved list: {name}")

    def connect_saved_device(self, dev):
        dev_type = dev.get("type", "usb")
        if dev_type == "usb":
            serial = dev.get("serial")
            name = dev.get("nickname") or dev.get("display_name")
            
            def check_presence(devices):
                self._refresh_devices_success(devices)
                if serial in self.device_serial_to_label:
                    label = self.device_serial_to_label[serial]
                    self.device_combo.set(label)
                    self.refresh_dashboard_state()
                    self.set_status(f"Selected USB device: {name}")
                else:
                    messagebox.showerror("Error", f"USB Device '{name}' is not physically connected.")
                    self.console_mgr.log("WARN", f"Saved USB device {serial} not found in live scan.")
                    
            self.adb.refresh_devices(
                lambda devs: self.root.after(0, check_presence, devs),
                lambda err: self.root.after(0, lambda: messagebox.showerror("Scan Error", "Failed to scan devices."))
            )
        else:
            ip = dev.get("ip")
            port = dev.get("serial", "").split(":")[1] if ":" in dev.get("serial", "") else "5555"
            ip_port = f"{ip}:{port}"
            self.set_status(f"Connecting to saved device {ip_port}...")
            
            def on_success():
                self.root.after(0, self._connect_wireless_success, ip_port)
            def on_error(reason):
                self.root.after(0, self._connect_wireless_error, ip_port, reason)
                
            self.adb.connect_wireless(ip_port, on_success, on_error)

    def update_card_text_wrap(self, card_width, title_widget, subtitle_widget=None):
        pad = 40
        if title_widget and title_widget.winfo_exists():
            try: title_widget.configure(wraplength=max(100, card_width - pad))
            except Exception: pass
        if subtitle_widget and subtitle_widget.winfo_exists():
            try: subtitle_widget.configure(wraplength=max(100, card_width - pad))
            except Exception: pass
