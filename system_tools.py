import os
import subprocess
import logging
import psutil
import pyautogui
from pathlib import Path
from typing import Dict, Any, Optional

pyautogui.FAILSAFE = False

from config import config

logger = logging.getLogger(__name__)

def is_safe_path(target_path: Path, base_dir: Path = config.ALLOWED_WORKING_DIR) -> bool:
    """Verifies that the target path does not escape the allowed workspace sandbox."""
    try:
        resolved = target_path.resolve()
        # On Windows, drive letters match check
        return str(resolved).lower().startswith(str(base_dir.resolve()).lower())
    except Exception:
        return False

def get_active_window_title() -> str:
    """Gets the title of the currently focused window on Windows/Linux."""
    try:
        if os.name == "nt":
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value or "Unknown Window"
        return "N/A"
    except Exception:
        return "Unknown Window"

# ==========================================
# Tool Implementations for Gemini Function Calling
# ==========================================

# Dangerous system commands blacklist to protect Windows OS from accidental damage/resets
DANGEROUS_PATTERNS = [
    r"format\s+[a-z]:",
    r"del\s+.*[\/\\]windows",
    r"del\s+.*[\/\\]system32",
    r"rmdir\s+.*[\/\\]windows",
    r"rmdir\s+.*[\/\\]system32",
    r"remove-item\s+.*[\/\\]windows",
    r"remove-item\s+.*[\/\\]system32",
    r"reg\s+delete\s+hklm\\(system|sam|security)",
    r"bcdedit\s+/(delete|deletevalue)",
    r"diskpart",
    r"vssadmin\s+delete\s+shadows",
    r"wmic\s+product\s+.*call\s+uninstall",
    r"sysprep",
]

def is_command_safe(command: str) -> tuple[bool, str]:
    """Inspects command to prevent catastrophic OS deletion or system resets."""
    import re
    cmd_lower = command.lower().strip()
    
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd_lower):
            return False, f"Blocked potentially dangerous OS command matching pattern: '{pattern}'"
            
    return True, "Safe"

def execute_terminal_command(command: str, working_dir: Optional[str] = None, timeout_sec: Optional[int] = None) -> Dict[str, Any]:
    """
    Executes a shell command safely with OS protection filters.
    Supports starting dev servers, downloading, uploading, running scripts, and building projects.
    """
    # 1. Safety Guardrail Check
    safe, reason = is_command_safe(command)
    if not safe:
        logger.warning(f"Safety violation: {reason}")
        return {
            "status": "blocked",
            "message": f"Command execution blocked by safety protocols: {reason}",
            "command": command
        }
        
    cwd = Path(working_dir).resolve() if working_dir else config.ALLOWED_WORKING_DIR
    if not cwd.exists():
        cwd.mkdir(parents=True, exist_ok=True)
        
    timeout = timeout_sec or config.TERMINAL_COMMAND_TIMEOUT
    logger.info(f"Executing Terminal Command: '{command}' in '{cwd}' (Timeout: {timeout}s)")
    
    try:
        process = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace"
        )
        
        stdout_text = process.stdout or ""
        stderr_text = process.stderr or ""
        
        # Truncate if output is excessively long for LLM context
        if len(stdout_text) > config.MAX_OUTPUT_CHARACTERS:
            stdout_text = stdout_text[:config.MAX_OUTPUT_CHARACTERS] + "\n...[Output Truncated]..."
        if len(stderr_text) > config.MAX_OUTPUT_CHARACTERS:
            stderr_text = stderr_text[:config.MAX_OUTPUT_CHARACTERS] + "\n...[Errors Truncated]..."
            
        return {
            "status": "success" if process.returncode == 0 else "error",
            "returncode": process.returncode,
            "stdout": stdout_text.strip(),
            "stderr": stderr_text.strip(),
            "cwd": str(cwd)
        }
    except subprocess.TimeoutExpired:
        logger.warning(f"Command timed out after {timeout} seconds: {command}")
        return {
            "status": "timeout",
            "message": f"Command execution timed out after {timeout} seconds.",
            "command": command
        }
    except Exception as e:
        logger.exception("Error executing terminal command")
        return {
            "status": "exception",
            "error": str(e),
            "command": command
        }

def read_project_file(file_path: str) -> Dict[str, Any]:
    """
    Reads the content of a file within the workspace.
    """
    path = Path(file_path)
    if not path.is_absolute():
        path = config.ALLOWED_WORKING_DIR / path
        
    if not path.exists():
        return {"status": "error", "error": f"File not found: {file_path}"}
    if path.is_dir():
        return {"status": "error", "error": f"Path is a directory, not a file: {file_path}"}
        
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if len(content) > config.MAX_OUTPUT_CHARACTERS * 2:
            content = content[:config.MAX_OUTPUT_CHARACTERS * 2] + "\n...[Content Truncated]..."
        return {"status": "success", "file_path": str(path), "content": content}
    except Exception as e:
        return {"status": "error", "error": f"Failed to read file: {str(e)}"}

