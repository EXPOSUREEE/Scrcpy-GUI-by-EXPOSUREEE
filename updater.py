"""Software update discovery, download, and execution for Scrcpy Deck."""
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import uuid

from release_catalog import (
    DECK_REPO,
    SCRCPY_REPO,
    ReleaseEntry,
    get_catalog,
    parse_semver,
)

GITHUB_REPO = DECK_REPO
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases"


def portable_release_page():
    """Portable application updates are downloaded from the release page."""
    from assets import has_portable_marker
    if has_portable_marker():
        return f"https://github.com/{GITHUB_REPO}/releases/latest"
    return None
VERSION_PREFS_FILE = "version_preferences.json"


def parse_version(text):
    """Extract a version tuple (major, minor, patch) from text.

    Supports formats like '4.0.0', 'v4.0.1', '3.1', 'v3.1', 'ScrcpyDeck 4.0.2', etc.
    Returns (major, minor, patch) as ints, or None if no valid version is found.
    """
    return parse_semver(text)


def format_version(version_tuple):
    """Format a version tuple as 'major.minor.patch'."""
    return f"{version_tuple[0]}.{version_tuple[1]}.{version_tuple[2]}"


def select_installer_asset(assets):
    """Select the best Windows installer .exe among release assets.

    Prioritizes .exe assets containing 'setup' or 'installer', then any .exe.
    """
    from release_catalog import select_deck_asset
    return select_deck_asset(assets)


def find_latest_update(current_version_str, repo=GITHUB_REPO, timeout=6):
    """Check GitHub releases for a newer version than current_version_str.

    Returns dict with update metadata if a newer version with an installer .exe
    is found, or None otherwise.
    """
    current_ver = parse_version(current_version_str)
    if not current_ver:
        return None

    url = f"https://api.github.com/repos/{repo}/releases"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ScrcpyDeck-Updater",
            "Accept": "application/vnd.github.v3+json",
        },
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        releases = json.loads(resp.read().decode("utf-8"))

    if not isinstance(releases, list):
        return None

    newer_releases = []
    for rel in releases:
        if rel.get("draft", False):
            continue
        tag = rel.get("tag_name", "")
        name = rel.get("name", "")
        rel_ver = parse_version(tag) or parse_version(name)
        if not rel_ver:
            continue
        if rel_ver > current_ver:
            asset = select_installer_asset(rel.get("assets", []))
            if asset:
                newer_releases.append({
                    "version_tuple": rel_ver,
                    "version": format_version(rel_ver),
                    "tag_name": tag,
                    "release_name": name,
                    "asset_name": asset["name"],
                    "download_url": asset["browser_download_url"],
                    "size": asset.get("size", 0),
                    "body": rel.get("body", ""),
                    "html_url": rel.get("html_url", ""),
                })

    if not newer_releases:
        return None

    newer_releases.sort(key=lambda r: r["version_tuple"], reverse=True)
    return newer_releases[0]


def get_installed_scrcpy_version(scrcpy_exe):
    """Query the local scrcpy executable for its version string."""
    if not scrcpy_exe or not Path(scrcpy_exe).is_file():
        return ""
    try:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        res = subprocess.run(
            [str(scrcpy_exe), "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=creationflags,
        )
        output = res.stdout + "\n" + res.stderr
        m = re.search(r"scrcpy\s+v?(\d+\.\d+(?:\.\d+)?)", output, re.IGNORECASE)
        if m:
            return m.group(1)
    except Exception:
        pass
    return ""


def find_latest_scrcpy_release(current_version_str="", repo=SCRCPY_REPO, timeout=6):
    """Check Genymobile/scrcpy GitHub releases for the latest Windows release."""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ScrcpyDeck-Updater",
            "Accept": "application/vnd.github.v3+json",
        },
    )

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        rel = json.loads(resp.read().decode("utf-8"))

    tag = rel.get("tag_name", "")
    name = rel.get("name", "")
    rel_ver = parse_version(tag) or parse_version(name)
    if not rel_ver:
        return None

    current_ver = parse_version(current_version_str)

    zip_asset = None
    for asset in rel.get("assets", []):
        asset_name = asset.get("name", "")
        if "win64" in asset_name.lower() and asset_name.lower().endswith(".zip"):
            zip_asset = asset
            break

    if not zip_asset:
        for asset in rel.get("assets", []):
            if asset.get("name", "").lower().endswith(".zip"):
                zip_asset = asset
                break

    if not zip_asset:
        return None

    vm = re.search(r"(\d+\.\d+(?:\.\d+)?)", tag) or re.search(r"(\d+\.\d+(?:\.\d+)?)", name)
    latest_str = vm.group(1) if vm else format_version(rel_ver)
    has_update = (rel_ver > current_ver) if current_ver else True

    return {
        "version_tuple": rel_ver,
        "version": latest_str,
        "tag_name": tag,
        "release_name": name,
        "asset_name": zip_asset["name"],
        "download_url": zip_asset["browser_download_url"],
        "size": zip_asset.get("size", 0),
        "html_url": rel.get("html_url", f"https://github.com/{repo}/releases"),
        "has_update": has_update,
    }


