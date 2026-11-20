"""Locate read-only bundle assets separately from tools and writable user files."""
import os
from pathlib import Path
import shutil
import sys

RESOURCES = Path(__file__).resolve().parent
APP_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else RESOURCES
VERSION = "4.0.1"


def get_writable_runtime():
    """Return a directory suitable for storing updated runtime binaries."""
    app_runtime = APP_DIR / "runtime"
    try:
        app_runtime.mkdir(parents=True, exist_ok=True)
        test_file = app_runtime / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        return app_runtime
    except OSError:
        pass

    user_data = Path(os.environ.get("SCRCPY_DECK_PROFILE_DIR") or
                     Path(os.environ.get("LOCALAPPDATA", "")) / "ScrcpyDeck")
    user_runtime = user_data / "runtime"
    user_runtime.mkdir(parents=True, exist_ok=True)
    return user_runtime


def executable(name):
    for directory in (get_writable_runtime(), APP_DIR / "runtime", APP_DIR):
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
