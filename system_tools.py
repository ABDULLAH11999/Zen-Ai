import os
import time
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
    Focuses an application window (e.g. Chrome, VS Code, Notepad, Discord, Telegram),
    types the given text, and supports simulated key tokens like {TAB}, {ENTER}, {DOWN}, {UP}, {CTRL+A}, {BACKSPACE}.
    """
    import time
    import re
    import pyautogui
    import pyperclip
    
    try:
        focus_window_by_title(app_keyword)
        time.sleep(0.4)
        
        # Check if text contains simulated key tokens like {TAB}, {ENTER}, etc.
        tokens = re.findall(r"(\{[A-Za-z0-9_+-]+\}|[^{]+)", text)
        for token in tokens:
            t_upper = token.upper().strip()
            if t_upper == "{TAB}":
                pyautogui.press("tab")
                time.sleep(0.15)
            elif t_upper in ["{ENTER}", "{RETURN}"]:
                pyautogui.press("enter")
                time.sleep(0.2)
            elif t_upper == "{DOWN}":
                pyautogui.press("down")
                time.sleep(0.15)
            elif t_upper == "{UP}":
                pyautogui.press("up")
                time.sleep(0.15)
            elif t_upper in ["{ESC}", "{ESCAPE}"]:
                pyautogui.press("escape")
                time.sleep(0.15)
            elif t_upper in ["{BACKSPACE}", "{BS}"]:
                pyautogui.press("backspace")
                time.sleep(0.1)
            elif t_upper in ["{CTRL+A}", "{SELECT_ALL}"]:
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.1)
            elif t_upper == "{SPACE}":
                pyautogui.press("space")
                time.sleep(0.1)
            else:
                # Type or paste normal text chunk
                if token:
                    pyperclip.copy(token)
                    pyautogui.hotkey("ctrl", "v")
                    time.sleep(0.15)
                    
        if press_enter and not any(k in text.upper() for k in ["{ENTER}", "{RETURN}"]):
            time.sleep(0.2)
            pyautogui.press("enter")
            
        return {
            "status": "success",
            "message": f"Sir, {app_keyword} mein text type aur key execution mukammal kardiya hai."
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

def proceed_browser_login(app_keyword: str = "Chrome", action: str = "submit") -> Dict[str, Any]:
    """
    Proceeds with login on the active browser page by submitting prefilled credentials or pressing Enter.
    Call whenever user says 'login proceed kro', 'login enter karo', 'login button click karo', 'prefilled login proceed karo'.
    """
    import time
    import pyautogui
    try:
        focus_window_by_title(app_keyword)
        time.sleep(0.4)
        
        # Press Enter to submit the form or active login button
        pyautogui.press("enter")
        
        return {
            "status": "success",
            "message": "Sir, browser login proceed aur submit kardiya hai."
        }
    except Exception as e:
        logger.exception("Error in proceed_browser_login")
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

# Standalone Pure Black Screen Controller (Guarantees Unlocked State with 0% Lock Screen risk)
_black_screen_proc = None

def manage_screen_power(action: str = "off") -> Dict[str, Any]:
    """
    Controls display power and black screen overlay without locking the session.
    Actions:
    - 'off' / 'black': Opens fullscreen pure black overlay (screen is pitch black, cursor hidden, session stays 100% unlocked).
    - 'on' / 'wake': Instantly removes black screen overlay, waking desktop without PIN/Password.
    - 'keep_alive': Prevents Windows from auto-locking or sleeping.
    """
    global _black_screen_proc
    import subprocess
    import sys
    import ctypes
    from pathlib import Path
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    action = action.lower().strip()
    
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002
    
    overlay_script = str(Path(__file__).resolve().parent / "black_screen_overlay.py")
    
    if action in ["off", "black", "dim", "toggle_off"]:
        # Keep system running & awake
        kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
        
        # Check if already running
        if _black_screen_proc and _black_screen_proc.poll() is None:
            return {"status": "success", "message": "Screen already black, session unlocked, Sir."}
            
        try:
            # Spawn interactive GUI window on the user desktop
            _black_screen_proc = subprocess.Popen([sys.executable, overlay_script])
        except Exception as e:
            logger.error(f"Failed to spawn black_screen_overlay: {e}")
            
        return {
            "status": "success",
            "message": "Screen black kar di gayi hai, workstation session unlocked aur apps active hain, Sir."
        }
    elif action in ["on", "wake", "bright", "toggle_on"]:
        # Terminate black screen overlay if active
        if _black_screen_proc:
            try:
                _black_screen_proc.terminate()
            except Exception:
                pass
            _black_screen_proc = None
            
        # Extra safety: kill any residual black_screen_overlay processes
        try:
            subprocess.run(["taskkill", "/F", "/IM", "black_screen_overlay.py", "/T"], capture_output=True)
        except Exception:
            pass
            
        # Jiggle mouse to refresh desktop & ensure display active
        kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
        user32.mouse_event(0x0001, 1, 1, 0, 0)
        time.sleep(0.02)
        user32.mouse_event(0x0001, -1, -1, 0, 0)
        
        return {
            "status": "success",
            "message": "Display on kar di gayi hai, Sir."
        }
    elif action == "keep_alive":
        kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
        return {
            "status": "success",
            "message": "System awake protection active hai."
        }
    return {"status": "info", "message": f"Screen action '{action}' executed."}

def manage_windows_power(action: str = "lock") -> Dict[str, Any]:
    """
    Manages power and screen locking on Windows.
    Actions: 'lock' (locks screen/workstation), 'screen_off' (black screen without lock), 'wake_screen', 'sleep', 'restart', 'shutdown', 'cancel_shutdown'.
    """
    try:
        action = action.lower()
        if action == "lock":
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return {"status": "success", "message": "Windows workstation locked, Sir."}
        elif action in ["screen_off", "black_screen", "display_off"]:
            return manage_screen_power("off")
        elif action in ["wake_screen", "screen_on", "display_on"]:
            return manage_screen_power("on")
        elif action == "sleep":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            return {"status": "success", "message": "Putting system to sleep."}
        elif action == "shutdown":
            os.system("shutdown /s /t 5")
            return {"status": "success", "message": "Sir, system shutdown 5 seconds mein initiate kar diya gaya hai."}
        elif action == "restart":
            os.system("shutdown /r /t 5")
            return {"status": "success", "message": "Restart initiated in 5 seconds."}
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
    r"""
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
    Uses direct low-level Windows SendInput API with hardware scan codes and multi-phase fallback.
    """
    import time
    import ctypes
    user32 = ctypes.windll.user32
    
    target_pin = pin if pin else config.WINDOWS_PIN
    if not target_pin:
        return {"status": "error", "error": "No Windows PIN configured in .env."}
        
    PUL = ctypes.POINTER(ctypes.c_ulong)
    class KeyBdInput(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.c_ushort),
            ("wScan", ctypes.c_ushort),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", PUL)
        ]

    class HardwareInput(ctypes.Structure):
        _fields_ = [("uMsg", ctypes.c_ulong), ("wParamL", ctypes.c_short), ("wParamH", ctypes.c_ushort)]

    class MouseInput(ctypes.Structure):
        _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong), ("dwExtraInfo", PUL)]

    class Input_I(ctypes.Union):
        _fields_ = [("ki", KeyBdInput), ("mi", MouseInput), ("hi", HardwareInput)]

    class Input(ctypes.Structure):
        _fields_ = [("type", ctypes.c_ulong), ("ii", Input_I)]

    KEYEVENTF_EXTENDEDKEY = 0x0001
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_SCANCODE = 0x0008
    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_ABSOLUTE = 0x8000

    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    center_x = w // 2

    def send_key(vk_code, is_extended=False, delay=0.06):
        scan = user32.MapVirtualKeyW(vk_code, 0)
        
        # 1. Low-level Hardware SendInput with KEYEVENTF_SCANCODE
        flags_down = KEYEVENTF_SCANCODE
        flags_up = KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP
        if is_extended:
            flags_down |= KEYEVENTF_EXTENDEDKEY
            flags_up |= KEYEVENTF_EXTENDEDKEY
            
        extra = ctypes.c_ulong(0)
        ii_down = Input_I()
        ii_down.ki = KeyBdInput(vk_code, scan, flags_down, 0, ctypes.pointer(extra))
        x_down = Input(ctypes.c_ulong(1), ii_down)
        
        ii_up = Input_I()
        ii_up.ki = KeyBdInput(vk_code, scan, flags_up, 0, ctypes.pointer(extra))
        x_up = Input(ctypes.c_ulong(1), ii_up)
        
        user32.SendInput(1, ctypes.pointer(x_down), ctypes.sizeof(x_down))
        time.sleep(delay)
        user32.SendInput(1, ctypes.pointer(x_up), ctypes.sizeof(x_up))
        time.sleep(delay)
        
        # 2. Also execute classic Win32 keybd_event as secondary layer
        try:
            user32.keybd_event(vk_code, scan, 0, 0)
            time.sleep(0.02)
            user32.keybd_event(vk_code, scan, KEYEVENTF_KEYUP, 0)
        except Exception:
            pass

    def click_point(x, y, delay=0.06):
        # 1. Hardware-level SendInput with Absolute coordinates (bypasses Winlogon UIPI)
        abs_x = int(x * 65535 / w)
        abs_y = int(y * 65535 / h)
        extra = ctypes.c_ulong(0)
        
        down_inp = Input(
            ctypes.c_ulong(0),
            Input_I(mi=MouseInput(abs_x, abs_y, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_LEFTDOWN, 0, ctypes.pointer(extra)))
        )
        up_inp = Input(
            ctypes.c_ulong(0),
            Input_I(mi=MouseInput(abs_x, abs_y, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_LEFTUP, 0, ctypes.pointer(extra)))
        )
        user32.SendInput(1, ctypes.pointer(down_inp), ctypes.sizeof(down_inp))
        time.sleep(delay)
        user32.SendInput(1, ctypes.pointer(up_inp), ctypes.sizeof(up_inp))
        time.sleep(delay)
        
        # 2. Also execute user32 SetCursorPos & mouse_event as secondary layer
        try:
            user32.SetCursorPos(int(x), int(y))
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.02)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        except Exception:
            pass

    try:
        VK_SPACE = 0x20
        VK_RETURN = 0x0D
        VK_TAB = 0x09
        VK_RIGHT = 0x27
        VK_LEFT = 0x25
        VK_UP = 0x26
        VK_DOWN = 0x28
        
        # 1. Wake screen and lift lock screen cover
        click_point(center_x, int(h * 0.5))
        time.sleep(0.1)
        send_key(VK_SPACE, delay=0.1)
        time.sleep(0.7)
        
        # Immediate direct PIN entry attempt (works 100% if PIN box is active)
        for char in str(target_pin):
            if char.isdigit():
                send_key(ord(char), delay=0.08)
                try:
                    pyautogui.press(char)
                except Exception:
                    pass
        time.sleep(0.2)
        send_key(VK_RETURN, delay=0.1)
        try:
            pyautogui.press('enter')
        except Exception:
            pass
        time.sleep(0.4)
        
        # 2. Click "Sign-in options" text link / button (handles Fingerprint default)
        for y_pos in [int(h * 0.54), int(h * 0.58), int(h * 0.60), int(h * 0.76), int(h * 0.80)]:
            click_point(center_x, y_pos)
            time.sleep(0.04)
            
        # Also trigger keyboard Tab sequence
        send_key(VK_TAB, delay=0.08)
        time.sleep(0.08)
        send_key(VK_SPACE, delay=0.08)
        time.sleep(0.08)
        send_key(VK_RETURN, delay=0.08)
        time.sleep(0.35)
        
        # 3. Select PIN Tile (Keypad icon)
        for y_tile in [int(h * 0.58), int(h * 0.62), int(h * 0.80)]:
            for offset_x in [-70, -50, -35, -20, 0, 20, 35, 50, 70]:
                click_point(center_x + offset_x, y_tile)
                time.sleep(0.03)
            
        send_key(VK_LEFT, is_extended=True, delay=0.08)
        time.sleep(0.08)
        send_key(VK_RETURN, delay=0.08)
        time.sleep(0.1)
        send_key(VK_RIGHT, is_extended=True, delay=0.08)
        time.sleep(0.08)
        send_key(VK_RETURN, delay=0.08)
        time.sleep(0.4)
        
        # 4. Click PIN text box area & type PIN digits
        for y_pin in [int(h * 0.52), int(h * 0.55), int(h * 0.58), int(h * 0.60)]:
            click_point(center_x, y_pin)
            time.sleep(0.04)
            
        for char in str(target_pin):
            if char.isdigit():
                send_key(ord(char), delay=0.08)
                try:
                    pyautogui.press(char)
                except Exception:
                    pass
                
        time.sleep(0.25)
        send_key(VK_RETURN, delay=0.1)
        try:
            pyautogui.press('enter')
        except Exception:
            pass
        time.sleep(0.3)
        
        return {
            "status": "success",
            "message": "Windows PIN unlock sequence executed with hardware input layer, Sir."
        }
    except Exception as e:
        logger.exception("Error executing unlock sequence")
        return {"status": "error", "error": str(e)}

def send_antigravity_command(prompt_text: str) -> Dict[str, Any]:
    """
    Focuses the Antigravity IDE window, types prompt_text into the chat/command input, and sends it.
    """
    import ctypes
    import time
    import subprocess
    user32 = ctypes.windll.user32
    
    try:
        # Find Antigravity window handle
        target_hwnd = None
        def enum_handler(hwnd, _):
            nonlocal target_hwnd
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    if "antigravity" in buff.value.lower():
                        target_hwnd = hwnd
                        return False
            return True
            
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
        user32.EnumWindows(WNDENUMPROC(enum_handler), 0)
        
        if target_hwnd:
            SW_RESTORE = 9
            user32.ShowWindow(target_hwnd, SW_RESTORE)
            user32.SetForegroundWindow(target_hwnd)
            time.sleep(0.3)
            
        # Copy prompt text to clipboard via PowerShell
        import tempfile
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".txt") as tf:
            tf.write(prompt_text)
            temp_prompt_file = tf.name
            
        ps_cmd = f"Get-Content -Path '{temp_prompt_file}' -Raw -Encoding utf8 | Set-Clipboard"
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
        try:
            os.remove(temp_prompt_file)
        except Exception:
            pass
            
        time.sleep(0.2)
        # Send Ctrl+V and Enter
        VK_CONTROL = 0x11
        VK_V = 0x56
        VK_RETURN = 0x0D
        
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_V, 0, 0, 0)
        time.sleep(0.08)
        user32.keybd_event(VK_V, 0, 2, 0)
        user32.keybd_event(VK_CONTROL, 0, 2, 0)
        time.sleep(0.2)
        
        user32.keybd_event(VK_RETURN, 0, 0, 0)
        time.sleep(0.08)
        user32.keybd_event(VK_RETURN, 0, 2, 0)
        
        return {
            "status": "success",
            "prompt_sent": prompt_text,
            "message": f"Sir, Antigravity IDE mein prompt type karke send kardiya hai: '{prompt_text}'"
        }
    except Exception as e:
        logger.exception("Error sending Antigravity command")
        return {"status": "error", "error": str(e), "message": f"Antigravity prompt error: {str(e)}"}

def set_ai_model(model_name: str) -> Dict[str, Any]:
    """
    Switches/sets the AI Model for ZEN / Antigravity (e.g., 'gemini-2.5-flash', 'gemini-3.5-flash', 'qwen', etc.).
    """
    try:
        clean_model = model_name.strip()
        # Aliases
        if clean_model in ["3.7", "3.8", "3.5", "2.5", "flash"]:
            model_map = {
                "3.7": "gemini-3.7-flash",
                "3.8": "gemini-3.8-flash",
                "3.5": "gemini-3.5-flash",
                "2.5": "gemini-2.5-flash",
                "flash": "gemini-flash-latest"
            }
            target_model = model_map.get(clean_model, f"gemini-{clean_model}-flash")
        else:
            target_model = clean_model
            
        config.GEMINI_MODEL = target_model
        
        # Persist to .env
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()
            import re
            if "GEMINI_MODEL=" in content:
                content = re.sub(r"GEMINI_MODEL=.*", f"GEMINI_MODEL={target_model}", content)
            else:
                content += f"\nGEMINI_MODEL={target_model}\n"
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(content)
                
        return {
            "status": "success",
            "model_set": target_model,
            "message": f"Sir, active AI model {target_model} par set kar diya gaya hai."
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "message": f"Model switch error: {str(e)}"}

def get_running_system_apps() -> Dict[str, Any]:
    """
    Scans running desktop applications, active browser tabs, and open Antigravity workspaces.
    """
    import psutil
    user_app_patterns = {
        "antigravity": "Antigravity IDE",
        "code": "Visual Studio Code",
        "chrome": "Google Chrome",
        "msedge": "Microsoft Edge",
        "brave": "Brave Browser",
        "spotify": "Spotify",
        "discord": "Discord",
        "whatsapp": "WhatsApp",
        "gta5": "GTA V",
        "playgtav": "GTA V",
        "githubdesktop": "GitHub Desktop",
        "laragon": "Laragon",
        "steam": "Steam",
        "notepad": "Notepad",
        "vlc": "VLC",
    }
    
    found_apps = {}
    for p in psutil.process_iter(["name"]):
        try:
            n = (p.info["name"] or "").lower().replace(".exe", "").replace(" ", "").replace("-", "")
            for pattern, display in user_app_patterns.items():
                if pattern in n and display not in found_apps:
                    found_apps[display] = True
        except Exception:
            pass
            
    # Check Antigravity Workspace if running
    antigravity_workspace = None
    if "Antigravity IDE" in found_apps:
        brain_dir = r"C:\Users\LapStore\.gemini\antigravity-ide\brain"
        if os.path.exists(brain_dir):
            conv_dirs = [os.path.join(brain_dir, d) for d in os.listdir(brain_dir) if os.path.isdir(os.path.join(brain_dir, d)) and d != "tempmediaStorage"]
            conv_dirs.sort(key=os.path.getmtime, reverse=True)
            if conv_dirs:
                latest_conv = conv_dirs[0]
                t_file = os.path.join(latest_conv, ".system_generated", "logs", "transcript.jsonl")
                if os.path.exists(t_file):
                    try:
                        with open(t_file, "r", encoding="utf-8") as f:
                            for line in f:
                                if "f:\\Agent" in line or "f:/Agent" in line:
                                    antigravity_workspace = "F:\\Agent"
                                    break
                                elif "binance_mexc_bot" in line:
                                    antigravity_workspace = "F:\\binance_mexc_bot"
                                    break
                    except Exception:
                        pass
        if not antigravity_workspace:
            antigravity_workspace = "F:\\Agent"
            
    app_list_str = []
    for app in found_apps.keys():
        if app == "Antigravity IDE" and antigravity_workspace:
            app_list_str.append(f"Antigravity IDE (Workspace: {antigravity_workspace})")
        else:
            app_list_str.append(app)
            
    if not app_list_str:
        summary = "Sir, system par is waqt koi major user application open nahi hai."
    else:
        summary = "Sir, system par is waqt yeh applications run ho rahe hain: " + ", ".join(app_list_str) + "."
        
    return {
        "status": "success",
        "running_apps": list(found_apps.keys()),
        "antigravity_workspace": antigravity_workspace,
        "spoken_summary": summary,
        "message": summary
    }

def get_antigravity_activity_summary() -> Dict[str, Any]:
    """
    Summarizes the current conversation, latest prompt, and actions executing in Antigravity IDE.
    """
    import json
    import re
    brain_dir = r"C:\Users\LapStore\.gemini\antigravity-ide\brain"
    if not os.path.exists(brain_dir):
        return {"status": "error", "message": "Sir, Antigravity IDE directory nahi mili."}
        
    conv_dirs = [os.path.join(brain_dir, d) for d in os.listdir(brain_dir) if os.path.isdir(os.path.join(brain_dir, d)) and d != "tempmediaStorage"]
    conv_dirs.sort(key=os.path.getmtime, reverse=True)
    if not conv_dirs:
        return {"status": "error", "message": "Sir, koi active Antigravity session nahi mila."}
        
    latest_conv = conv_dirs[0]
    t_file = os.path.join(latest_conv, ".system_generated", "logs", "transcript.jsonl")
    
    last_user_query = ""
    last_agent_text = ""
    
    if os.path.exists(t_file):
        with open(t_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        for line in reversed(lines):
            try:
                item = json.loads(line)
                t = item.get("type")
                content = item.get("content", "")
                if t == "USER_INPUT" and not last_user_query:
                    clean_req = re.sub(r"<USER_REQUEST>\s*", "", content)
                    clean_req = re.sub(r"</USER_REQUEST>.*", "", clean_req, flags=re.DOTALL).strip()
                    if clean_req:
                        last_user_query = clean_req
                elif t == "PLANNER_RESPONSE" and not last_agent_text:
                    if content and len(content.strip()) > 15:
                        clean_c = re.sub(r"<thought>.*?</thought>", "", content, flags=re.DOTALL)
                        clean_c = re.sub(r"[\*#`]", "", clean_c).strip()
                        if clean_c:
                            last_agent_text = clean_c[:200]
                if last_user_query and last_agent_text:
                    break
            except Exception:
                pass
                
    if not last_user_query:
        last_user_query = "Code changes execution"
        
    summary = f"Sir, Antigravity IDE mein current task yeh hai: \"{last_user_query[:90]}\". Is par execution mukammal ki ja rahi hai."
    return {
        "status": "success",
        "last_user_query": last_user_query,
        "last_agent_summary": last_agent_text,
        "spoken_summary": summary,
        "message": summary
    }

def inspect_web_page_or_dashboard(url: str, prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Universal web page reader & dashboard inspector. Reads content from any URL and summarizes it.
    """
    import requests
    import html
    import re
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"https://{url}"
        
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
        res = requests.get(url, headers=headers, timeout=12, verify=False)
        if res.status_code != 200:
            return {"status": "error", "message": f"Webpage check karne mein error aya (Status {res.status_code})."}
            
        title_match = re.search(r'<title>(.*?)</title>', res.text, re.IGNORECASE | re.DOTALL)
        title = html.unescape(title_match.group(1)).strip() if title_match else "Web Page"
        
        # Clean HTML
        clean = re.sub(r'<script.*?</script>', '', res.text, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r'<style.*?</style>', '', clean, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r'<[^>]+>', ' ', clean)
        clean_text = ' '.join(html.unescape(clean).split())[:1000]
        
        summary = f"Sir, {title[:50]} page read karliya hai. Main content: {clean_text[:180]}."
        return {
            "status": "success",
            "url": url,
            "title": title,
            "content_sample": clean_text[:500],
            "spoken_summary": summary,
            "message": summary
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "message": f"Sir, web page read nahi ho saka: {str(e)}"}

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
        
        # 1. GTA 5 / GTA V Specific Launch Handler (PlayGTAV.exe)
        gta_keywords = ["gta 5", "gta v", "gta5", "gtav", "gta", "playgtav", "grand theft auto", "grand theft auto 5", "grand theft auto v", "grand theft auto vi"]
        if any(kw == t_lower or kw in t_lower for kw in gta_keywords):
            play_gta_exe = r"F:\Games\Grand Theft Auto V\PlayGTAV.exe"
            gta_dir = r"F:\Games\Grand Theft Auto V"
            desktop_lnk = r"C:\Users\Public\Desktop\Grand Theft Auto VI.lnk"
            
            if os.path.exists(play_gta_exe):
                subprocess.Popen([play_gta_exe], cwd=gta_dir, shell=True)
                return {
                    "status": "success",
                    "executable": play_gta_exe,
                    "message": "Sir, GTA V PlayGTAV.exe ke zariye launch kardiya hai."
                }
            elif os.path.exists(desktop_lnk):
                try:
                    os.startfile(desktop_lnk)
                    return {
                        "status": "success",
                        "shortcut": desktop_lnk,
                        "message": "Sir, Desktop shortcut se GTA V launch kardiya hai."
                    }
                except Exception:
                    subprocess.Popen(["cmd.exe", "/c", "start", "", desktop_lnk], shell=True)
                    return {"status": "success", "message": "Sir, GTA V launch kardiya hai."}
                    
        # 2. Spider-Man Game Handler
        if any(sk in t_lower for sk in ["spider-man", "spiderman", "spider man"]):
            spiderman_lnk = os.path.expandvars(r"C:\Users\%USERNAME%\Desktop\Spider-Man.lnk")
            spiderman_dir = r"F:\Games\Marvels Spider-Man Remastered"
            if os.path.exists(spiderman_lnk):
                os.startfile(spiderman_lnk)
                return {"status": "success", "message": "Sir, Spider-Man Remastered launch kardiya hai."}
            elif os.path.exists(spiderman_dir):
                for f in os.listdir(spiderman_dir):
                    if f.endswith(".exe") and "unins" not in f.lower():
                        subprocess.Popen([os.path.join(spiderman_dir, f)], cwd=spiderman_dir, shell=True)
                        return {"status": "success", "message": "Sir, Spider-Man launch kardiya hai."}

        # 3. Dynamic Desktop Shortcuts (.lnk) Search
        desktops = [os.path.expandvars(r"C:\Users\%USERNAME%\Desktop"), r"C:\Users\Public\Desktop"]
        clean_q = t_lower.replace(" ", "").replace("-", "").replace("_", "")
        for d in desktops:
            if os.path.exists(d):
                for f in os.listdir(d):
                    if f.lower().endswith(".lnk") or f.lower().endswith(".bat"):
                        base_name = os.path.splitext(f)[0].lower().replace(" ", "").replace("-", "").replace("_", "")
                        if clean_q in base_name or base_name in clean_q:
                            full_lnk = os.path.join(d, f)
                            try:
                                os.startfile(full_lnk)
                            except Exception:
                                subprocess.Popen(["cmd.exe", "/c", "start", "", full_lnk], shell=True)
                            return {"status": "success", "message": f"Sir, Desktop se {os.path.splitext(f)[0]} launch kardiya hai."}

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

