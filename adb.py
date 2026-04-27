import subprocess
import threading
import re
import os

class AdbManager:
    def __init__(self, adb_exe, script_dir, console_mgr):
        self.adb_exe = adb_exe
        self.script_dir = script_dir
        self.console = console_mgr

    def run_cmd_sync(self, args, context="ADB"):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        command = [self.adb_exe] + args
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                startupinfo=startupinfo,
                cwd=self.script_dir
            )
            self._log_command_result(command, result, context)
            return result
        except Exception as e:
            error_message = f"{context} failed before launch: {e}"
            self.console.log("INFO", f"{context} | Executing: {' '.join(command)}")
            self.console.log("ERROR", error_message)
            self.console.log_hint_for_message(error_message)
            return None

    def _log_command_result(self, command, result, context):
        self.console.log("INFO", f"{context} | Executing: {' '.join(command)}")
        if result.stdout.strip():
            for line in result.stdout.strip().splitlines():
                self.console.log("OUT", line)
        if result.stderr.strip():
            for line in result.stderr.strip().splitlines():
                self.console.log("ERR", line)
        if result.returncode != 0:
            error_summary = f"{context} exited with code {result.returncode}."
            self.console.log("ERROR", error_summary)
            combined = " ".join(part for part in [result.stdout.strip(), result.stderr.strip(), error_summary] if part)
            self.console.log_hint_for_message(combined)

    def refresh_devices(self, on_success, on_error):
        def task():
            result = self.run_cmd_sync(["devices"], context="ADB device scan")
            output = result.stdout.strip() if result else ""
            if result and result.returncode == 0 and output:
                lines = output.split('\n')[1:]
                devices = [line.split()[0] for line in lines if "device" in line]
                if devices:
                    on_success(devices)
                else:
                    on_error("no_devices")
            else:
                on_error("adb_error")
        threading.Thread(target=task, daemon=True).start()

    def get_device_ip(self, serial, on_success, on_error):
        def task():
            result = self.run_cmd_sync(["-s", serial, "shell", "ip", "-f", "inet", "addr", "show", "wlan0"], context=f"Fetch Wi-Fi IP for {serial}")
            output = result.stdout.strip() if result else ""
            if result and result.returncode == 0 and output:
                match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", output)
                if match:
                    on_success(match.group(1))
                    return
            on_error()
        threading.Thread(target=task, daemon=True).start()

    def enable_tcpip(self, serial, on_success, on_error):
        def task():
            result = self.run_cmd_sync(["-s", serial, "tcpip", "5555"], context=f"Enable TCP/IP for {serial}")
            if result and result.returncode == 0:
                on_success()
            else:
                on_error()
        threading.Thread(target=task, daemon=True).start()

    def connect_wireless(self, ip, on_success, on_error):
        def task():
            result = self.run_cmd_sync(["connect", f"{ip}:5555"], context=f"Wireless connect to {ip}:5555")
            output = result.stdout.strip() if result else ""
            combined = " ".join(part for part in [output, result.stderr.strip() if result else ""] if part)
            if result and result.returncode == 0 and "connected" in combined.lower():
                on_success()
            else:
                on_error(combined)
        threading.Thread(target=task, daemon=True).start()

    def kill_server(self, on_success, on_error):
        def task():
            result = self.run_cmd_sync(["kill-server"], context="ADB kill-server")
            if result and result.returncode == 0:
                on_success()
            else:
                on_error()
        threading.Thread(target=task, daemon=True).start()

    def reset_connection(self, ip, on_success, on_error):
        def task():
            if ip:
                self.run_cmd_sync(["disconnect", f"{ip}:5555"], context=f"Disconnect saved target {ip}:5555")
            self.run_cmd_sync(["disconnect"], context="ADB disconnect all")
            self.run_cmd_sync(["kill-server"], context="ADB kill-server before pairing reset")

            adb_key_dir = os.path.join(os.path.expanduser("~"), ".android")
            adb_key_paths = [
                os.path.join(adb_key_dir, "adbkey"),
                os.path.join(adb_key_dir, "adbkey.pub"),
            ]
            removed_keys = []
            key_errors = []
            for key_path in adb_key_paths:
                if not os.path.exists(key_path):
                    continue
                try:
                    os.remove(key_path)
                    removed_keys.append(os.path.basename(key_path))
                except Exception as exc:
                    key_errors.append(f"{os.path.basename(key_path)}: {exc}")

            if removed_keys:
                self.console.log("INFO", f"Removed local ADB key files: {', '.join(removed_keys)}")
            else:
                self.console.log("INFO", "No local ADB key files were found to remove.")

            if key_errors:
                for error in key_errors:
                    self.console.log("ERROR", f"Could not remove {error}")
                self.console.log_hint_for_message("access is denied while removing adb keys")

            self.run_cmd_sync(["start-server"], context="ADB start-server after pairing reset")
            on_success()
        threading.Thread(target=task, daemon=True).start()
