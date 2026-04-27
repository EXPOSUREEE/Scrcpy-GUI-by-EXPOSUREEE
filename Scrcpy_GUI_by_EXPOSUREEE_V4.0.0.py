import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
import subprocess
import threading
import os
import sys
import re
import urllib.request
import urllib.parse
import webbrowser
import tempfile
import json
from datetime import datetime
import pywinstyles

# --- CONFIGURATION ---
PROGRAM_TITLE = "Scrcpy GUI PRO (Glass Edition)"
CURRENT_VERSION = "4.0.0"
UPDATE_URL = "https://exposureee.in/wp-content/uploads/2024/08/Scrcpy_GUI_by_EXPOSUREEE-Version.txt"
DOWNLOAD_URL = "https://exposureee.in/scrcpy-gui-by-exposureee/"
TUTORIAL_URL = "https://www.youtube.com/watch?v=pWKY_dntX5c"
UPI_ID = "exposureee@upi"
PAYEE_NAME = "Abhishek Mishra"

# --- COLORS ---
ACCENT_RED = "#ff4757"     
HOVER_RED = "#ff6b81"      
UPDATE_GREEN = "#2ecc71"

class ScrcpyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{PROGRAM_TITLE} v{CURRENT_VERSION}")
        self.root.geometry("900x750")
        self.root.minsize(800, 600)
        
        # Apply Glassmorphism / Acrylic Effect
        try:
            pywinstyles.apply_style(self.root, "acrylic")
        except Exception as e:
            print(f"Glass effect failed: {e}")
            
        # --- PATH SETUP ---
        if getattr(sys, 'frozen', False):
            self.script_dir = os.path.dirname(sys.executable)
        else:
            self.script_dir = os.path.dirname(os.path.abspath(__file__))

        self.scrcpy_exe = os.path.join(self.script_dir, "scrcpy.exe")
        self.adb_exe = os.path.join(self.script_dir, "adb.exe")
        self.config_file = os.path.join(self.script_dir, "config.json")
        
        # --- ICON SETUP ---
        icon_path = os.path.join(self.script_dir, "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass
        
        if not os.path.exists(self.scrcpy_exe):
            self.scrcpy_exe = "scrcpy"
        if not os.path.exists(self.adb_exe):
            self.adb_exe = "adb"

        # --- VARIABLES ---
        self.init_variables()
        self.load_config()
        
        self.create_widgets()
        self.refresh_devices()
        
        # Background Update Check
        threading.Thread(target=self.check_for_updates, daemon=True).start()

    def init_variables(self):
        # Connection
        self.var_ip = ctk.StringVar()
        
        # Video & Audio
        self.var_source = ctk.StringVar(value="screen")
        self.var_bitrate = ctk.StringVar(value="8")
        self.var_max_fps = ctk.StringVar(value="0") 
        self.var_max_size = ctk.StringVar(value="0") 
        self.var_video_codec = ctk.StringVar(value="h264")
        self.var_audio_codec = ctk.StringVar(value="opus")
        self.cam_ar_combo_val = ctk.StringVar(value="Full Sensor (Default)")
        self.renderer_combo_val = ctk.StringVar(value="software")
        self.orientation_combo_val = ctk.StringVar(value="Auto (Rotate with Phone)")
        
        # Advanced & Window
        self.var_always_on_top = ctk.BooleanVar(value=False)
        self.var_stay_awake = ctk.BooleanVar(value=True)
        self.var_screen_off = ctk.BooleanVar(value=False)
        self.var_show_touches = ctk.BooleanVar(value=False)
        self.var_no_audio = ctk.BooleanVar(value=False)
        self.var_fullscreen = ctk.BooleanVar(value=False)
        self.var_borderless = ctk.BooleanVar(value=False)
        self.var_no_control = ctk.BooleanVar(value=False)
        self.var_record = ctk.BooleanVar(value=False)
        self.var_debug_mode = ctk.BooleanVar(value=False)
        
    def save_config(self):
        config = {
            "ip": self.var_ip.get(),
            "source": self.var_source.get(),
            "bitrate": self.var_bitrate.get(),
            "max_fps": self.var_max_fps.get(),
            "max_size": self.var_max_size.get(),
            "video_codec": self.var_video_codec.get(),
            "audio_codec": self.var_audio_codec.get(),
            "cam_ar": self.cam_ar_combo_val.get(),
            "renderer": self.renderer_combo_val.get(),
            "orientation": self.orientation_combo_val.get(),
            "always_on_top": self.var_always_on_top.get(),
            "stay_awake": self.var_stay_awake.get(),
            "screen_off": self.var_screen_off.get(),
            "show_touches": self.var_show_touches.get(),
            "no_audio": self.var_no_audio.get(),
            "fullscreen": self.var_fullscreen.get(),
            "borderless": self.var_borderless.get(),
            "no_control": self.var_no_control.get(),
            "record": self.var_record.get(),
            "debug_mode": self.var_debug_mode.get()
        }
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Error saving config: {e}")

    def load_config(self):
        if not os.path.exists(self.config_file):
            return
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            self.var_ip.set(config.get("ip", ""))
            self.var_source.set(config.get("source", "screen"))
            self.var_bitrate.set(config.get("bitrate", "8"))
            self.var_max_fps.set(config.get("max_fps", "0"))
            self.var_max_size.set(config.get("max_size", "0"))
            self.var_video_codec.set(config.get("video_codec", "h264"))
            self.var_audio_codec.set(config.get("audio_codec", "opus"))
            self.cam_ar_combo_val.set(config.get("cam_ar", "Full Sensor (Default)"))
            self.renderer_combo_val.set(config.get("renderer", "software"))
            self.orientation_combo_val.set(config.get("orientation", "Auto (Rotate with Phone)"))
            self.var_always_on_top.set(config.get("always_on_top", False))
            self.var_stay_awake.set(config.get("stay_awake", True))
            self.var_screen_off.set(config.get("screen_off", False))
            self.var_show_touches.set(config.get("show_touches", False))
            self.var_no_audio.set(config.get("no_audio", False))
            self.var_fullscreen.set(config.get("fullscreen", False))
            self.var_borderless.set(config.get("borderless", False))
            self.var_no_control.set(config.get("no_control", False))
            self.var_record.set(config.get("record", False))
            self.var_debug_mode.set(config.get("debug_mode", False))
        except Exception as e:
            print(f"Error loading config: {e}")


    def create_widgets(self):
        # MAIN WRAPPER
        wrapper = ctk.CTkFrame(self.root, fg_color="transparent")
        wrapper.pack(fill="both", expand=True, padx=20, pady=20)

        # --- TOP HEADER SECTION ---
        header_frame = ctk.CTkFrame(wrapper, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(header_frame, text=PROGRAM_TITLE, font=ctk.CTkFont(size=24, weight="bold"), text_color=ACCENT_RED).pack(anchor="center")
        ctk.CTkLabel(header_frame, text=f"by EXPOSUREEE | v{CURRENT_VERSION}", font=ctk.CTkFont(size=12), text_color="gray").pack(anchor="center")
        
        lbl_tut = ctk.CTkLabel(header_frame, text="▶ Watch Tutorial: How to use this software", font=ctk.CTkFont(size=12, underline=True), text_color="#3498db", cursor="hand2")
        lbl_tut.pack(pady=(5, 5))
        lbl_tut.bind("<Button-1>", lambda e: self.open_tutorial())

        self.update_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        self.update_frame.pack(fill="x", pady=(5, 0))
        self.btn_update = ctk.CTkButton(self.update_frame, text="Update Available!", fg_color=UPDATE_GREEN, hover_color="#27ae60", command=self.open_download)

        # --- NOTEBOOK (TABS) ---
        self.tabview = ctk.CTkTabview(wrapper, segmented_button_selected_color=ACCENT_RED, segmented_button_selected_hover_color=HOVER_RED)
        self.tabview.pack(fill="both", expand=True, pady=(0, 15))
        
        self.tabview.add("🔌 Connection")
        self.tabview.add("🎥 Video & Audio")
        self.tabview.add("⚙️ Advanced Options")

        self.build_connection_tab(self.tabview.tab("🔌 Connection"))
        self.build_video_tab(self.tabview.tab("🎥 Video & Audio"))
        self.build_advanced_tab(self.tabview.tab("⚙️ Advanced Options"))

        # --- BOTTOM SECTION ---
        # Start Button
        self.btn_start = ctk.CTkButton(wrapper, text="START MIRRORING", fg_color=ACCENT_RED, hover_color=HOVER_RED, font=ctk.CTkFont(size=16, weight="bold"), height=50, command=self.start_scrcpy)
        self.btn_start.pack(fill="x", pady=(0, 10))

        # Footer
        footer_frame = ctk.CTkFrame(self.root, fg_color="#111111", corner_radius=0)
        footer_frame.pack(side="bottom", fill="x")

        self.status_var = ctk.StringVar(value="Ready.")
        status_lbl = ctk.CTkLabel(footer_frame, textvariable=self.status_var, text_color="gray", font=ctk.CTkFont(size=11))
        status_lbl.pack(fill="x", side="top", pady=2)
        
        btn_donate = ctk.CTkButton(footer_frame, text="❤ Support / Donate via UPI", fg_color="transparent", hover_color="#333333", text_color=ACCENT_RED, command=self.donate_upi)
        btn_donate.pack(fill="x", side="bottom", pady=2)

    def build_connection_tab(self, parent):
        # Device Selection
        dev_frame = ctk.CTkFrame(parent)
        dev_frame.pack(fill="x", pady=(10, 20), padx=10)
        ctk.CTkLabel(dev_frame, text="USB Connection", font=ctk.CTkFont(weight="bold", size=14), text_color=ACCENT_RED).pack(anchor="w", padx=15, pady=(10,0))
        
        inner_dev = ctk.CTkFrame(dev_frame, fg_color="transparent")
        inner_dev.pack(fill="x", padx=15, pady=10)
        self.device_combo = ctk.CTkComboBox(inner_dev, values=[])
        self.device_combo.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(inner_dev, text="↻ SCAN DEVICES", width=120, command=self.refresh_devices, fg_color="#555", hover_color="#444").pack(side="right")

        # Wireless Mode
        wifi_frame = ctk.CTkFrame(parent)
        wifi_frame.pack(fill="x", padx=10)
        ctk.CTkLabel(wifi_frame, text="Wireless Mode", font=ctk.CTkFont(weight="bold", size=14), text_color=ACCENT_RED).pack(anchor="w", padx=15, pady=(10,0))
        
        r_ip = ctk.CTkFrame(wifi_frame, fg_color="transparent") 
        r_ip.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(r_ip, text="Device IP Address:", width=120, anchor="w").pack(side="left")
        ctk.CTkEntry(r_ip, textvariable=self.var_ip).pack(side="left", fill="x", expand=True, padx=(10, 10))
        ctk.CTkButton(r_ip, text="AUTO GET IP", width=120, command=self.get_device_ip, fg_color="#555", hover_color="#444").pack(side="right")

        r_wbtn = ctk.CTkFrame(wifi_frame, fg_color="transparent")
        r_wbtn.pack(fill="x", padx=15, pady=(0, 15))
        ctk.CTkButton(r_wbtn, text="Step 1: Enable TCP/IP (USB Req)", command=self.enable_tcpip, fg_color="#555", hover_color="#444").pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(r_wbtn, text="Step 2: Connect Wirelessly", command=self.connect_wireless, fg_color="#555", hover_color="#444").pack(side="left", fill="x", expand=True, padx=(5, 0))

    def build_video_tab(self, parent):
        # Source Selection
        src_frame = ctk.CTkFrame(parent)
        src_frame.pack(fill="x", pady=(10, 15), padx=10)
        ctk.CTkLabel(src_frame, text="Source", font=ctk.CTkFont(weight="bold", size=14), text_color=ACCENT_RED).pack(anchor="w", padx=15, pady=(10,5))
        
        inner_src = ctk.CTkFrame(src_frame, fg_color="transparent")
        inner_src.pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkRadioButton(inner_src, text="Screen", variable=self.var_source, value="screen", fg_color=ACCENT_RED, hover_color=HOVER_RED).pack(side="left", padx=(0, 15))
        ctk.CTkRadioButton(inner_src, text="Back Camera", variable=self.var_source, value="camera_back", fg_color=ACCENT_RED, hover_color=HOVER_RED).pack(side="left", padx=15)
        ctk.CTkRadioButton(inner_src, text="Front Camera", variable=self.var_source, value="camera_front", fg_color=ACCENT_RED, hover_color=HOVER_RED).pack(side="left", padx=15)
        ctk.CTkRadioButton(inner_src, text="Only Microphone", variable=self.var_source, value="mic_only", fg_color=ACCENT_RED, hover_color=HOVER_RED).pack(side="left", padx=15)

        # Quality Settings
        qual_frame = ctk.CTkFrame(parent)
        qual_frame.pack(fill="x", pady=(0, 15), padx=10)
        ctk.CTkLabel(qual_frame, text="Quality Settings", font=ctk.CTkFont(weight="bold", size=14), text_color=ACCENT_RED).pack(anchor="w", padx=15, pady=(10,5))
        
        r1 = ctk.CTkFrame(qual_frame, fg_color="transparent")
        r1.pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkLabel(r1, text="Video Bitrate (Mbps):", width=140, anchor="w").pack(side="left")
        ctk.CTkEntry(r1, textvariable=self.var_bitrate, width=80).pack(side="left")
        
        ctk.CTkLabel(r1, text="Max FPS (0=Unlimited):", width=150, anchor="w").pack(side="left", padx=(30,0))
        ctk.CTkEntry(r1, textvariable=self.var_max_fps, width=80).pack(side="left")

        r2 = ctk.CTkFrame(qual_frame, fg_color="transparent")
        r2.pack(fill="x", padx=15, pady=(0, 15))
        ctk.CTkLabel(r2, text="Max Size (0=Original):", width=140, anchor="w").pack(side="left")
        ctk.CTkEntry(r2, textvariable=self.var_max_size, width=80).pack(side="left")
        ctk.CTkLabel(r2, text="px  (e.g., 1080, 720)", text_color="gray").pack(side="left", padx=(10,0))

        # Codec Settings
        codec_frame = ctk.CTkFrame(parent)
        codec_frame.pack(fill="x", padx=10)
        ctk.CTkLabel(codec_frame, text="Codecs & Render", font=ctk.CTkFont(weight="bold", size=14), text_color=ACCENT_RED).pack(anchor="w", padx=15, pady=(10,5))

        r3 = ctk.CTkFrame(codec_frame, fg_color="transparent")
        r3.pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkLabel(r3, text="Video Codec:", width=100, anchor="w").pack(side="left")
        ctk.CTkComboBox(r3, variable=self.var_video_codec, values=["h264", "h265", "av1"], width=100).pack(side="left")
        
        ctk.CTkLabel(r3, text="Audio Codec:", width=100, anchor="w").pack(side="left", padx=(30,0))
        ctk.CTkComboBox(r3, variable=self.var_audio_codec, values=["opus", "aac", "raw"], width=100).pack(side="left")

        r4 = ctk.CTkFrame(codec_frame, fg_color="transparent")
        r4.pack(fill="x", padx=15, pady=(0, 15))
        ctk.CTkLabel(r4, text="Renderer:", width=100, anchor="w").pack(side="left")
        ctk.CTkComboBox(r4, variable=self.renderer_combo_val, values=["auto", "opengl", "direct3d", "software"], width=100).pack(side="left")
        
        ctk.CTkLabel(r4, text="Cam Ratio:", width=100, anchor="w").pack(side="left", padx=(30,0))
        ctk.CTkComboBox(r4, variable=self.cam_ar_combo_val, values=["Full Sensor (Default)", "16:9", "4:3", "1:1"], width=160).pack(side="left")


    def build_advanced_tab(self, parent):
        # Window & Display
        win_frame = ctk.CTkFrame(parent)
        win_frame.pack(fill="x", pady=(10, 15), padx=10)
        ctk.CTkLabel(win_frame, text="Window & Display", font=ctk.CTkFont(weight="bold", size=14), text_color=ACCENT_RED).pack(anchor="w", padx=15, pady=(10,5))
        
        inner_win = ctk.CTkFrame(win_frame, fg_color="transparent")
        inner_win.pack(fill="x", padx=15, pady=(0, 10))

        checks = [
            ("Always on Top", self.var_always_on_top),
            ("Borderless Window", self.var_borderless),
            ("Fullscreen", self.var_fullscreen),
            ("Stay Awake", self.var_stay_awake),
            ("Turn Screen Off", self.var_screen_off),
            ("Show Touches", self.var_show_touches),
            ("Disable Control (View Only)", self.var_no_control),
            ("Disable Audio", self.var_no_audio),
        ]
        
        for i, (text, var) in enumerate(checks):
            ctk.CTkCheckBox(inner_win, text=text, variable=var, fg_color=ACCENT_RED, hover_color=HOVER_RED).grid(row=i//2, column=i%2, sticky="w", padx=10, pady=8)
            
        r_orient = ctk.CTkFrame(win_frame, fg_color="transparent")
        r_orient.pack(fill="x", padx=15, pady=(5, 15))
        ctk.CTkLabel(r_orient, text="Orientation Lock:", width=120, anchor="w").pack(side="left", padx=(0, 10))
        ctk.CTkComboBox(r_orient, variable=self.orientation_combo_val, values=[
            "Auto (Rotate with Phone)", "Portrait (@0)", "Landscape (@90)", 
            "Portrait Reversed (@180)", "Landscape Reversed (@270)"
        ], width=200).pack(side="left")

        # Extras
        extra_frame = ctk.CTkFrame(parent)
        extra_frame.pack(fill="x", padx=10)
        ctk.CTkLabel(extra_frame, text="Extras", font=ctk.CTkFont(weight="bold", size=14), text_color=ACCENT_RED).pack(anchor="w", padx=15, pady=(10,5))
        
        ctk.CTkCheckBox(extra_frame, text="Record Output to MP4", variable=self.var_record, fg_color=ACCENT_RED, hover_color=HOVER_RED).pack(anchor="w", padx=25, pady=8)
        ctk.CTkCheckBox(extra_frame, text="Enable Debug Console (Show CMD Window)", variable=self.var_debug_mode, fg_color=ACCENT_RED, hover_color=HOVER_RED).pack(anchor="w", padx=25, pady=(8, 15))

    def open_tutorial(self):
        webbrowser.open(TUTORIAL_URL)

    def donate_upi(self):
        try:
            upi_payload = f"upi://pay?pa={UPI_ID}&pn={urllib.parse.quote(PAYEE_NAME)}&cu=INR"
            encoded_data = urllib.parse.quote(upi_payload)
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&bgcolor=ffffff&data={encoded_data}"
            
            html_content = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Donate to EXPOSUREEE</title>
                <meta charset="UTF-8">
                <style>
                    body {{ background-color: #1e1e1e; color: #ffffff; font-family: 'Segoe UI', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
                    .card {{ background-color: #2d2d30; padding: 40px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; width: 350px; border-top: 5px solid #ff4757; }}
                    h1 {{ color: #ff4757; margin: 0 0 5px 0; font-size: 28px; letter-spacing: 1px; text-transform: uppercase; }}
                    h2 {{ color: #a0a0a0; margin: 0 0 25px 0; font-size: 16px; font-weight: normal; }}
                    .qr-box {{ background: white; padding: 15px; border-radius: 10px; display: inline-block; margin-bottom: 20px; }}
                    img {{ display: block; width: 100%; height: auto; }}
                    .label {{ font-size: 12px; color: #888; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px; }}
                    .upi-box {{ background: #3e3e42; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 16px; color: #fff; border: 1px solid #444; word-break: break-all; user-select: all; }}
                    .footer {{ color: #666; font-size: 13px; margin-top: 25px; line-height: 1.5; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>EXPOSUREEE</h1>
                    <h2>{PAYEE_NAME}</h2>
                    <div class="qr-box">
                        <img src="{qr_url}" alt="UPI QR Code" width="250" height="250">
                    </div>
                    <div class="label">UPI ID</div>
                    <div class="upi-box">{UPI_ID}</div>
                    <div class="footer">
                        Scan with GPay, PhonePe, or Paytm.<br>
                        Thank you for your support! ❤
                    </div>
                </div>
            </body>
            </html>
            '''
            
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html', encoding='utf-8') as f:
                f.write(html_content)
                temp_path = f.name
            
            webbrowser.open('file://' + temp_path)
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not generate donation page: {e}")

    # --- STANDARD METHODS ---
    def run_adb_cmd(self, args):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        try:
            result = subprocess.run([self.adb_exe] + args, capture_output=True, text=True, startupinfo=startupinfo, cwd=self.script_dir)
            return result.stdout.strip()
        except Exception as e:
            return None

    def refresh_devices(self):
        self.status_var.set("Scanning...")
        self.root.update_idletasks()
        output = self.run_adb_cmd(["devices"])
        if output:
            lines = output.split('\n')[1:]
            devices = [line.split()[0] for line in lines if "device" in line]
            if devices:
                self.device_combo.configure(values=devices)
                self.device_combo.set(devices[0])
                self.status_var.set(f"Connected: {devices[0]}")
            else:
                self.device_combo.configure(values=["No devices found"])
                self.device_combo.set("No devices found")
                self.status_var.set("No devices found.")
        else:
            self.status_var.set("ADB Error.")

    def get_device_ip(self):
        serial = self.device_combo.get()
        if not serial or serial == "No devices found":
            messagebox.showwarning("Error", "Select a device connected via USB first.")
            return
        self.status_var.set("Fetching IP...")
        output = self.run_adb_cmd(["-s", serial, "shell", "ip", "-f", "inet", "addr", "show", "wlan0"])
        if output:
            match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", output)
            if match:
                ip = match.group(1)
                self.var_ip.set(ip)
                self.status_var.set(f"Found IP: {ip}")
                return
        self.status_var.set("Could not find IP (Is Wi-Fi on?)")
        messagebox.showinfo("Info", "Could not automatically find IP.\nPlease check if Wi-Fi is connected on the phone.")

    def enable_tcpip(self):
        serial = self.device_combo.get()
        if not serial or serial == "No devices found":
            messagebox.showwarning("Error", "Select a device connected via USB first.")
            return
        self.status_var.set("Enabling Wi-Fi Mode...")
        self.run_adb_cmd(["-s", serial, "tcpip", "5555"])
        messagebox.showinfo("Success", "Wi-Fi mode enabled.\n\nNow you can unplug USB and click 'Connect'.")
        self.status_var.set("Wi-Fi Mode Enabled on Port 5555.")

    def connect_wireless(self):
        ip = self.var_ip.get().strip()
        if not ip:
            messagebox.showwarning("Error", "Please enter the Device IP address.")
            return
        self.status_var.set(f"Connecting to {ip}...")
        output = self.run_adb_cmd(["connect", f"{ip}:5555"])
        if output and "connected" in output:
            self.status_var.set(f"Successfully connected to {ip}")
            self.refresh_devices()
        else:
            self.status_var.set("Connection failed.")
            messagebox.showerror("Error", f"Failed to connect.\nADB says: {output}")

    def start_scrcpy(self):
        self.save_config() 
        
        if not self.device_combo.get() or self.device_combo.get() == "No devices found":
            messagebox.showwarning("No Device", "Please select a device first.")
            return
        
        cmd = [self.scrcpy_exe, "-s", self.device_combo.get()]
        
        source = self.var_source.get()
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
            
            cam_ar = self.cam_ar_combo_val.get()
            if cam_ar != "Full Sensor (Default)":
                cmd.append(f"--camera-ar={cam_ar}")
        
        # --- VIDEO & AUDIO SETTINGS ---
        if not is_mic_only: 
            bitrate = self.var_bitrate.get().strip()
            if bitrate: cmd.extend(["--video-bit-rate", f"{bitrate}M"])
            
            max_fps = self.var_max_fps.get().strip()
            if max_fps and max_fps != "0": cmd.extend(["--max-fps", max_fps])
            
            max_size = self.var_max_size.get().strip()
            if max_size and max_size != "0": cmd.extend(["--max-size", max_size])
            
            vid_codec = self.var_video_codec.get()
            if vid_codec != "h264": cmd.extend(["--video-codec", vid_codec])
            
        if not is_camera and not self.var_no_audio.get():
            aud_codec = self.var_audio_codec.get()
            if aud_codec != "opus": cmd.extend(["--audio-codec", aud_codec])
            
        # --- RECORDING ---
        if self.var_record.get():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.mp4"
            cmd.extend(["--record", filename])
            self.status_var.set(f"Recording to {filename}...")

        # --- RENDERER & WINDOW ---
        renderer = self.renderer_combo_val.get()
        if renderer != "auto":
            cmd.extend(["--render-driver", renderer])
            
        orient = self.orientation_combo_val.get()
        if "Portrait (@0)" in orient: cmd.extend(["--capture-orientation=@0"])
        elif "Landscape (@90)" in orient: cmd.extend(["--capture-orientation=@90"])
        elif "Portrait Reversed (@180)" in orient: cmd.extend(["--capture-orientation=@180"])
        elif "Landscape Reversed (@270)" in orient: cmd.extend(["--capture-orientation=@270"])
        
        if self.var_always_on_top.get(): cmd.append("--always-on-top")
        if self.var_borderless.get(): cmd.append("--window-borderless")
        if self.var_fullscreen.get() and not is_mic_only: cmd.append("--fullscreen")
        
        # --- DEVICE BEHAVIOR ---
        if not is_camera and not is_mic_only:
            if self.var_stay_awake.get(): cmd.append("--stay-awake")
            if self.var_screen_off.get(): cmd.append("--turn-screen-off")
            if self.var_show_touches.get(): cmd.append("--show-touches")
            if self.var_no_control.get(): cmd.append("--no-control")
        
        if not is_camera and not is_mic_only and self.var_no_audio.get():
            cmd.append("--no-audio")

        if not self.var_record.get():
            self.status_var.set(f"Running (Renderer: {renderer})...")
        
        # --- EXECUTE ---
        try:
            if self.var_debug_mode.get():
                subprocess.Popen(cmd, cwd=self.script_dir)
            else:
                CREATE_NO_WINDOW = 0x08000000 
                subprocess.Popen(
                    cmd, 
                    cwd=self.script_dir, 
                    creationflags=CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
        except Exception as e:
            messagebox.showerror("Execution Error", str(e))

    def check_for_updates(self):
        try:
            with urllib.request.urlopen(UPDATE_URL) as response:
                remote_version_str = response.read().decode('utf-8').strip()
            try:
                update_available = float(remote_version_str) > float(CURRENT_VERSION)
            except ValueError:
                update_available = remote_version_str != CURRENT_VERSION
            if update_available:
                self.root.after(0, lambda: self.reveal_update_button(remote_version_str))
        except Exception as e:
            print(f"Update Check Failed: {e}")

    def reveal_update_button(self, new_version):
        self.btn_update.configure(text=f"⬇ UPDATE AVAILABLE: v{new_version}")
        self.btn_update.pack(fill="x", ipady=8)

    def open_download(self):
        webbrowser.open(DOWNLOAD_URL)

if __name__ == "__main__":
    # Ensure High DPI awareness for sharper UI
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    
    root = ctk.CTk()
    app = ScrcpyGUI(root)
    root.mainloop()