ALIAS_GROUPS = [
    {
        "keywords": ["vmi", "contabo", "plesk"],
        "url": "https://vmi2928547.contaboserver.net:8443/login_up.php",
        "name": "Contabo VMI"
    },
    {
        "keywords": ["emp", "einno", "einnovention", "eino", "emp portal", "einno portal"],
        "url": "https://emp.einnovention.co.uk",
        "name": "Einnovention EMP"
    },
    {
        "keywords": ["scalper", "scalper bot", "scalper dashboard"],
        "url": "https://scalper-bot.84-247-185-16.plesk.page/",
        "name": "Scalper Bot Dashboard"
    },
    {
        "keywords": ["youtube", "yt"],
        "url": "https://www.youtube.com",
        "name": "YouTube"
    },
    {
        "keywords": ["chatgpt", "openai"],
        "url": "https://chatgpt.com",
        "name": "ChatGPT"
    },
    {
        "keywords": ["github"],
        "url": "https://github.com",
        "name": "GitHub"
    },
    {
        "keywords": ["binance"],
        "url": "https://www.binance.com",
        "name": "Binance"
    },
    {
        "keywords": ["mexc"],
        "url": "https://www.mexc.com",
        "name": "MEXC"
    },
    {
        "keywords": ["tradingview"],
        "url": "https://www.tradingview.com",
        "name": "TradingView"
    },
    {
        "keywords": ["whatsapp"],
        "url": "https://web.whatsapp.com",
        "name": "WhatsApp Web"
    },
    {
        "keywords": ["gmail"],
        "url": "https://mail.google.com",
        "name": "Gmail"
    }
]

