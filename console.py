import re
from datetime import datetime
import subprocess
import threading

def infer_fix_hint(message):
    lowered = message.lower()
    if "adb" in lowered and ("not recognized" in lowered or "not responding" in lowered or "no such file" in lowered or "cannot find" in lowered):
        return "Make sure adb.exe is next to this app or available in PATH."
    if "scrcpy" in lowered and ("not recognized" in lowered or "no such file" in lowered or "cannot find" in lowered):
        return "Make sure scrcpy.exe is next to this app or available in PATH."
    if "unauthorized" in lowered:
        return "Unlock the phone and accept the USB debugging authorization prompt, then scan again."
    if "no devices" in lowered or "device not found" in lowered:
        return "Connect the phone by USB, enable USB debugging, and tap 'Scan devices' again."
    if "failed to connect" in lowered or "unable to connect" in lowered or "connection failed" in lowered:
        return "Check that phone and PC are on the same Wi-Fi, the IP is correct, and TCP/IP mode is enabled on port 5555."
    if "could not find ip" in lowered or "wlan0" in lowered:
        return "Turn Wi-Fi on for the phone and keep the USB connection active while fetching the address."
    if "access is denied" in lowered:
        return "Try running the app as administrator and confirm no other tool is locking adb or scrcpy."
    if "more than one device" in lowered:
        return "Disconnect extra devices or keep using the selected serial with the device chooser."
    return None

def extract_console_level(line):
    match = re.search(r"\]\s+([A-Z]+)\s", line)
    if not match:
        return "OUT"
    level = match.group(1)
    if level in {"ERR", "ERROR"}:
        return "ERROR"
    return level

class ConsoleManager:
    def __init__(self, append_callback, script_dir):
        self.append_callback = append_callback
        self.script_dir = script_dir

    def log(self, level, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {level:<5} {message}\n"
        self.append_callback(line, level)

    def log_hint_for_message(self, message):
        hint = infer_fix_hint(message)
        if hint:
            self.log("HINT", hint)

    def run_command_async(self, command_text):
        self.log("INFO", f"Console command | Executing: {command_text}")
        def task():
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                result = subprocess.run(
                    command_text,
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=self.script_dir,
                    startupinfo=startupinfo
                )
                if result.stdout.strip():
                    for line in result.stdout.strip().splitlines():
                        self.log("OUT", line)
                if result.stderr.strip():
                    for line in result.stderr.strip().splitlines():
                        self.log("ERR", line)
                if result.returncode == 0:
                    self.log("INFO", f"Console command completed with code {result.returncode}.")
                else:
                    summary = f"Console command exited with code {result.returncode}."
                    self.log("ERROR", summary)
                    combined = " ".join(
                        part for part in [command_text, result.stdout.strip(), result.stderr.strip(), summary] if part
                    )
                    self.log_hint_for_message(combined)
            except Exception as e:
                error_message = f"Console command failed before launch: {e}"
                self.log("ERROR", error_message)
                self.log_hint_for_message(error_message)
        
        threading.Thread(target=task, daemon=True).start()
