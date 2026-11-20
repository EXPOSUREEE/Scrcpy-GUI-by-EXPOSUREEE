"""Locate read-only bundle assets separately from tools and writable user files."""
import os
from pathlib import Path
import shutil
import sys

RESOURCES = Path(__file__).resolve().parent
APP_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else RESOURCES
VERSION = "4.0.1"


def executable(name):
    for directory in (APP_DIR / "runtime", APP_DIR):
        candidate = directory / (name + ".exe")
        if candidate.is_file():
            return str(candidate)
    return shutil.which(name) or name


def child_environment(adb_exe, scrcpy_exe):
    env = os.environ.copy()
    paths = [str(Path(exe).parent) for exe in (adb_exe, scrcpy_exe) if Path(exe).is_absolute()]
    env["PATH"] = os.pathsep.join([*dict.fromkeys(paths), env.get("PATH", "")])
    env["ADB"] = adb_exe
    return env