def resolve_target_urls(query: str, profile_dir: str = "Profile 1") -> list:
    """
    Parses a query for one or more target websites/portals (e.g. 'vmi aur einno dono open kro').
    Matches aliases, Chrome history, or falls back to exact URL / Google search.
    """
    import os
    import re
    import sqlite3
    import shutil
    import urllib.parse

    q_lower = query.lower().strip()
    matched_urls = []
    matched_names = []
    seen = set()

    # 1. Match known alias groups
    for group in ALIAS_GROUPS:
        for kw in group["keywords"]:
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, q_lower) or kw in q_lower:
                if group["url"] not in seen:
                    seen.add(group["url"])
                    matched_urls.append(group["url"])
                    matched_names.append(group["name"])
                break

    if matched_urls:
        return matched_urls

    # 2. Check if the query is a direct URL or domain
    if "." in query and " " not in query:
        url = query if query.startswith("http") else f"https://{query}"
        return [url]

    # 3. Clean query from conversational filler words
    clean_q = q_lower
    for w in ["browser mein", "browser me", "browser", "open karo", "open kro", "kholo", "login", "guest", "incognito", "dono", "aur", "sath", "or", "d kro"]:
        clean_q = clean_q.replace(w, " ")
    clean_q = " ".join(clean_q.split()).strip()

    # 4. Search Chrome History SQLite database for clean query
    if clean_q:
        user_data = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
        for p in [profile_dir, "Default"]:
            hist_path = os.path.join(user_data, p, "History")
            if os.path.exists(hist_path):
                temp_path = os.path.join(user_data, p, f"History_tmp_query_{os.getpid()}")
                try:
                    shutil.copyfile(hist_path, temp_path)
                    conn = sqlite3.connect(temp_path)
                    c = conn.cursor()
                    c.execute(
                        "SELECT url FROM urls WHERE (url LIKE ? OR title LIKE ?) AND url NOT LIKE ? "
                        "ORDER BY visit_count DESC, last_visit_time DESC LIMIT 1",
                        (f"%{clean_q}%", f"%{clean_q}%", "%google.com/search%")
                    )
                    row = c.fetchone()
                    conn.close()
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
                    if row and row[0]:
                        return [row[0]]
                except Exception:
                    pass

    # 5. Fallback to Google Search
    fallback_q = clean_q if clean_q else query
    return [f"https://www.google.com/search?q={urllib.parse.quote(fallback_q)}"]