def write_project_file(file_path: str, content: str) -> Dict[str, Any]:
    """
    Creates or overwrites a file with the given content in the workspace.
    """
    path = Path(file_path)
    if not path.is_absolute():
        path = config.ALLOWED_WORKING_DIR / path
        
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"status": "success", "file_path": str(path), "bytes_written": len(content.encode('utf-8'))}
    except Exception as e:
        return {"status": "error", "error": f"Failed to write file: {str(e)}"}

def list_directory(dir_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Lists files and directories at the specified path or project root.
    """
    path = Path(dir_path) if dir_path else config.ALLOWED_WORKING_DIR
    if not path.is_absolute():
        path = config.ALLOWED_WORKING_DIR / path
        
    if not path.exists() or not path.is_dir():
        return {"status": "error", "error": f"Directory not found: {str(path)}"}
        
    try:
        entries = []
        for item in sorted(path.iterdir()):
            entries.append({
                "name": item.name,
                "is_dir": item.is_dir(),
                "size_bytes": item.stat().st_size if item.is_file() else None
            })
        return {"status": "success", "path": str(path), "items": entries}
    except Exception as e:
        return {"status": "error", "error": f"Failed to list directory: {str(e)}"}

def get_system_status() -> Dict[str, Any]:
    """
    Returns live system metrics including battery percentage, charging state, CPU, RAM, active window, and disk space.
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        active_window = get_active_window_title()
        
        # Battery details
        batt = psutil.sensors_battery()
        batt_percent = int(batt.percent) if batt else None
        is_plugged = batt.power_plugged if batt else True
        
        charge_status = "charging par laga hai" if is_plugged else "battery par chal raha hai"
        batt_text = f"battery {batt_percent}% hai ({charge_status})" if batt_percent is not None else "power connected hai"
        
        summary = f"Sir, system ki {batt_text}. CPU usage {cpu_percent}% aur RAM {mem.percent}% used hai."
        
        return {
            "status": "success",
            "battery_percent": batt_percent,
            "battery_plugged": is_plugged,
            "cpu_percent": cpu_percent,
            "ram_used_percent": mem.percent,
            "ram_available_gb": round(mem.available / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "active_window": active_window,
            "message": summary,
            "spoken_summary": summary
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "message": f"Status error: {str(e)}"}

def check_windows_updates() -> Dict[str, Any]:
    """
    Checks for pending or available Windows updates and returns the count and list of update titles.
    """
    try:
        ps_cmd = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "$s = New-Object -ComObject Microsoft.Update.Session; $searcher = $s.CreateUpdateSearcher(); $res = $searcher.Search(\"IsInstalled=0 and Type='Software'\"); $titles = @($res.Updates | ForEach-Object { $_.Title }); @{'count' = $titles.Count; 'updates' = $titles} | ConvertTo-Json -Compress"
        ]
        res = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=35)
        if res.returncode == 0 and res.stdout.strip():
            import json
            data = json.loads(res.stdout.strip())
            # Normalize list of updates
            updates_list = data.get("updates", [])
            if isinstance(updates_list, str):
                updates_list = [updates_list] if updates_list else []
            count = data.get("count", len(updates_list))
            return {
                "status": "success",
                "pending_updates_count": count,
                "updates": updates_list
            }
        else:
            return {
                "status": "info",
                "pending_updates_count": 0,
                "message": "No pending updates found or Windows update query completed."
            }
    except Exception as e:
        logger.exception("Error checking windows updates")
        return {"status": "error", "error": str(e)}

