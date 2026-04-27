import customtkinter as ctk
from ui import ScrcpyGUI

def run_app():
    # Ensure High DPI awareness for sharper UI
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    root = ctk.CTk()
    app = ScrcpyGUI(root)
    root.mainloop()

if __name__ == "__main__":
    run_app()