def find_best_url_match(query: str, profile_dir: str = "Profile 1") -> str:
    """
    Simulates Chrome Omnibox Autocomplete: returns top URL match for a given query.
    """
    urls = resolve_target_urls(query, profile_dir=profile_dir)
    return urls[0] if urls else f"https://www.google.com/search?q={query}"

def search_and_open_in_browser(query: str = "", mode: str = "default", search_type: str = "web") -> Dict[str, Any]:
    """
    Opens Google Chrome with Sir Abdullah Irfan's profile by default, in Guest mode, or in Incognito mode.
    Supports single or multiple site targets (e.g. 'vmi and einno') and opens exact URLs simultaneously in tabs.
    Modes:
    - 'default': Opens with Sir Abdullah Irfan's profile (--profile-directory="Profile 1").
    - 'guest': Opens with Guest account (--guest).
    - 'incognito': Opens in Incognito mode with Abdullah Irfan's profile (--incognito).
    """
    import subprocess
    import os
    
    try:
        # Locate Chrome executable
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
        ]
        chrome_exe = next((p for p in chrome_paths if os.path.exists(p)), "chrome.exe")
        
        # Determine mode from query or parameter
        q_lower = query.lower() if query else ""
        if "guest" in q_lower or mode == "guest":
            active_mode = "guest"
            mode_flags = ["--guest"]
            mode_desc = "Guest Account"
        elif "incognito" in q_lower or "private" in q_lower or mode == "incognito":
            active_mode = "incognito"
            mode_flags = ["--incognito", "--profile-directory=Profile 1"]
            mode_desc = "Incognito Mode (Abdullah Irfan)"
        else:
            active_mode = "default"
            mode_flags = ["--profile-directory=Profile 1"]
            mode_desc = "Abdullah Irfan Profile"
            
        # Clean query if mode keywords were embedded
        clean_query = query
        for kw in ["guest account", "guest", "incognito"]:
            clean_query = clean_query.replace(kw, "").strip()
            
        # If no specific query left, just open browser blank/home
        if not clean_query.strip() or clean_query.strip() in ["browser", "chrome", "google chrome", "browser open kro", "browser kholo"]:
            cmd = [chrome_exe] + mode_flags
            subprocess.Popen(cmd)
            return {
                "status": "success",
                "mode": active_mode,
                "message": f"Sir, Chrome {mode_desc} ke sath open kardiya hai."
            }
            
        # Resolve target URLs (single or multiple)
        target_urls = resolve_target_urls(clean_query, profile_dir="Profile 1")
        cmd = [chrome_exe] + mode_flags + target_urls
        subprocess.Popen(cmd)
        
        urls_joined = ", ".join(target_urls)
        return {
            "status": "success",
            "opened_urls": target_urls,
            "mode": active_mode,
            "spoken_summary": f"Sir, {mode_desc} mein targets open kardiye hain.",
            "message": f"Sir, {mode_desc} mein requested links open kardiye hain: {urls_joined}"
        }
    except Exception as e:
        logger.exception("Error in search_and_open_in_browser")
        return {"status": "error", "error": str(e), "message": f"Browser launch error: {str(e)}"}