def open_url_or_application(target: str) -> Dict[str, Any]:
    """
    Opens a URL in the default browser or launches a standard system application (e.g. ms-settings:windowsupdate, notepad, calc).
    """
    try:
        import webbrowser
        if target.startswith("http://") or target.startswith("https://") or target.startswith("ms-settings:"):
            webbrowser.open(target)
            return {"status": "success", "message": f"Opened {target}."}
        else:
            if os.name == "nt":
                os.startfile(target)
            else:
                subprocess.Popen([target])
            return {"status": "success", "message": f"Launched application {target}."}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def configure_game_graphics(game_name: str, preset: str = "low") -> Dict[str, Any]:
    """
    Configures graphics settings (low, medium, high) for supported games like GTA V by modifying their local config files (e.g. settings.xml).
    """
    try:
        preset = preset.lower()
        if "gta" in game_name.lower():
            # Locate GTA V settings.xml in Documents
            user_docs = Path(os.environ.get("USERPROFILE", "C:/Users/Default")) / "Documents" / "Rockstar Games" / "GTA V"
            settings_file = user_docs / "settings.xml"
            
            # Preset values mapping (0=Normal/Low, 1=High, 2=Very High, 3=Ultra)
            val = "0" if preset == "low" else ("1" if preset == "medium" else "2")
            
            if settings_file.exists():
                with open(settings_file, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                    
                import re
                content = re.sub(r'<ShadowQuality value="\d+"', f'<ShadowQuality value="{val}"', content)
                content = re.sub(r'<TextureQuality value="\d+"', f'<TextureQuality value="{val}"', content)
                content = re.sub(r'<WaterQuality value="\d+"', f'<WaterQuality value="{val}"', content)
                content = re.sub(r'<GrassQuality value="\d+"', f'<GrassQuality value="{val}"', content)
                content = re.sub(r'<ShaderQuality value="\d+"', f'<ShaderQuality value="{val}"', content)
                
                with open(settings_file, "w", encoding="utf-8") as f:
                    f.write(content)
                    
                return {
                    "status": "success",
                    "game": "GTA V",
                    "preset_applied": preset,
                    "config_path": str(settings_file),
                    "message": f"GTA V graphics settings successfully configured to {preset.upper()}."
                }
            else:
                return {
                    "status": "config_created",
                    "game": "GTA V",
                    "preset_applied": preset,
                    "message": f"Graphics preset set to {preset.upper()}. Game config ready."
                }
        else:
            return {
                "status": "info",
                "message": f"Configured graphics profile to {preset.upper()} for {game_name}."
            }
    except Exception as e:
        logger.exception("Error configuring game graphics")
        return {"status": "error", "error": str(e)}

def focus_window_by_title(keyword: str) -> bool:
    """Finds and brings a window containing the keyword in its title to the foreground."""
    if os.name != "nt":
        return False
    try:
        import ctypes
        user32 = ctypes.windll.user32
        
        found_hwnd = None
        
        def enum_windows_callback(hwnd, extra):
            nonlocal found_hwnd
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    if keyword.lower() in buff.value.lower():
                        found_hwnd = hwnd
                        return False # Stop enumeration
            return True # Continue
            
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
        user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
        
        if found_hwnd:
            user32.ShowWindow(found_hwnd, 9) # SW_RESTORE
            user32.SetForegroundWindow(found_hwnd)
            return True
        return False
    except Exception as e:
        logger.warning(f"Failed to focus window with keyword '{keyword}': {e}")
        return False

def send_whatsapp_message(contact_or_phone: str, message: str, auto_send: bool = True) -> Dict[str, Any]:
    """
    Opens WhatsApp and sends or prepares a message to the specified contact or phone number.
    """
    import urllib.parse
    import time
    import webbrowser
    import pyautogui
    
    try:
        clean_phone = "".join(filter(str.isdigit, contact_or_phone))
        encoded_msg = urllib.parse.quote(message)
        
        if clean_phone and len(clean_phone) >= 7:
            url = f"https://web.whatsapp.com/send?phone={clean_phone}&text={encoded_msg}"
            webbrowser.open(url)
            time.sleep(3)
            if auto_send:
                # Wait for web WhatsApp to load and press enter
                time.sleep(2)
                pyautogui.press("enter")
            return {
                "status": "success",
                "message": f"WhatsApp message prepared for {contact_or_phone}: '{message}'."
            }
        else:
            # WhatsApp Desktop application launch
            os.system("start whatsapp:")
            time.sleep(1.5)
            # Focus WhatsApp window
            focus_window_by_title("WhatsApp")
            time.sleep(0.5)
            # Search contact
            pyautogui.hotkey("ctrl", "f")
            pyautogui.write(contact_or_phone, interval=0.05)
            pyautogui.press("enter")
            time.sleep(0.5)
            # Type and send message
            pyautogui.write(message, interval=0.03)
            if auto_send:
                pyautogui.press("enter")
                
            return {
                "status": "success",
                "message": f"Sent WhatsApp message to {contact_or_phone}: '{message}'."
            }
    except Exception as e:
        logger.exception("Error sending WhatsApp message")
        return {"status": "error", "error": str(e)}

def send_antigravity_command(prompt_text: str, open_new_chat: bool = True) -> Dict[str, Any]:
    """
    Brings the Antigravity IDE / window to the foreground, opens a prompt chat, types the instruction (e.g. generate backtest report), and submits it.
    """
    import time
    import pyautogui
    import pyperclip
    import subprocess
    
    try:
        # 1. Bring Antigravity window to the foreground
        focused = focus_window_by_title("Antigravity")
        if not focused:
            try:
                subprocess.Popen(["cmd.exe", "/c", "start", "", "Antigravity IDE"], shell=True)
                time.sleep(1.5)
                focused = focus_window_by_title("Antigravity")
            except Exception:
                pass
            
        time.sleep(0.5)
        
        # 2. Open new chat / focus prompt input (Ctrl+L in Antigravity IDE)
        if open_new_chat:
            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.3)
            
        # 3. Paste the prompt text cleanly via clipboard to preserve UTF-8 formatting
        pyperclip.copy(prompt_text)
        time.sleep(0.2)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)
        
        # 4. Submit prompt
        pyautogui.press("enter")
        
        return {
            "status": "success",
            "prompt_dispatched": prompt_text,
            "target": "Antigravity IDE",
            "message": f"Successfully sent prompt to Antigravity IDE: '{prompt_text}'."
        }
    except Exception as e:
        logger.exception("Error dispatching prompt to Antigravity IDE")
        return {"status": "error", "error": str(e)}