def extract_scrcpy_archive(zip_path, target_runtime_dir):
    """Extract scrcpy distribution zip into target_runtime_dir safely."""
    from runtime_manager import safe_extract_scrcpy_zip
    return safe_extract_scrcpy_zip(Path(zip_path), Path(target_runtime_dir))


def download_installer(url, target_path, on_progress=None, cancel_event=None, timeout=60):
    """Download installer from url to target_path, calling on_progress(percent).

    Returns True on success, False if cancelled or on failure.
    """
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    part_file = target.with_suffix(target.suffix + ".part")

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ScrcpyDeck-Updater"},
    )

    with urllib.request.urlopen(req, timeout=timeout) as response:
        total_size = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 65536

        with open(part_file, "wb") as f:
            while True:
                if cancel_event and cancel_event.is_set():
                    f.close()
                    part_file.unlink(missing_ok=True)
                    return False
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if on_progress and total_size > 0:
                    percent = min(100, int((downloaded / total_size) * 100))
                    on_progress(percent)

    if part_file.exists():
        part_file.replace(target)
        if on_progress:
            on_progress(100)
        return True
    return False


def backup_user_settings(profile_dir: Path = None) -> Path | None:
    """Create a timestamped backup of the user configuration before update/downgrade."""
    if profile_dir is None:
        from assets import get_profile_dir
        profile_dir = get_profile_dir()

    config_file = profile_dir / "config.json"
    if not config_file.is_file():
        return None

    backups_dir = profile_dir / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backups_dir / f"config_backup_{ts}.json"
    try:
        shutil.copy2(config_file, backup_file)
        return backup_file
    except OSError:
        return None