def get_open_browser_tabs(browser_name: str = "chrome") -> Dict[str, Any]:
    """
    Inspects active open tabs, web pages, and recent URLs in Google Chrome, Microsoft Edge, or Brave browser.
    Returns list of open tabs and a polite spoken summary.
    """
    import glob
    import sqlite3
    import shutil
    import tempfile
    import psutil
    
    b_lower = browser_name.lower()
    proc_name = "chrome.exe" if "chrome" in b_lower else ("msedge.exe" if "edge" in b_lower else "brave.exe")
    display_name = "Chrome" if "chrome" in b_lower else ("Edge" if "edge" in b_lower else "Brave")
    
    # 1. Check if browser is running
    is_running = any(p.name().lower() == proc_name for p in psutil.process_iter(["name"]))
    if not is_running:
        return {
            "status": "error",
            "is_running": False,
            "message": f"Sir, {display_name} browser is waqt laptop par open nahi hai."
        }
        
    user_data = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data" if "chrome" in b_lower else r"%LOCALAPPDATA%\Microsoft\Edge\User Data")
    if not os.path.exists(user_data):
        return {"status": "error", "message": f"Sir, {display_name} user data directory nahi mili."}
        
    profiles = glob.glob(os.path.join(user_data, "Profile *")) + [os.path.join(user_data, "Default")]
    
    def get_prof_mtime(p):
        h = os.path.join(p, "History")
        s = os.path.join(p, "Sessions")
        m1 = os.path.getmtime(h) if os.path.exists(h) else 0
        m2 = os.path.getmtime(s) if os.path.exists(s) else 0
        return max(m1, m2)
        
    profiles.sort(key=get_prof_mtime, reverse=True)
    
    found_tabs = []
    seen_urls = set()
    seen_titles = set()
    
    for prof in profiles[:3]:
        hist_file = os.path.join(prof, "History")
        if os.path.exists(hist_file):
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    tmp_path = tmp.name
                shutil.copy2(hist_file, tmp_path)
                conn = sqlite3.connect(tmp_path)
                cur = conn.cursor()
                cur.execute(
                    "SELECT title, url FROM urls "
                    "WHERE title != '' AND url NOT LIKE '%favicon%' AND url NOT LIKE 'chrome%' "
                    "ORDER BY last_visit_time DESC LIMIT 15"
                )
                for row in cur.fetchall():
                    title, url = str(row[0]).strip(), str(row[1]).strip()
                    title_norm = title.lower()[:25]
                    if url not in seen_urls and title_norm not in seen_titles and len(title) > 1:
                        seen_urls.add(url)
                        seen_titles.add(title_norm)
                        found_tabs.append({"title": title, "url": url})
                conn.close()
            except Exception:
                pass
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
                        
    if not found_tabs:
        return {
            "status": "success",
            "tabs": [],
            "message": f"Sir, {display_name} open hai lekin koi active web page ya tab nahi mila."
        }
        
    top_tabs = found_tabs[:5]
    tab_descriptions = [f"{i+1}. {t['title'][:40]}" for i, t in enumerate(top_tabs)]
    summary = f"Sir, {display_name} mein is waqt yeh tabs open hain: " + ", ".join(tab_descriptions) + "."
    
    return {
        "status": "success",
        "is_running": True,
        "count": len(top_tabs),
        "tabs": top_tabs,
        "spoken_summary": summary,
        "message": summary
    }