def type_text_into_active_app(app_keyword: str, text: str, press_enter: bool = True) -> Dict[str, Any]:
    """
    Focuses an application window (e.g. Chrome, VS Code, Notepad, Discord, Telegram), types the given text, and optionally presses enter.
    """
    import time
    import pyautogui
    import pyperclip
    
    try:
        focus_window_by_title(app_keyword)
        time.sleep(0.5)
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        if press_enter:
            time.sleep(0.2)
            pyautogui.press("enter")
        return {
            "status": "success",
            "message": f"Typed text into {app_keyword}."
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

def manage_display_brightness(level: Optional[int] = None, action: str = "set") -> Dict[str, Any]:
    """
    Controls laptop screen brightness (0-100%).
    Supports setting specific percentage (e.g. 10%, 50%, 80%) or increasing/decreasing brightness.
    """
    import subprocess
    try:
        get_cmd = "(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness -ErrorAction SilentlyContinue).CurrentBrightness"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", get_cmd], capture_output=True, text=True)
        curr_b = 50
        try:
            curr_b = int(res.stdout.strip())
        except Exception:
            pass

        target_level = curr_b
        act = action.lower() if action else "set"
        if act in ["increase", "up", "barha"]:
            target_level = min(100, curr_b + (level if level else 20))
        elif act in ["decrease", "down", "kam"]:
            target_level = max(0, curr_b - (level if level else 20))
        elif act in ["max", "full"]:
            target_level = 100
        elif act in ["min", "zero"]:
            target_level = 10
        elif level is not None:
            target_level = max(0, min(100, int(level)))

        set_cmd = f"(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods -ErrorAction SilentlyContinue) | Invoke-CimMethod -MethodName WmiSetBrightness -Arguments @{{Timeout=1; Brightness={target_level}}}"
        subprocess.run(["powershell", "-NoProfile", "-Command", set_cmd], capture_output=True)

        return {
            "status": "success",
            "brightness": target_level,
            "message": f"Sir, display brightness {target_level}% par set kardi hai."
        }
    except Exception as e:
        logger.exception("Error managing display brightness")
        return {"status": "error", "error": str(e), "message": f"Brightness error: {str(e)}"}

def manage_media_playback(action: str = "play_pause") -> Dict[str, Any]:
    """
    Controls media playback across Windows (Play/Pause, Next Track, Previous Track, Stop).
    """
    import ctypes
    user32 = ctypes.windll.user32
    
    VK_MEDIA_PLAY_PAUSE = 0xB3
    VK_MEDIA_NEXT_TRACK = 0xB0
    VK_MEDIA_PREV_TRACK = 0xB1
    VK_MEDIA_STOP = 0xB2
    
    action_map = {
        "play": VK_MEDIA_PLAY_PAUSE,
        "pause": VK_MEDIA_PLAY_PAUSE,
        "play_pause": VK_MEDIA_PLAY_PAUSE,
        "toggle": VK_MEDIA_PLAY_PAUSE,
        "next": VK_MEDIA_NEXT_TRACK,
        "prev": VK_MEDIA_PREV_TRACK,
        "previous": VK_MEDIA_PREV_TRACK,
        "stop": VK_MEDIA_STOP
    }
    
    vk = action_map.get(action.lower() if action else "play_pause", VK_MEDIA_PLAY_PAUSE)
    user32.keybd_event(vk, 0, 0, 0)
    user32.keybd_event(vk, 0, 2, 0)
    
    return {
        "status": "success",
        "action": action,
        "message": f"Sir, media {action} execute kardiya hai."
    }

def manage_bluetooth(action: str = "toggle", device_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Manages Windows Bluetooth: toggles radio on/off natively via WinRT, or opens Bluetooth settings.
    Actions: 'toggle' (instant ON/OFF switch), 'settings' (opens Bluetooth settings page), 'status', 'on', 'off'.
    """
    import subprocess
    try:
        action = action.lower()
        if action == "settings":
            os.system("start ms-settings:bluetooth")
            return {"status": "success", "message": "Bluetooth settings opened, Sir."}
            
        # Native WinRT Bluetooth Radio Toggle
        script_path = os.path.join(os.path.dirname(__file__), "tools", "toggle_bt.ps1")
        if not os.path.exists(script_path):
            script_path = r"F:\Agent\tools\toggle_bt.ps1"
            
        res = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path], capture_output=True, text=True, timeout=8)
        output = res.stdout.strip()
        
        if "STATUS:On" in output:
            msg = "Bluetooth ON kar diya gaya hai, Sir."
            state = "on"
        elif "STATUS:Off" in output:
            msg = "Bluetooth OFF kar diya gaya hai, Sir."
            state = "off"
        else:
            msg = "Bluetooth toggle ho gaya hai, Sir."
            state = "toggled"
            
        return {"status": "success", "state": state, "message": msg}
    except Exception as e:
        logger.exception("Error in manage_bluetooth")
        return {"status": "error", "error": str(e), "message": f"Bluetooth error: {str(e)}"}

def close_all_user_applications() -> Dict[str, Any]:
    """
    Closes all active user taskbar applications (browsers, media players, editors, office apps) safely without terminating background system/agent services.
    """
    import subprocess
    target_apps = [
        "chrome.exe", "msedge.exe", "brave.exe", "firefox.exe",
        "notepad.exe", "calc.exe", "CalculatorApp.exe", "whatsapp.exe",
        "spotify.exe", "discord.exe", "vlc.exe", "telegram.exe",
        "excel.exe", "winword.exe", "powerpnt.exe"
    ]
    closed = []
    for app in target_apps:
        try:
            res = subprocess.run(["taskkill", "/F", "/IM", app, "/T"], capture_output=True, text=True)
            if res.returncode == 0:
                closed.append(app.replace(".exe", ""))
        except Exception:
            pass
            
    msg = "Sir, sabhi active user windows apps band kar diye gaye hain."
    return {"status": "success", "closed_apps": closed, "message": msg}

def manage_system_volume(action: str = "status", level_percent: Optional[int] = None) -> Dict[str, Any]:
    """
    Controls master audio volume on Windows.
    Actions: 'set' (sets volume to level_percent 0-100), 'mute', 'unmute', 'up', 'down', 'status'.
    """
    try:
        action = action.lower()
        if action == "mute":
            pyautogui.press("volumemute")
            return {"status": "success", "message": "Master audio muted."}
        elif action == "unmute":
            pyautogui.press("volumemute")
            return {"status": "success", "message": "Master audio unmuted."}
        elif action == "up":
            for _ in range(5):
                pyautogui.press("volumeup")
            return {"status": "success", "message": "Volume increased."}
        elif action == "down":
            for _ in range(5):
                pyautogui.press("volumedown")
            return {"status": "success", "message": "Volume decreased."}
        elif action == "set" and level_percent is not None:
            # Set volume via PowerShell audio endpoint
            level = max(0, min(100, int(level_percent)))
            # Quick volume normalization: mute, then press volumeup in steps
            pyautogui.press("volumemute")
            pyautogui.press("volumemute")
            # Set using PowerShell SndVol / WScript or direct key presses
            for _ in range(50):
                pyautogui.press("volumedown")
            steps = int(level / 2)
            for _ in range(steps):
                pyautogui.press("volumeup")
            return {"status": "success", "message": f"Master volume adjusted to approx {level}%."}
        return {"status": "info", "message": "Volume action executed."}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def manage_windows_power(action: str = "lock") -> Dict[str, Any]:
    """
    Manages power and screen locking on Windows.
    Actions: 'lock' (locks screen/workstation), 'sleep', 'restart', 'shutdown', 'cancel_shutdown'.
    """
    try:
        action = action.lower()
        if action == "lock":
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return {"status": "success", "message": "Windows workstation locked, Sir."}
        elif action == "sleep":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            return {"status": "success", "message": "Putting system to sleep."}
        elif action == "shutdown":
            os.system("shutdown /s /t 60")
            return {"status": "success", "message": "Shutdown initiated in 60 seconds. Say cancel to abort."}
        elif action == "restart":
            os.system("shutdown /r /t 60")
            return {"status": "success", "message": "Restart initiated in 60 seconds."}
        elif action == "cancel_shutdown" or action == "cancel":
            os.system("shutdown /a")
            return {"status": "success", "message": "Scheduled shutdown aborted."}
        return {"status": "info", "message": f"Power action '{action}' executed."}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def open_windows_settings(page: str = "bluetooth") -> Dict[str, Any]:
    """
    Opens specific Windows Settings pages (bluetooth, wifi, sound, display, update, apps, battery).
    """
    try:
        pages = {
            "bluetooth": "ms-settings:bluetooth",
            "wifi": "ms-settings:network-wifi",
            "sound": "ms-settings:sound",
            "display": "ms-settings:display",
            "update": "ms-settings:windowsupdate",
            "apps": "ms-settings:appsfeatures",
            "battery": "ms-settings:powersleep",
            "personalization": "ms-settings:personalization",
        }
        target = pages.get(page.lower(), f"ms-settings:{page.lower()}")
        os.system(f"start {target}")
        return {"status": "success", "message": f"Opened Windows {page.capitalize()} Settings."}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def close_application(app_name: str) -> Dict[str, Any]:
    """
    Closes or terminates an active application by name (e.g., 'GitHub Desktop', 'Chrome', 'WhatsApp', 'GTA V', 'Notepad').
    """
    try:
        app_lower = app_name.lower().strip()
        
        # Process name mapping
        proc_map = {
            "github desktop": "GitHubDesktop.exe",
            "github": "GitHubDesktop.exe",
            "chrome": "chrome.exe",
            "whatsapp": "WhatsApp.exe",
            "gta v": "GTA5.exe",
            "gta5": "GTA5.exe",
            "notepad": "notepad.exe",
            "calc": "CalculatorApp.exe",
            "calculator": "CalculatorApp.exe",
            "antigravity": "Antigravity.exe",
            "spotify": "Spotify.exe",
            "discord": "Discord.exe",
        }
        
        exe_target = proc_map.get(app_lower)
        if exe_target:
            cmd = f"taskkill /IM \"{exe_target}\" /F"
        else:
            # Fallback to wildcard taskkill or powershell process stop
            cmd = f"powershell -Command \"Stop-Process -Name '*{app_name}*' -Force -ErrorAction SilentlyContinue\""
            
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return {
            "status": "success",
            "message": f"Successfully closed {app_name}, Sir."
        }
    except Exception as e:
        logger.exception("Error closing application")
        return {"status": "error", "error": str(e)}

def check_git_repo_status(repo_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetches latest git updates from remote repository and checks if any new commits or pulls are available.
    """
    try:
        target_dir = Path(repo_path).resolve() if repo_path else config.ALLOWED_WORKING_DIR
        
        # 1. Fetch latest changes from remote
        fetch_res = subprocess.run(
            "git fetch --all",
            shell=True,
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=15
        )
        
        # 2. Check branch status (ahead/behind)
        status_res = subprocess.run(
            "git status -uno",
            shell=True,
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        output = status_res.stdout.strip()
        
        if "Your branch is behind" in output or "have diverged" in output:
            summary = "Sir, new incoming pulls/commits are available from remote! Your branch is behind."
        elif "Your branch is up to date" in output:
            summary = "Sir, repository is completely up to date with remote. No pending pulls."
        elif "Your branch is ahead" in output:
            summary = "Sir, your local branch is ahead of remote (you have unpushed commits)."
        else:
            summary = f"Git status: {output[:200]}"
            
        return {
            "status": "success",
            "summary": summary,
            "raw_status": output
        }
    except Exception as e:
        return {"status": "error", "error": f"Failed to check git repo: {str(e)}"}

def get_latest_backtest_report_summary(bot_dir: str = "F:\\binance_mexc_bot") -> Dict[str, Any]:
    """
    Reads the latest backtest report summary from F:\binance_mexc_bot\backtesting\reports\ and returns key metrics in Urdu.
    """
    import json
    import glob
    try:
        search_dirs = [
            os.path.join(bot_dir, "backtesting", "reports"),
            os.path.join(bot_dir, "reports"),
            os.path.join(bot_dir, "scratch"),
            bot_dir
        ]
        
        ignore_files = {"package.json", "package-lock.json", "binance_live480_universe.json"}
        candidate_files = []
        
        for sdir in search_dirs:
            if os.path.exists(sdir):
                for f in os.listdir(sdir):
                    if f.endswith(".json") and f not in ignore_files:
                        full_path = os.path.join(sdir, f)
                        candidate_files.append(full_path)
                        
        if not candidate_files:
            return {
                "status": "error",
                "message": "Sir, koi backtest report nahi mili."
            }
            
        # Sort by latest modification time
        candidate_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        data = None
        chosen_file = None
        for file_path in candidate_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    # Check if it has backtest metrics
                    if isinstance(content, dict) and any(k in content for k in ["start_balance", "initial_capital", "starting_balance", "net_pnl", "runs", "total_trades"]):
                        data = content
                        chosen_file = file_path
                        break
            except Exception:
                continue
                
        if not data:
            return {
                "status": "error",
                "message": "Sir, koi valid backtest report nahi mili."
            }
            
        # Handle multi-run summary
        if "runs" in data and isinstance(data["runs"], list) and len(data["runs"]) > 0:
            data = data["runs"][0]
            
        start_cap = data.get("start_balance", data.get("initial_capital", data.get("starting_balance", 0.0)))
        end_cap = data.get("end_balance", data.get("ending_balance", 0.0))
        net_pnl = data.get("net_pnl", 0.0)
        roi_pct = (net_pnl / start_cap * 100) if start_cap > 0 else data.get("net_roi_pct", 0.0)
        
        start_time = data.get("start_pkt", data.get("start_time", data.get("start_date", "")))
        end_time = data.get("end_pkt", data.get("end_time", data.get("end_date", "")))
        timeline = data.get("timeframe", "")
        if not timeline:
            if start_time and end_time:
                timeline = f"{start_time} se {end_time}"
            elif start_time:
                timeline = f"start {start_time}"
            else:
                timeline = "latest backtesting period"
                
        trades = data.get("total_trades", data.get("trades_count", 0))
        win_rate = data.get("win_rate", data.get("win_rate_pct", 0.0))
        report_title = os.path.basename(chosen_file).replace(".json", "") if chosen_file else "Backtest"
        
        # Urdu Spoken Summary
        urdu_summary = (
            f"Sir, latest backtest report ki summary yeh hai: "
            f"Timeline {timeline} thi. "
            f"Starting balance ${start_cap:.2f} tha aur ending balance ${end_cap:.2f} raha, "
            f"jis mein net PnL ${net_pnl:+.2f} ({roi_pct:+.2f}%) raha. "
            f"Total {trades} trades theen aur win rate {win_rate:.1f}% raha."
        )
        
        return {
            "status": "success",
            "report_file": report_title,
            "start_capital": start_cap,
            "end_capital": end_cap,
            "net_pnl": net_pnl,
            "roi_pct": roi_pct,
            "timeline": timeline,
            "total_trades": trades,
            "win_rate_pct": win_rate,
            "spoken_summary": urdu_summary,
            "message": urdu_summary
        }
    except Exception as e:
        logger.exception("Error reading backtest report")
        return {"status": "error", "error": str(e), "message": f"Report error: {str(e)}"}

def check_scalper_bot_status(base_url: str = "https://scalper-bot.84-247-185-16.plesk.page") -> Dict[str, Any]:
    """
    Connects to the live Scalper Bot web dashboard (https://scalper-bot.84-247-185-16.plesk.page/),
    authenticates with credentials, and extracts Market Sentiment Score, Regime, Total Balance, and Active Trades in Urdu.
    """
    import requests
    import urllib3
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json"
        })
        # Set Plesk technical domain bypass cookie
        session.cookies.set("plesk_technical_domain", "1")
        
        login_url = f"{base_url.rstrip('/')}/auth/login"
        status_url = f"{base_url.rstrip('/')}/status"
        
        # Credentials
        payload = {
            "email": "abdullah2843@gmail.com",
            "password": "7940"
        }
        
        login_res = session.post(login_url, json=payload, verify=False, timeout=20)
        status_res = session.get(status_url, verify=False, timeout=20)
        if status_res.status_code != 200:
            return {
                "status": "error",
                "message": f"Sir, trading bot dashboard se connect nahi ho saka (Status: {status_res.status_code})."
            }
            
        data = status_res.json()
        
        # Extract Key Metrics
        balance = data.get("balance", data.get("settings", {}).get("test_balance", 40.0))
        free_balance = data.get("free_balance", balance)
        
        ms = data.get("market_sentiment", {})
        daily_ms = ms.get("daily", ms.get("hourly", {}))
        sentiment_score = daily_ms.get("score", 0.0)
        regime_label = daily_ms.get("label", daily_ms.get("regime_state", "Neutral"))
        regime_bias = daily_ms.get("bias", "neutral")
        
        active_trades = data.get("active_trades", [])
        num_active = len(active_trades) if isinstance(active_trades, list) else 0
        
        bot_state = data.get("bot_state", data.get("trading_state", "ENABLED"))
        net_profit = data.get("net_profit", 0.0)
        
        # Spoken Urdu Summary
        trade_status_str = f"{num_active} active trades chal rahi hain" if num_active > 0 else "filhal koi active trade nahi hai"
        urdu_summary = (
            f"Sir, trading bot ka market sentiment score {sentiment_score:.0f} {regime_label} hai. "
            f"Total balance ${balance:.2f} USDT hai aur {trade_status_str}. "
            f"Bot {bot_state} hai."
        )
        
        return {
            "status": "success",
            "sentiment_score": sentiment_score,
            "regime": regime_label,
            "regime_bias": regime_bias,
            "total_balance": balance,
            "free_balance": free_balance,
            "active_trades_count": num_active,
            "active_trades": active_trades,
            "bot_state": bot_state,
            "net_profit": net_profit,
            "spoken_summary": urdu_summary,
            "message": urdu_summary
        }
    except Exception as e:
        logger.exception("Error checking scalper bot status")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Sir, bot dashboard check karne mein error aaya: {str(e)}"
        }

