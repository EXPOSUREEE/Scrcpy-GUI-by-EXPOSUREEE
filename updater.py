"""Software update discovery, download, and execution for Scrcpy Deck."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

GITHUB_REPO = "Yavagu/Scrcpy-GUI-by-EXPOSUREEE"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases"


def parse_version(text):
    """Extract a 3-part version tuple (major, minor, patch) from text.

    Supports formats like '4.0.0', 'v4.0.1', 'ScrcpyDeck 4.0.2', etc.
    Returns (major, minor, patch) as ints, or None if no 3-part version is found.
    """
    if not text:
        return None
    match = re.search(r"\bv?(\d+)\.(\d+)\.(\d+)\b", str(text), re.IGNORECASE)
    if match:
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return None


def format_version(version_tuple):
    """Format a version tuple as 'major.minor.patch'."""
    return f"{version_tuple[0]}.{version_tuple[1]}.{version_tuple[2]}"


def select_installer_asset(assets):
    """Select the best Windows installer .exe among release assets.

    Prioritizes .exe assets containing 'setup' or 'installer', then any .exe.
    """
    candidates = []
    for asset in assets:
        name = asset.get("name", "")
        url = asset.get("browser_download_url", "")
        if not name or not url:
            continue
        if name.lower().endswith(".exe"):
            candidates.append(asset)

    if not candidates:
        return None

    def score(asset):
        name = asset.get("name", "").lower()
        pts = 0
        if "setup" in name or "installer" in name:
            pts += 10
        if "scrcpy" in name or "deck" in name:
            pts += 5
        if "x64" in name or "win64" in name:
            pts += 2
        return pts

    candidates.sort(key=score, reverse=True)
    return candidates[0]


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


def get_target_executable():
    """Locate ScrcpyDeck.exe for relaunch after update."""
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
    return Path(sys.executable).resolve()


def create_update_runner_script(installer_path, target_exe=None):
    """Create helper scripts (VBScript + fallback BAT) to run the installer and relaunch Scrcpy Deck completely hidden."""
    installer = Path(installer_path).resolve()
    if not installer.is_file():
        raise FileNotFoundError(f"Installer not found: {installer}")

    target = Path(target_exe or get_target_executable()).resolve()
    runner_vbs = installer.parent / "scrcpy_deck_update_runner.vbs"
    runner_bat = installer.parent / "scrcpy_deck_update_runner.bat"

    # 1. VBScript runner runs natively via wscript.exe without opening any console window
    vbs_content = f'''Dim WshShell, ret, objWMIService, colProcesses
Set WshShell = CreateObject("WScript.Shell")

' Wait 2 seconds for Scrcpy Deck to close cleanly and release file locks
WScript.Sleep 2000

' Run installer silently and hidden (0 = SW_HIDE), wait for completion (True)
ret = WshShell.Run("""{str(installer)}"" /SILENT /FORCECLOSEAPPLICATIONS", 0, True)
If ret <> 0 Then
    ' Fallback to normal interactive install if silent mode failed
    WshShell.Run """{str(installer)}""", 1, True
End If

' Allow installation changes to settle
WScript.Sleep 1500

' Check if ScrcpyDeck is already running; if not, restart it
Set objWMIService = GetObject("winmgmts:\\\\.\\root\\cimv2")
Set colProcesses = objWMIService.ExecQuery("Select * from Win32_Process Where Name = 'ScrcpyDeck.exe'")
If colProcesses.Count = 0 Then
    If CreateObject("Scripting.FileSystemObject").FileExists("""{str(target)}""") Then
        WshShell.Run """{str(target)}""", 1, False
    End If
End If
'''
    runner_vbs.write_text(vbs_content, encoding="utf-8")

    # 2. Batch fallback that also exits cleanly with exit 0 (never hangs or stays open)
    bat_content = f"""@echo off
setlocal
chcp 65001 >nul

:: Wait 2 seconds for Scrcpy Deck to close cleanly and release file locks
timeout /t 2 /nobreak >nul

:: Run installer silently with forced application closure
start /wait "" "{str(installer)}" /SILENT /FORCECLOSEAPPLICATIONS
if errorlevel 1 (
    start /wait "" "{str(installer)}"
)

:: Wait 2 seconds for installation to finalize
timeout /t 2 /nobreak >nul

:: Check if ScrcpyDeck.exe is running; if not, restart it
tasklist /fi "imagename eq ScrcpyDeck.exe" 2>nul | find /i "ScrcpyDeck.exe" >nul
if errorlevel 1 (
    if exist "{str(target)}" (
        start "" "{str(target)}"
    )
)

exit 0
"""
    runner_bat.write_text(bat_content, encoding="utf-8")
    return runner_vbs


def launch_installer_and_restart(installer_path, target_exe=None):
    """Launch the installer runner detached and completely hidden so no CMD/PowerShell window opens."""
    runner_vbs = create_update_runner_script(installer_path, target_exe)
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

        subprocess.Popen(
            cmd,
            startupinfo=startupinfo,
            creationflags=creationflags,
            close_fds=True,
            shell=False,
        )
    else:
        subprocess.Popen([str(installer_path)], close_fds=True)