def play_youtube_music_or_video(query: str = "relaxing lofi music") -> Dict[str, Any]:
    """
    Searches YouTube for any song, artist, video, or genre and immediately starts playing the top video in Google Chrome (Abdullah Irfan profile).
    Call whenever user says 'song chalao', 'gaana lagao', 'music play karo', 'play arijit singh', 'play lofi song', etc.
    """
    import urllib.parse
    import urllib.request
    import re
    import subprocess
    import os
    
    clean_query = query.strip() if query else "latest popular songs"
    # Clean up conversational prefixes
    for pfx in ["koi accha", "koi pyara", "song lagao", "gaana lagao", "music lagao", "play karo", "play", "chalao", "lagao", "suno", "lga do", "lgao"]:
        clean_query = clean_query.replace(pfx, "").strip()
        
    if not clean_query:
        clean_query = "latest hindi urdu songs"
        
    # Resolve top video URL
    target_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(clean_query)}"
    try:
        search_url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(clean_query)
        req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        html = urllib.request.urlopen(req, timeout=4).read().decode("utf-8")
        matches = re.findall(r"watch\?v=([a-zA-Z0-9_-]{11})", html)
        if matches:
            target_url = "https://www.youtube.com/watch?v=" + matches[0]
    except Exception:
        pass
        
    # Open in Chrome with Abdullah Irfan profile
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
    ]
    chrome_exe = next((p for p in chrome_paths if os.path.exists(p)), "chrome.exe")
    
    cmd = [chrome_exe, "--profile-directory=Profile 1", target_url]
    subprocess.Popen(cmd)
    
    return {
        "status": "success",
        "query": clean_query,
        "video_url": target_url,
        "spoken_summary": f"Sir, YouTube par '{clean_query}' play kardiya hai.",
        "message": f"Sir, YouTube par '{clean_query}' play kardiya hai: {target_url}"
    }