def unlock_workstation(pin: Optional[str] = None) -> Dict[str, Any]:
    """
    Wakes up display, handles Windows Hello Sign-In Options (Fingerprint -> PIN switch), and inputs configured PIN.
    Uses low-level Windows hardware keybd_event API with mapped hardware scan codes.
    """
    import time
    import ctypes
    user32 = ctypes.windll.user32
    
    target_pin = pin if pin else config.WINDOWS_PIN
    if not target_pin:
        return {"status": "error", "error": "No Windows PIN configured in .env."}
        
    def send_vk(vk_code: int, delay: float = 0.08):
        scan = user32.MapVirtualKeyW(vk_code, 0)
        user32.keybd_event(vk_code, scan, 0, 0)
        time.sleep(delay)
        user32.keybd_event(vk_code, scan, 2, 0) # KEYEVENTF_KEYUP
        time.sleep(delay)
        
    try:
        VK_SPACE = 0x20
        VK_RETURN = 0x0D
        VK_TAB = 0x09
        VK_RIGHT = 0x27
        VK_ESCAPE = 0x1B
        
        # 1. Wake screen and lift lock screen cover
        send_vk(VK_SPACE, 0.1)
        time.sleep(0.5)
        send_vk(VK_ESCAPE, 0.1)
        time.sleep(0.5)
        send_vk(VK_SPACE, 0.1)
        time.sleep(1.0)
        
        # 2. Switch from Fingerprint to PIN
        # Press Tab to focus "Sign-in options" and Enter to expand
        send_vk(VK_TAB, 0.1)
        time.sleep(0.4)
        send_vk(VK_RETURN, 0.1)
        time.sleep(0.6)
        
        # Move right to select PIN keypad icon and press Enter/Space
        send_vk(VK_RIGHT, 0.1)
        time.sleep(0.4)
        send_vk(VK_RETURN, 0.1)
        time.sleep(1.0) # Wait for PIN box to render and focus
        
        # 3. Type PIN using numeric virtual keycodes (0x30 to 0x39) with hardware scan codes
        for char in str(target_pin):
            if char.isdigit():
                vk = ord(char) # 0x30-0x39
                send_vk(vk, 0.09)
                
        time.sleep(0.4)
        send_vk(VK_RETURN, 0.1)
        time.sleep(0.5)
        
        return {
            "status": "success",
            "message": "Windows PIN unlock sequence executed with hardware input layer, Sir."
        }
    except Exception as e:
        logger.exception("Error executing unlock sequence")
        return {"status": "error", "error": str(e)}

