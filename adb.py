import subprocess
import threading
import re
import os
import time

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
        from device_names import DeviceInfo, load_device_name_map, build_display_name
        
        def task():
            mapping = load_device_name_map(self.script_dir)
            result = self.run_cmd_sync(["devices", "-l"], context="ADB device scan")
            output = result.stdout.strip() if result else ""
            if result and result.returncode == 0 and output:
                lines = output.split('\n')[1:]
                device_infos = []
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    parts = line.split()
                    if len(parts) < 2: continue
                    
                    serial = parts[0]
                    state = parts[1]
                    
                    if state != "device":
                        self.console.log("WARN", f"Device unauthorized or offline: {serial}. Please allow USB debugging on the phone.")
                        continue
                        
                    transport = "usb"
                    if ":" in serial:
                        transport = "wireless"
                    elif serial.startswith("emulator-"):
                        transport = "emulator"
                        
                    info = DeviceInfo(serial=serial, state=state, transport=transport)
                    
                    for part in parts[2:]:
                        if part.startswith("product:"):
                            info.product = part.split(":", 1)[1]
                        elif part.startswith("model:"):
                            info.model = part.split(":", 1)[1]
                        elif part.startswith("device:"):
                            info.device = part.split(":", 1)[1]
                            
                    props_to_fetch = {
                        "ro.serialno": "hardware_serial",
                        "ro.product.manufacturer": "manufacturer",
                        "ro.product.brand": "brand",
                        "ro.product.model": "model",
                        "ro.product.name": "product",
                        "ro.product.device": "device",
                        "ro.product.marketname": "market_name",
                        "ro.vendor.product.model": "model_vendor",
                        "ro.product.vendor.model": "model_vendor2",
                        "ro.config.marketing_name": "market_name2",
                        "ro.vendor.oplus.market.name": "market_name3",
                        "ro.miui.device.name": "market_name4"
                    }
                    
                    for prop, attr in props_to_fetch.items():
                        cmd = [self.adb_exe, "-s", serial, "shell", "getprop", prop]
                        try:
                            res = subprocess.run(
                                cmd,
                                capture_output=True,
                                text=True,
                                cwd=self.script_dir,
                                timeout=1.5,
                                startupinfo=startupinfo
                            )
                            val = res.stdout.strip()
                            if val:
                                if attr.startswith("market_name"):
                                    if not info.market_name: info.market_name = val
                                elif attr.startswith("model"):
                                    if not info.model: info.model = val
                                else:
                                    setattr(info, attr, val)
                        except Exception:
                            pass
                            
                    if not getattr(info, "hardware_serial", ""):
                        if info.transport == "usb":
                            info.hardware_serial = info.serial

                    build_display_name(info, mapping)
                    self.console.log("INFO", f"Detected device: {info.display_name} [serial: {info.serial[:6]}...]")
                    device_infos.append(info)
                    
                if device_infos:
                    on_success(device_infos)
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
            target = ip if ":" in ip else f"{ip}:5555"
            result = self.run_cmd_sync(["connect", target], context=f"Wireless connect to {target}")
            output = result.stdout.strip() if result else ""
            combined = " ".join(part for part in [output, result.stderr.strip() if result else ""] if part)
            lowered = combined.lower()
            
            # Robust verification of connection success
            if result and result.returncode == 0 and ("connected to" in lowered or "already connected" in lowered) and not ("failed" in lowered or "cannot" in lowered or "unable" in lowered):
                on_success()
            else:
                on_error(combined)
        threading.Thread(target=task, daemon=True).start()

    def pair_wireless(self, ip_port, code, on_success, on_error):
        def task():
            result = self.run_cmd_sync(["pair", ip_port, code], context=f"Wireless pair with {ip_port}")
            output = result.stdout.strip() if result else ""
            combined = " ".join(part for part in [output, result.stderr.strip() if result else ""] if part)
            if result and result.returncode == 0 and "successfully paired" in combined.lower():
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

    def discover_mdns_ports(self, on_success, on_error):
        def task():
            last_output = "No scan performed."
            for attempt in range(1, 6):
                self.console.log("INFO", f"Scanning local network for dynamic wireless ports (Attempt {attempt}/5)...")
                result = self.run_cmd_sync(["mdns", "services"], context=f"ADB mdns services attempt {attempt}")
                output = result.stdout.strip() if result else ""
                last_output = output or last_output
                
                if result and result.returncode == 0 and output:
                    found = {}
                    for line in output.splitlines():
                        if "_adb-tls-connect._tcp" in line:
                            match = re.search(r'(\d+\.\d+\.\d+\.\d+):(\d+)', line)
                            if match:
                                ip, port = match.groups()
                                found[ip] = port
                    if found:
                        self.console.log("INFO", f"mDNS discovery succeeded on attempt {attempt}.")
                        on_success(found)
                        return
                
                if attempt < 5:
                    self.console.log("WARN", f"No active dynamic wireless debugging services found in mDNS scan. Retrying in 1.5s (Attempt {attempt}/5)...")
                    time.sleep(1.5)
            
            self.console.log("ERROR", "mDNS service discovery failed after 5 attempts.")
            on_error(last_output or "No active discovered services after 5 attempts.")
        threading.Thread(target=task, daemon=True).start()

    def resolve_device_by_serial(self, hardware_serial, on_success, on_error):
        def task():
            if not hardware_serial:
                on_error("No hardware serial provided.")
                return
            
            last_output = "No scan performed."
            target_token = f"adb-{hardware_serial.lower()}"
            
            for attempt in range(1, 6):
                self.console.log("INFO", f"Scanning local network for hardware serial '{hardware_serial}' (Attempt {attempt}/5)...")
                result = self.run_cmd_sync(["mdns", "services"], context=f"ADB mdns services attempt {attempt}")
                output = result.stdout.strip() if result else ""
                last_output = output or last_output
                
                if result and result.returncode == 0 and output:
                    resolved = {}
                    for line in output.splitlines():
                        line_lower = line.lower()
                        if target_token in line_lower:
                            match = re.search(r'(\d+\.\d+\.\d+\.\d+):(\d+)', line)
                            if match:
                                ip, port = match.groups()
                                if "_adb-tls-connect._tcp" in line:
                                    resolved["dynamic"] = (ip, port)
                                elif "_adb._tcp" in line:
                                    resolved["stable"] = (ip, port)
                    if resolved:
                        self.console.log("INFO", f"mDNS serial resolution succeeded on attempt {attempt} for {hardware_serial}.")
                        on_success(resolved)
                        return
                
                if attempt < 5:
                    self.console.log("WARN", f"Device '{hardware_serial}' not found in mDNS scan. Retrying in 1.5s (Attempt {attempt}/5)...")
                    time.sleep(1.5)
            
            self.console.log("ERROR", f"mDNS serial resolution failed for {hardware_serial} after 5 attempts.")
            on_error("Device not found in mDNS scan after 5 attempts.")
        threading.Thread(target=task, daemon=True).start()