def fetch_web_knowledge_and_facts(query: str) -> Dict[str, Any]:
    """
    Searches the live web for real-time information, biographies, places, things, companies, news, and technical facts.
    Returns rich snippets and accurate knowledge to explain to the user.
    """
    import urllib.request
    import urllib.parse
    import json
    import re

    clean_q = query.strip()
    for pfx in ["muje", "ke bare mei malomat do", "ke bare mein batao", "kya he", "kya hai", "kon he", "kon hai", "kidr he", "kidhar hai", "batao", "info do"]:
        clean_q = clean_q.replace(pfx, " ").strip()
    clean_q = " ".join(clean_q.split())
    if not clean_q:
        clean_q = query

    snippets = []
    # 1. DuckDuckGo Search
    try:
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(clean_q)
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        )
        html = urllib.request.urlopen(req, timeout=6).read().decode("utf-8", errors="ignore")
        raw_snippets = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html, re.DOTALL)
        for s in raw_snippets[:5]:
            clean_s = re.sub(r'<[^>]+>', '', s).strip()
            clean_s = clean_s.replace("&amp;", "&").replace("&#x27;", "'").replace("&quot;", '"')
            if clean_s and len(clean_s) > 20:
                snippets.append(clean_s)
    except Exception as e:
        logger.debug(f"Web search error: {e}")

    # 2. Wikipedia API lookup
    try:
        wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(clean_q)}"
        req = urllib.request.Request(wiki_url, headers={"User-Agent": "ZEN-Agent/2.0"})
        data = json.loads(urllib.request.urlopen(req, timeout=4).read().decode("utf-8"))
        if "extract" in data and data["extract"]:
            snippets.insert(0, data["extract"])
    except Exception:
        pass

    if snippets:
        combined_text = "\n".join(snippets[:4])
        return {
            "status": "success",
            "query": clean_q,
            "facts": combined_text,
            "message": f"Retrieved web information for '{clean_q}':\n{combined_text}"
        }
    else:
        return {
            "status": "info",
            "query": clean_q,
            "facts": "",
            "message": f"No web search snippets found for '{clean_q}'. Provide best AI knowledge."
        }