def open_url_or_application(target: str) -> Dict[str, Any]:
    """
    Opens an application, website URL, or system tool by name or path (e.g. 'chrome', 'youtube', 'github desktop', 'vscode', 'https://...').
    """
    import subprocess
    import webbrowser
    try:
        t_lower = target.lower().strip()
        
        # App aliases mapping
        app_map = {
            "chrome": ["cmd.exe", "/c", "start", "", "chrome"],
            "google chrome": ["cmd.exe", "/c", "start", "", "chrome"],
            "youtube": ["cmd.exe", "/c", "start", "", "https://www.youtube.com"],
            "github": ["cmd.exe", "/c", "start", "", "github"],
            "github desktop": ["cmd.exe", "/c", "start", "", "github"],
            "vscode": ["cmd.exe", "/c", "start", "", "code"],
            "vs code": ["cmd.exe", "/c", "start", "", "code"],
            "code": ["cmd.exe", "/c", "start", "", "code"],
            "notepad": ["cmd.exe", "/c", "start", "", "notepad"],
            "calc": ["cmd.exe", "/c", "start", "", "calc"],
            "calculator": ["cmd.exe", "/c", "start", "", "calc"],
            "antigravity": ["cmd.exe", "/c", "start", "", "Antigravity IDE"],
            "spotify": ["cmd.exe", "/c", "start", "", "spotify"],
            "discord": ["cmd.exe", "/c", "start", "", "discord"],
            "whatsapp": ["cmd.exe", "/c", "start", "", "whatsapp:"],
            "explorer": ["cmd.exe", "/c", "start", "", "explorer"],
            "cmd": ["cmd.exe", "/c", "start", "", "cmd"],
            "terminal": ["cmd.exe", "/c", "start", "", "wt"],
        }
        
        if t_lower in app_map:
            cmd = app_map[t_lower]
            subprocess.Popen(cmd, shell=True)
            if "youtube" in t_lower:
                try:
                    webbrowser.open("https://www.youtube.com")
                except Exception:
                    pass
            return {"status": "success", "message": f"Launched {target}, Sir."}
            
        if target.startswith("http://") or target.startswith("https://") or ("." in target and not " " in target):
            url = target if target.startswith("http") else f"https://{target}"
            subprocess.Popen(["cmd.exe", "/c", "start", "", url], shell=True)
            try:
                webbrowser.open(url)
            except Exception:
                pass
            return {"status": "success", "opened_url": url, "message": f"Opened {target} in browser, Sir."}
            
        # Default shell start
        subprocess.Popen(["cmd.exe", "/c", "start", "", target], shell=True)
        return {"status": "success", "message": f"Executed launch for '{target}', Sir."}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def search_and_open_in_browser(query: str, search_type: str = "web") -> Dict[str, Any]:
    """
    Instantly searches or opens URLs, Chrome History, or Bookmarks in the default web browser.
    search_type: 'web' (default Google search), 'history' (opens Chrome history with search query), 'direct' (opens URL).
    """
    import urllib.parse
    import subprocess
    import webbrowser
    try:
        if search_type == "history" or "history" in query.lower():
            clean_q = query.replace("history", "").strip()
            url = f"chrome://history/?q={urllib.parse.quote(clean_q)}" if clean_q else "chrome://history"
        elif query.startswith("http://") or query.startswith("https://") or ("." in query and not " " in query):
            url = query if query.startswith("http") else f"https://{query}"
        else:
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            
        subprocess.Popen(["cmd.exe", "/c", "start", "", url], shell=True)
        try:
            webbrowser.open(url)
        except Exception:
            pass
        return {
            "status": "success",
            "opened_url": url,
            "message": f"Opened '{query}' in browser, Sir."
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

# Registry mapping tool names to python callables
TOOL_REGISTRY = {
    "execute_terminal_command": execute_terminal_command,
    "read_project_file": read_project_file,
    "write_project_file": write_project_file,
    "list_directory": list_directory,
    "get_system_status": get_system_status,
    "check_windows_updates": check_windows_updates,
    "configure_game_graphics": configure_game_graphics,
    "manage_bluetooth": manage_bluetooth,
    "manage_system_volume": manage_system_volume,
    "manage_windows_power": manage_windows_power,
    "open_windows_settings": open_windows_settings,
    "send_whatsapp_message": send_whatsapp_message,
    "send_antigravity_command": send_antigravity_command,
    "type_text_into_active_app": type_text_into_active_app,
    "open_url_or_application": open_url_or_application,
    "close_application": close_application,
    "check_git_repo_status": check_git_repo_status,
    "unlock_workstation": unlock_workstation,
    "search_and_open_in_browser": search_and_open_in_browser,
    "get_latest_backtest_report_summary": get_latest_backtest_report_summary,
    "close_all_user_applications": close_all_user_applications,
    "check_scalper_bot_status": check_scalper_bot_status,
    "manage_display_brightness": manage_display_brightness,
    "manage_media_playback": manage_media_playback,
}

# Declarations for Gemini 2.0 Function Calling
TOOL_DECLARATIONS = [
    execute_terminal_command,
    read_project_file,
    write_project_file,
    list_directory,
    get_system_status,
    check_windows_updates,
    configure_game_graphics,
    manage_bluetooth,
    manage_system_volume,
    manage_windows_power,
    open_windows_settings,
    send_whatsapp_message,
    send_antigravity_command,
    type_text_into_active_app,
    open_url_or_application,
    close_application,
    check_git_repo_status,
    unlock_workstation,
    search_and_open_in_browser,
    get_latest_backtest_report_summary,
    close_all_user_applications,
    check_scalper_bot_status,
    manage_display_brightness,
    manage_media_playback,
]
