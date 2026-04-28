import subprocess
import os

print("Installing pyinstaller...")
subprocess.run(["python", "-m", "pip", "install", "pyinstaller"], check=True)

print("Building with PyInstaller...")
cmd = [
    "python", "-m", "PyInstaller",
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--name", "Scrcpy_GUI_Pro",
    "--collect-all", "customtkinter",
    "main.py"
]
subprocess.run(cmd, check=True)
print("Build complete! Executable is at dist/Scrcpy_GUI_Pro.exe")