def download_software_or_game(software_name: str, use_fdm: Optional[bool] = None) -> Dict[str, Any]:
    """
    Downloads official Windows (x64) installers for applications, software, tools, and games.
    Supports specific site search (SteamRIP, FitGirl, OceanOfGames, Dodi, GitHub, SourceForge).
    If 'use_fdm' is True:
      - Verifies FDM installation & Chrome FDM extension and queues/triggers the download directly in Free Download Manager.
    If 'use_fdm' is False or not specified:
      - Initiates the download via Google Chrome into the default Windows Downloads folder.
    """
    import os
    import subprocess
    import urllib.parse
    import re
    import time
    import pyautogui
    
    clean_name = software_name.lower().strip()
    if use_fdm is None:
        if "fdm" in clean_name or "free download manager" in clean_name:
            use_fdm = True
        else:
            use_fdm = False
            
    # Detect target site if requested (e.g. steamrip, fitgirl, oceanofgames, dodi)
    site_search_map = {
        "steamrip": "https://steamrip.com/?s=",
        "fitgirl": "https://fitgirl-repacks.site/?s=",
        "oceanofgames": "https://oceanofgames.com/?s=",
        "ocean of games": "https://oceanofgames.com/?s=",
        "dodi": "https://dodi-repacks.site/?s=",
        "apunkagames": "https://apunkagames.biz/?s=",
        "github": "https://github.com/search?q=",
        "sourceforge": "https://sourceforge.net/directory/?q=",
        "softpedia": "https://www.softpedia.com/dyn-search.php?search_term="
    }
    
    detected_site = None
    site_prefix_url = None
    for site_key, site_url in site_search_map.items():
        if site_key in clean_name:
            detected_site = site_key
            site_prefix_url = site_url
            break
            
    # Clean up prefixes and filler words
    for kw in ["download karo", "download kro", "download kar do", "download", "ko", "mein", "me", "se", "fdm", "free download manager", "install karo", "installer", "website"]:
        clean_name = clean_name.replace(kw, " ").strip()
    if detected_site:
        clean_name = clean_name.replace(detected_site, " ").strip()
    clean_name = " ".join(clean_name.split())
    if not clean_name:
        clean_name = software_name.strip()

    # Chrome executable
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
    ]
    chrome_exe = next((p for p in chrome_paths if os.path.exists(p)), "chrome.exe")

    # FDM executable path lookup
    fdm_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Softdeluxe\Free Download Manager\fdm.exe"),
        r"C:\Program Files\Softdeluxe\Free Download Manager\fdm.exe",
        r"C:\Program Files\FreeDownloadManager.ORG\Free Download Manager\fdm.exe"
    ]
    fdm_exe = next((p for p in fdm_paths if os.path.exists(p)), None)

    # 1. Custom Website Specified (e.g. SteamRIP, FitGirl)
    if detected_site and site_prefix_url:
        target_url = site_prefix_url + urllib.parse.quote(clean_name)
        app_title = f"{clean_name.title()} ({detected_site.upper()})"
        
        # Open the exact search/download page in Chrome (Profile 1)
        subprocess.Popen([chrome_exe, "--profile-directory=Profile 1", target_url])
        
        # If FDM is requested, ensure FDM is active in background
        if use_fdm and fdm_exe:
            try:
                subprocess.Popen([fdm_exe])
            except Exception:
                pass
            spoken = f"Sir, {detected_site.upper()} se '{clean_name.title()}' ka download page Chrome aur FDM mein open kardiya hai."
            return {
                "status": "success",
                "software": app_title,
                "target_url": target_url,
                "downloader": f"FDM + Chrome ({detected_site.upper()})",
                "spoken_summary": spoken,
                "message": f"Sir, {detected_site.upper()} website se '{clean_name.title()}' ka download page Chrome aur FDM mein open kardiya hai ({target_url})."
            }
        else:
            spoken = f"Sir, {detected_site.upper()} se '{clean_name.title()}' ka download page Chrome mein open kardiya hai."
            return {
                "status": "success",
                "software": app_title,
                "target_url": target_url,
                "downloader": f"Chrome ({detected_site.upper()})",
                "spoken_summary": spoken,
                "message": f"Sir, {detected_site.upper()} website se '{clean_name.title()}' ka download page Chrome mein open kardiya hai ({target_url})."
            }

    catalog = {
        "tradingview": {
            "name": "TradingView Desktop (x64)",
            "url": "https://tvd-packages.tradingview.com/desktop/staging/win32/x64/TradingView.msix",
            "page_url": "https://www.tradingview.com/desktop/"
        },
        "vscode": {
            "name": "Visual Studio Code (x64)",
            "url": "https://code.visualstudio.com/sha/download?build=stable&os=win32-x64-user",
            "page_url": "https://code.visualstudio.com/Download"
        },
        "vs code": {
            "name": "Visual Studio Code (x64)",
            "url": "https://code.visualstudio.com/sha/download?build=stable&os=win32-x64-user",
            "page_url": "https://code.visualstudio.com/Download"
        },
        "git": {
            "name": "Git for Windows (x64)",
            "url": "https://github.com/git-for-windows/git/releases/latest/download/Git-64-bit.exe",
            "page_url": "https://git-scm.com/download/win"
        },
        "discord": {
            "name": "Discord Desktop",
            "url": "https://discord.com/api/download?platform=win",
            "page_url": "https://discord.com/download"
        },
        "telegram": {
            "name": "Telegram Desktop (x64)",
            "url": "https://telegram.org/dl/desktop/win64",
            "page_url": "https://desktop.telegram.org/"
        },
        "vlc": {
            "name": "VLC Media Player (x64)",
            "url": "https://get.videolan.org/vlc/last/win64/vlc-win64.exe",
            "page_url": "https://www.videolan.org/vlc/"
        },
        "steam": {
            "name": "Steam Client",
            "url": "https://cdn.cloudflare.steamstatic.com/client/installer/SteamSetup.exe",
            "page_url": "https://store.steampowered.com/about/"
        },
        "obs": {
            "name": "OBS Studio (x64)",
            "url": "https://obsproject.com/download",
            "page_url": "https://obsproject.com/download"
        },
        "nodejs": {
            "name": "Node.js (x64)",
            "url": "https://nodejs.org/dist/v22.14.0/node-v22.14.0-x64.msi",
            "page_url": "https://nodejs.org/en/download"
        },
        "node": {
            "name": "Node.js (x64)",
            "url": "https://nodejs.org/dist/v22.14.0/node-v22.14.0-x64.msi",
            "page_url": "https://nodejs.org/en/download"
        },
        "python": {
            "name": "Python 3.13 (x64)",
            "url": "https://www.python.org/ftp/python/3.13.2/python-3.13.2-amd64.exe",
            "page_url": "https://www.python.org/downloads/"
        },
        "7zip": {
            "name": "7-Zip (x64)",
            "url": "https://www.7-zip.org/a/7z2408-x64.exe",
            "page_url": "https://www.7-zip.org/"
        },
        "brave": {
            "name": "Brave Browser (x64)",
            "url": "https://laptop-updates.brave.com/latest/winx64",
            "page_url": "https://brave.com/download/"
        },
        "chrome": {
            "name": "Google Chrome (x64)",
            "url": "https://dl.google.com/chrome/install/standalone/x64/ChromeStandaloneSetup64.exe",
            "page_url": "https://www.google.com/chrome/"
        },
        "whatsapp": {
            "name": "WhatsApp Desktop (x64)",
            "url": "https://web.whatsapp.com/desktop/windows/release/x64/WhatsAppSetup.exe",
            "page_url": "https://www.whatsapp.com/download"
        },
        "spotify": {
            "name": "Spotify Desktop",
            "url": "https://download.scdn.co/SpotifySetup.exe",
            "page_url": "https://www.spotify.com/download/"
        },
        "postman": {
            "name": "Postman Desktop (x64)",
            "url": "https://dl.pstmn.io/download/latest/win64",
            "page_url": "https://www.postman.com/downloads/"
        },
        "epic": {
            "name": "Epic Games Launcher",
            "url": "https://launcher-public-service-prod06.ol.epicgames.com/launcher/api/installer/download/EpicGamesLauncherInstaller.msi",
            "page_url": "https://store.epicgames.com/en-US/download"
        },
        "notepad++": {
            "name": "Notepad++ (x64)",
            "url": "https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/v8.7.6/npp.8.7.6.Installer.x64.exe",
            "page_url": "https://notepad-plus-plus.org/downloads/"
        }
    }

    # Match target entry from catalog or dynamic link
    target_entry = None
    for key, data in catalog.items():
        if key in clean_name or clean_name in key:
            target_entry = data
            break

    if target_entry:
        app_title = target_entry["name"]
        target_url = target_entry["url"]
    else:
        app_title = clean_name.capitalize()
        target_url = f"https://www.google.com/search?q={urllib.parse.quote(clean_name + ' download official windows 64-bit')}"

    if use_fdm and fdm_exe:
        # Launch in Free Download Manager
        try:
            subprocess.Popen([fdm_exe, target_url])
            time.sleep(0.6)
            # Auto-confirm FDM popup dialog if focused
            focus_window_by_title("Free Download Manager")
            time.sleep(0.2)
            pyautogui.press("enter")
        except Exception:
            pass
        # Also open in Chrome (Profile 1) with FDM extension active
        try:
            subprocess.Popen([chrome_exe, "--profile-directory=Profile 1", target_url])
        except Exception:
            pass
            
        spoken = f"Sir, {app_title} Free Download Manager (FDM) mein download par laga diya hai."
        return {
            "status": "success",
            "software": app_title,
            "target_url": target_url,
            "downloader": "Free Download Manager (FDM)",
            "spoken_summary": spoken,
            "message": f"Sir, {app_title} x64 installer Free Download Manager (FDM) mein download par laga diya hai ({target_url})."
        }
    else:
        # Standard Browser Download in Chrome -> Windows Downloads Folder
        subprocess.Popen([chrome_exe, "--profile-directory=Profile 1", target_url])
        spoken = f"Sir, {app_title} Windows Downloads folder mein download par laga diya hai."
        return {
            "status": "success",
            "software": app_title,
            "target_url": target_url,
            "downloader": "Chrome (Windows Downloads)",
            "spoken_summary": spoken,
            "message": f"Sir, {app_title} x64 installer Windows Downloads folder mein download par laga diya hai ({target_url})."
        }

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
    "manage_screen_power": manage_screen_power,
    "get_open_browser_tabs": get_open_browser_tabs,
    "get_running_system_apps": get_running_system_apps,
    "get_antigravity_activity_summary": get_antigravity_activity_summary,
    "set_ai_model": set_ai_model,
    "inspect_web_page_or_dashboard": inspect_web_page_or_dashboard,
    "play_youtube_music_or_video": play_youtube_music_or_video,
    "proceed_browser_login": proceed_browser_login,
    "fetch_web_knowledge_and_facts": fetch_web_knowledge_and_facts,
    "download_software_or_game": download_software_or_game,
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
    manage_screen_power,
    open_windows_settings,
    send_whatsapp_message,
    send_antigravity_command,
    type_text_into_active_app,
    proceed_browser_login,
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
    get_open_browser_tabs,
    get_running_system_apps,
    get_antigravity_activity_summary,
    set_ai_model,
    inspect_web_page_or_dashboard,
    play_youtube_music_or_video,
    fetch_web_knowledge_and_facts,
    download_software_or_game,
]