def get_version_preferences(profile_dir: Path = None) -> dict:
    """Load user version manager preferences (pins, dismissed notifications, etc.)."""
    if profile_dir is None:
        from assets import get_profile_dir
        profile_dir = get_profile_dir()
    defaults = {
        "deck_pinning": "follow_latest",
        "scrcpy_pinning": "follow_latest",
        "deck_pin": "latest",
        "scrcpy_pin": "latest",
        "dismissed_deck_notifications": [],
        "dismissed_scrcpy_notifications": [],
        "show_prereleases": False,
    }
    prefs_file = profile_dir / VERSION_PREFS_FILE
    if prefs_file.is_file():
        try:
            data = json.loads(prefs_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                defaults.update(data)
                return defaults
        except Exception:
            pass
    return defaults


def set_version_preference(key: str, val, profile_dir: Path = None):
    """Persist a single version preference atomically."""
    if profile_dir is None:
        from assets import get_profile_dir
        profile_dir = get_profile_dir()
    prefs = get_version_preferences(profile_dir)
    prefs[key] = val
    try:
        profile_dir.mkdir(parents=True, exist_ok=True)
        prefs_file = profile_dir / VERSION_PREFS_FILE
        tmp_file = profile_dir / f".prefs_{os.getpid()}_{uuid.uuid4().hex}.tmp"
        tmp_file.write_text(json.dumps(prefs, indent=2), encoding="utf-8")
        tmp_file.replace(prefs_file)
    except Exception:
        pass


def get_target_executable():
    """Locate ScrcpyDeck.exe for relaunch after update. Returns None if running from source and not found."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()

    candidates = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Scrcpy Deck Beta" / "ScrcpyDeck.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Scrcpy Deck Beta" / "ScrcpyDeck.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Scrcpy Deck Beta" / "ScrcpyDeck.exe",
        Path(__file__).resolve().parent / "dist" / "ScrcpyDeck" / "ScrcpyDeck.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def create_update_runner_script(installer_path, target_exe=None, pid=None):
    """Create helper scripts (VBScript + fallback BAT) to wait for old process, run installer, and restart."""
    installer = Path(installer_path).resolve()
    if not installer.is_file():
        raise FileNotFoundError(f"Installer not found: {installer}")

    target = Path(target_exe or get_target_executable() or "").resolve() if (target_exe or get_target_executable()) else None
    runner_vbs = installer.parent / "scrcpy_deck_update_runner.vbs"
    runner_bat = installer.parent / "scrcpy_deck_update_runner.bat"
    proc_pid = int(pid) if pid is not None else os.getpid()

    installer_vbs = str(installer).replace('"', '""')
    target_vbs = str(target).replace('"', '""') if target else ""

    installer_bat = str(installer)
    target_bat = str(target) if target else ""

    # 1. VBScript runner runs natively via wscript.exe without opening any console window
    vbs_content = f'''Dim WshShell, ret, objWMIService, colProcesses, fso, waited, pid
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
pid = {proc_pid}

Set objWMIService = GetObject("winmgmts:\\\\.\\root\\cimv2")

' Bounded wait loop for old Scrcpy Deck process to exit (up to 30s)
waited = 0
Do While waited < 60
    Set colProcesses = objWMIService.ExecQuery("Select * from Win32_Process Where ProcessId = " & pid)
    If colProcesses.Count = 0 Then
        Exit Do
    End If
    WScript.Sleep 500
    waited = waited + 1
Loop

' If old process failed to exit cleanly within timeout, abort update safely
Set colProcesses = objWMIService.ExecQuery("Select * from Win32_Process Where ProcessId = " & pid)
If colProcesses.Count > 0 Then
    WScript.Quit 1
End If

' Run installer silently and hidden (0 = SW_HIDE), wait for completion (True)
ret = WshShell.Run("""{installer_vbs}"" /SILENT /FORCECLOSEAPPLICATIONS", 0, True)
If ret <> 0 Then
    ' Fallback to normal interactive install if silent mode failed
    ret = WshShell.Run("""{installer_vbs}""", 1, True)
End If

' Only restart Scrcpy Deck if the installer succeeded (ret = 0)
If ret = 0 Then
    WScript.Sleep 1500
    Set colProcesses = objWMIService.ExecQuery("Select * from Win32_Process Where Name = 'ScrcpyDeck.exe'")
    If colProcesses.Count = 0 Then
        If fso.FileExists("{target_vbs}") Then
            WshShell.Run """{target_vbs}""", 1, False
        End If
    End If
End If
'''
    runner_vbs.write_text(vbs_content, encoding="utf-8")

    # 2. Batch fallback with bounded wait and exit code checks
    bat_content = f"""@echo off
setlocal
chcp 65001 >nul

:: Bounded wait loop for old process {proc_pid}
set /a attempts=0
:wait_loop
if %attempts% geq 60 goto abort_timeout
tasklist /fi "PID eq {proc_pid}" 2>nul | findstr /i "{proc_pid}" >nul
if errorlevel 1 goto proc_exited
timeout /t 1 /nobreak >nul
set /a attempts+=1
goto wait_loop

:abort_timeout
exit /b 1

:proc_exited
start /wait "" "{installer_bat}" /SILENT /FORCECLOSEAPPLICATIONS
if errorlevel 1 (
    start /wait "" "{installer_bat}"
)
if errorlevel 1 (
    exit /b 1
)

timeout /t 2 /nobreak >nul
tasklist /fi "imagename eq ScrcpyDeck.exe" 2>nul | find /i "ScrcpyDeck.exe" >nul
if errorlevel 1 (
    if exist "{target_bat}" (
        start "" "{target_bat}"
    )
)
exit 0
"""
    runner_bat.write_text(bat_content, encoding="utf-8")
    return runner_vbs


def launch_installer_and_restart(installer_path, target_exe=None, pid=None):
    """Launch the installer runner detached and completely hidden so no CMD/PowerShell window opens."""
    if portable_release_page():
        raise RuntimeError("Download the portable ZIP from the Scrcpy Deck release page.")
    proc_pid = int(pid) if pid is not None else os.getpid()
    runner_vbs = create_update_runner_script(installer_path, target_exe, pid=proc_pid)
    runner_bat = runner_vbs.parent / "scrcpy_deck_update_runner.bat"

    if sys.platform == "win32":
        wscript_exe = shutil.which("wscript.exe") or str(
            Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "wscript.exe"
        )
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE

        creationflags = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            | subprocess.DETACHED_PROCESS
            | subprocess.CREATE_NEW_PROCESS_GROUP
        )

        if Path(wscript_exe).is_file():
            cmd = [str(wscript_exe), str(runner_vbs)]
        else:
            cmd = ["cmd.exe", "/c", str(runner_bat)]

        return subprocess.Popen(
            cmd,
            startupinfo=startupinfo,
            creationflags=creationflags,
            close_fds=True,
            shell=False,
        )
    else:
        return subprocess.Popen([str(installer_path)], close_fds=True)
