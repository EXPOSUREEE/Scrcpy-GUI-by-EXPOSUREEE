"""Locate read-only bundle assets separately from tools and writable user files."""
import os
from functools import lru_cache
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryFile

RESOURCES = Path(__file__).resolve().parent
APP_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else RESOURCES
VERSION = "4.0.6"


def has_portable_marker():
    """Check for the portable distribution marker next to the application."""
    return (APP_DIR / "portable.mode").is_file()


@lru_cache
def _writable_portable_profile(app_dir):
    profile = app_dir / "portable_data"
    try:
        with TemporaryFile(dir=app_dir):
            profile.mkdir(exist_ok=True)
        with TemporaryFile(dir=profile):
            pass
    except OSError:
        return None
    return profile


def portable_profile_dir():
    """Return the writable portable profile when the marker is present."""
    return _writable_portable_profile(APP_DIR) if has_portable_marker() else None


def get_profile_dir():
    """Resolve the application profile, including the installed default."""
    portable = portable_profile_dir()
    if portable is not None:
        return portable
    override = os.environ.get("SCRCPY_DECK_PROFILE_DIR")
    if override:
        return Path(override)
    from PySide6.QtCore import QStandardPaths
    return Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))


def get_writable_runtime():
    """Return a directory suitable for storing updated runtime binaries."""
    portable = portable_profile_dir()
    if portable is not None:
        user_runtime = portable / "runtime"
        user_runtime.mkdir(parents=True, exist_ok=True)
        return user_runtime

    profile_override = os.environ.get("SCRCPY_DECK_PROFILE_DIR")
    if profile_override:
        user_runtime = Path(profile_override) / "runtime"
        user_runtime.mkdir(parents=True, exist_ok=True)
        return user_runtime

    app_runtime = APP_DIR / "runtime"
    try:
        app_runtime.mkdir(parents=True, exist_ok=True)
        test_file = app_runtime / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        return app_runtime
    except OSError:
        pass

    user_data = Path(os.environ.get("LOCALAPPDATA", "")) / "ScrcpyDeck"
    user_runtime = user_data / "runtime"
    user_runtime.mkdir(parents=True, exist_ok=True)
    return user_runtime


def executable(name):
    from runtime_manager import get_active_runtime_dir

    active_dir = get_active_runtime_dir()
    if active_dir:
        for fname in (name + ".exe", name):
            candidate = active_dir / fname
            if candidate.is_file():
                return str(candidate)

    for directory in (get_writable_runtime(), APP_DIR / "runtime", RESOURCES / "runtime", APP_DIR):
        for fname in (name + ".exe", name):
            candidate = directory / fname
            if candidate.is_file():
                return str(candidate)
    return shutil.which(name) or name


def child_environment(adb_exe, scrcpy_exe):
    env = os.environ.copy()
    paths = [str(Path(exe).parent) for exe in (adb_exe, scrcpy_exe) if Path(exe).is_absolute()]
    env["PATH"] = os.pathsep.join([*dict.fromkeys(paths), env.get("PATH", "")])
    env["ADB"] = adb_exe
    return env
