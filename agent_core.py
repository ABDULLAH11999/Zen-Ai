import logging
import time
from typing import Callable, Optional, Dict, Any, List
from google import genai
from google.genai import types

from config import config
from screen_vision import screen_vision
from system_tools import TOOL_REGISTRY, TOOL_DECLARATIONS

logger = logging.getLogger(__name__)

class JarvisAgent:
    """Core brain of Zen powered by Gemini 2.0 Flash with Multimodal Vision and Tool Calling."""
    
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not set in environment or config!")
            
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.model_name = config.GEMINI_MODEL
        self.chat_history: List[types.Content] = []
        
    def reset_history(self):
        """Clears conversation context."""
        self.chat_history = []

    def _execute_tool_call(self, function_call: types.FunctionCall, on_tool_event: Optional[Callable] = None) -> types.Part:
        """Executes a single tool call requested by Gemini and returns the FunctionResponse part."""
        name = function_call.name
        args = function_call.args or {}
        
        logger.info(f"Jarvis Tool Invocation -> {name}({args})")
        if on_tool_event:
            on_tool_event(f"Executing: {name}({args})")
            
        tool_func = TOOL_REGISTRY.get(name)
        if tool_func:
            try:
                result = tool_func(**args)
            except Exception as e:
                logger.exception(f"Error calling {name}")
                result = {"status": "error", "exception": str(e)}
        else:
            result = {"status": "error", "message": f"Unknown tool function: {name}"}
            
        if on_tool_event:
            on_tool_event(f"Result [{name}]: {str(result)[:200]}...")
            
        return types.Part.from_function_response(
            name=name,
            response={"result": result}
        )

    def _process_with_groq_fast_path(
        self,
        user_prompt: str,
        on_status_change: Optional[Callable[[str], None]] = None,
        on_tool_event: Optional[Callable[[str], None]] = None
    ) -> Optional[str]:
        """
        Executes non-vision commands through Groq LPUs in ~150ms with full tool execution.
        """
        if not config.GROQ_API_KEY:
            return None
            
        try:
            import json
            from groq import Groq
            groq_client = Groq(api_key=config.GROQ_API_KEY, timeout=6.0)
            
            groq_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "close_application",
                        "description": "Closes an active desktop application by name (e.g., 'GitHub Desktop', 'Chrome', 'WhatsApp', 'GTA V', 'Notepad').",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "app_name": {"type": "string", "description": "The name of the application to close."}
                            },
                            "required": ["app_name"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "check_git_repo_status",
                        "description": "Fetches latest git updates and checks if any new commits or incoming pulls are available.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "repo_path": {"type": "string", "description": "Optional repository path. Defaults to workspace."}
                            }
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "manage_system_volume",
                        "description": "Controls master audio volume on Windows (set 0-100, mute, unmute, up, down).",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["set", "mute", "unmute", "up", "down", "status"]},
                                "level_percent": {"type": "integer", "description": "Volume percentage (0-100)"}
                            },
                            "required": ["action"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "open_url_or_application",
                        "description": "Opens a URL in the default browser, launches an application, desktop shortcut, or game (e.g. GTA 5, GTA V, Spider-Man, Chrome, VS Code). Call immediately when user asks 'gta 5 launch krdo', 'gta v lga do', 'gta open karo', 'open youtube', etc.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "target": {"type": "string", "description": "The URL (https://...), game name ('gta 5', 'spider-man'), or application name."}
                            },
                            "required": ["target"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "execute_terminal_command",
                        "description": "Executes a shell command in the workspace directory safely.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "command": {"type": "string", "description": "The shell command to run."}
                            },
                            "required": ["command"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_system_status",
                        "description": "Returns current CPU, RAM, Disk, battery, and top processes.",
                        "parameters": {"type": "object", "properties": {}}
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "check_windows_updates",
                        "description": "Checks Windows for pending system updates.",
                        "parameters": {"type": "object", "properties": {}}
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "manage_windows_power",
                        "description": "Locks the screen, sleeps, or manages power (lock, sleep, restart, shutdown, cancel).",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["lock", "sleep", "restart", "shutdown", "cancel"]}
                            },
                            "required": ["action"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "unlock_workstation",
                        "description": "Wakes up display and automatically inputs pre-configured Windows PIN (7940) to unlock workstation. Call immediately whenever user asks to unlock or enter PIN. Never ask user for PIN.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "pin": {"type": "string", "description": "Optional PIN. Defaults to configured WINDOWS_PIN in .env."}
                            }
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "send_whatsapp_message",
                        "description": "Opens WhatsApp and sends a message to contact.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "contact_or_phone": {"type": "string"},
                                "message": {"type": "string"}
                            },
                            "required": ["contact_or_phone", "message"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "send_antigravity_command",
                        "description": "Opens Antigravity IDE and types command/prompt.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "prompt_text": {"type": "string"}
                            },
                            "required": ["prompt_text"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "search_and_open_in_browser",
                        "description": "Searches or opens URLs, Chrome History, or Websites (e.g. Contabo, Linux server, PMI, Google).",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search term, website name, or URL to open."}
                            },
                            "required": ["query"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "manage_display_brightness",
                        "description": "Adjusts laptop display/screen brightness from 0 to 100 percent. Call when user asks 'brightness 10 kardo', 'brightness barha do', 'screen light kam karo', etc.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "level": {"type": "integer", "description": "Target brightness percentage between 0 and 100."},
                                "action": {"type": "string", "enum": ["set", "increase", "decrease", "max", "min"], "description": "Action type"}
                            }
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "manage_system_volume",
                        "description": "Adjusts Windows master sound volume (0-100), mutes, or unmutes audio. Call when asked 'volume 50 kardo', 'mute karo', 'awaz barha do', etc.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "level": {"type": "integer", "description": "Volume percentage 0 to 100."},
                                "action": {"type": "string", "enum": ["set", "mute", "unmute", "increase", "decrease"]}
                            }
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "manage_bluetooth",
                        "description": "Toggles Windows Bluetooth ON or OFF. Call when asked 'bluetooth on karo', 'bluetooth toggle karo', 'bluetooth off karo'.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["toggle", "on", "off", "settings"]}
                            }
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "close_all_user_applications",
                        "description": "Closes all open user apps on taskbar (Chrome, Edge, Spotify, Notepad, WhatsApp, Office). Call when asked 'close all apps', 'tamam apps band kardo'.",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "close_application",
                        "description": "Closes a specific application window (e.g. Chrome, Notepad, Spotify).",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "app_name": {"type": "string", "description": "Application name or process to close."}
                            },
                            "required": ["app_name"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "manage_media_playback",
                        "description": "Controls music and video playback (Play, Pause, Next Track, Previous Track, Stop). Call when asked 'gaana roko', 'play music', 'next track'.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "action": {"type": "string", "enum": ["play", "pause", "play_pause", "toggle", "next", "prev", "stop"]}
                            }
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_latest_backtest_report_summary",
                        "description": "Reads latest Binance/MEXC trading bot backtest report and returns start/end capital, net PnL, timeline and trades in Urdu/Hindi.",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "check_scalper_bot_status",
                        "description": "Checks live web trading dashboard (https://scalper-bot.84-247-185-16.plesk.page/) and returns Market Sentiment Score, Regime, Total Balance, and Active Trades when asked 'trading bot kesa chal raha he' or 'bot status'.",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_open_browser_tabs",
                        "description": "Inspects open tabs, web pages, and URLs currently active in Google Chrome or Microsoft Edge. Call immediately when user asks 'chrome pe konse tabs on hein', 'chrome ke tabs dikhao', 'browser mein kya khula hai', etc.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "browser_name": {
                                    "type": "string",
                                    "description": "Browser name: 'chrome' (default) or 'edge'."
                                }
                            }
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_running_system_apps",
                        "description": "Scans all running user applications on the laptop and active Antigravity workspace. Call immediately when user asks 'system pe kya run hora he', 'laptop pe kya chal raha hai', 'running apps', etc.",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_antigravity_activity_summary",
                        "description": "Reads latest conversation and active commands/responses in Antigravity IDE and summarizes current task. Call when user asks 'antigravity pe kya chal raha he', 'antigravity status', 'antigravity summary', etc.",
                        "parameters": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "send_antigravity_command",
                        "description": "Focuses Antigravity IDE and types a prompt/command into the active workspace chat box and sends it. Call when user asks 'antigravity pe prompt likho', 'antigravity ko prompt bhejo', etc.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "prompt_text": {"type": "string", "description": "The exact prompt text to type and submit."}
                            },
                            "required": ["prompt_text"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "set_ai_model",
                        "description": "Switches the active AI model (e.g. '3.7 se 3.8', 'gemini-3.8-flash', 'gemini-2.5-flash'). Call when user asks 'model change karo', 'model 3.8 set karo', etc.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "model_name": {"type": "string", "description": "Model name or version to switch to."}
                            },
                            "required": ["model_name"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "inspect_web_page_or_dashboard",
                        "description": "Reads any website link/URL, extracts text/dashboard data, and summarizes what is on the page. Call when user provides any website link or asks to read a web page.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "url": {"type": "string", "description": "The full website URL to inspect."}
                            },
                            "required": ["url"]
                        }
                    }
                }
            ]
            
            messages = [
                {"role": "system", "content": config.SYSTEM_INSTRUCTION},
                {"role": "user", "content": user_prompt}
            ]
            
            resp = groq_client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=messages,
                tools=groq_tools,
                tool_choice="auto",
                max_tokens=250,
                temperature=0.5
            )
            
            msg = resp.choices[0].message
            tool_calls = msg.tool_calls or []
            
            # Text-based tool call fallback for models like Qwen
            if not tool_calls and msg.content and "<tool_call>" in msg.content:
                import re
                fn_matches = re.findall(r"<function=([a-zA-Z0-9_]+)>", msg.content)
                for fn_name in fn_matches:
                    param_dict = {}
                    param_matches = re.findall(rf"<parameter=([a-zA-Z0-9_]+)>\s*([^<\n\r]+)\s*</parameter>", msg.content)
                    for p_name, p_val in param_matches:
                        p_val = p_val.strip()
                        if p_val.isdigit():
                            param_dict[p_name] = int(p_val)
                        elif p_name in ["level", "volume_level"]:
                            param_dict["level"] = int(re.sub(r"\D", "", p_val) or 50)
                        else:
                            param_dict[p_name] = p_val
                    
                    class MockFunc:
                        def __init__(self, name, args):
                            self.name = name
                            self.arguments = json.dumps(args)
                    class MockToolCall:
                        def __init__(self, name, args):
                            self.id = "call_" + name
                            self.function = MockFunc(name, args)
                    tool_calls.append(MockToolCall(fn_name, param_dict))

            if tool_calls:
                tool_results = []
                for tool_call in tool_calls:
                    fn_name = tool_call.function.name
                    try:
                        fn_args = json.loads(tool_call.function.arguments)
                    except Exception:
                        fn_args = {}
                    logger.info(f"Groq Fast-Path Invocation -> {fn_name}({fn_args})")
                    if on_tool_event:
                        on_tool_event(f"Executing: {fn_name}({fn_args})")
                        
                    tool_func = TOOL_REGISTRY.get(fn_name)
                    if tool_func:
                        try:
                            res = tool_func(**fn_args)
                        except Exception as e:
                            res = {"status": "error", "error": str(e)}
                    else:
                        res = {"status": "error", "error": f"Tool '{fn_name}' not found."}
                    tool_results.append((tool_call, res))
                    
                # Instant crisp return if tool already provides clear spoken message
                for tc, r in tool_results:
                    if not isinstance(r, dict):
                        continue
                    
                    # Specific query customization for battery questions
                    if tc.function.name == "get_system_status":
                        prompt_l = user_prompt.lower()
                        if any(w in prompt_l for w in ["charge", "battery", "charg", "charging"]):
                            batt_p = r.get("battery_percent")
                            is_p = r.get("battery_plugged", True)
                            p_str = "charging par laga hai" if is_p else "battery par chal raha hai"
                            if batt_p is not None:
                                return f"Sir, system ki battery {batt_p}% hai aur {p_str}."
                        return r.get("spoken_summary", r.get("message", "Sir, system bilkul normal chal raha hai."))
                        
                    if r.get("spoken_summary"):
                        return r["spoken_summary"]
                    if r.get("message"):
                        return r["message"]
                        
                if any(tc.function.name == "unlock_workstation" for tc, _ in tool_results):
                    return "Jee Sir, aapka system unlock kardiya hai."
                    
                messages.append(msg)
                for tc, r in tool_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": getattr(tc, "id", "call_1"),
                        "name": tc.function.name,
                        "content": json.dumps(r)
                    })
                    
                try:
                    second_resp = groq_client.chat.completions.create(
                        model=config.GROQ_MODEL,
                        messages=messages,
                        max_tokens=150,
                        temperature=0.5,
                        timeout=5.0
                    )
                    final_text = second_resp.choices[0].message.content or ""
                    import re
                    final_text = re.sub(r"<think>.*?(?:</think>|$)", "", final_text, flags=re.DOTALL).strip()
                    if final_text:
                        logger.info(f"Groq Fast-Path executed: '{final_text}'")
                        return final_text
                except Exception as s_err:
                    logger.debug(f"Groq second turn timeout/err: {s_err}")
                    pass
                    
                # Direct instant fallback
                return "Jee Sir, kaam mukammal kardiya hai."
                
            elif msg.content and msg.content.strip():
                import re
                clean_msg = re.sub(r"<think>.*?(?:</think>|$)", "", msg.content, flags=re.DOTALL).strip()
                if clean_msg:
                    logger.info(f"Groq Fast-Path replied: '{clean_msg}'")
                    return clean_msg
                return "Jee Sir."
        except Exception as groq_fast_err:
            logger.debug(f"Groq Fast-Path fallback to Gemini ({groq_fast_err})")
            
        return None

    def process_query(
        self,
        user_prompt: str,
        include_screen: bool = True,
        on_status_change: Optional[Callable[[str], None]] = None,
        on_tool_event: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Ultra-low latency dual-engine query processor:
        1. Checks if visual screen analysis is specifically asked (e.g. 'screen dekho').
        2. If not vision-dependent, executes through Groq LPU Fast-Path in <200ms.
        3. If vision is required, uses Gemini 2.5 Flash Multimodal Vision.
        """
        if on_status_change:
            on_status_change("Thinking")
            
        # Detect if user specifically asked to look at/analyze the screen visually
        lower_prompt = user_prompt.lower()
        vision_triggers = [
            "screen dekho", "dekho screen", "screen pe kya", "screen par kya",
            "look at screen", "look at my screen", "see screen", "screen read",
            "chart dekho", "image dekho", "error dekho", "screen analysis"
        ]
        needs_vision = any(trigger in lower_prompt for trigger in vision_triggers)
        
        # Zero-latency immediate intent triggers (<20ms)
        if any(g in lower_prompt for g in ["gta 5", "gta v", "gta5", "gtav", "playgtav", "grand theft auto"]) and any(act in lower_prompt for act in ["launch", "open", "kholo", "lga", "laga", "chala", "run", "play"]):
            res = TOOL_REGISTRY["open_url_or_application"](target="gta 5")
            return res.get("message", "Sir, GTA V PlayGTAV.exe ke zariye launch kardiya hai.")
            
        if any(w in lower_prompt for w in ["chrome pe konse tabs", "chrome ke tabs", "konse tabs on", "browser ke tabs", "chrome tabs"]):
            res = TOOL_REGISTRY["get_open_browser_tabs"](browser_name="chrome")
            return res.get("spoken_summary", res.get("message", "Sir, Chrome ke tabs retrieve karliye hain."))
            
        if any(w in lower_prompt for w in ["system pe kya run", "system par kya run", "system pe kya chal", "laptop pe kya run", "kya chal raha he system", "running apps", "kon kon sa app"]):
            res = TOOL_REGISTRY["get_running_system_apps"]()
            return res.get("spoken_summary", res.get("message", "Sir, system applications retrieve karli hain."))
            
        if any(w in lower_prompt for w in ["antigravity pe kya", "antigravity par kya", "antigravity status", "antigravity summary", "antigravity activity", "antigravity kya kar"]):
            res = TOOL_REGISTRY["get_antigravity_activity_summary"]()
            return res.get("spoken_summary", res.get("message", "Sir, Antigravity summary retrieve karli hai."))
            
        if "model" in lower_prompt and any(w in lower_prompt for w in ["set", "change", "badlo", "karo", "switch", "3.7", "3.8"]):
            import re
            m = re.search(r"(\d+\.\d+|flash|pro|gemini[a-zA-Z0-9\.\-]+|qwen[a-zA-Z0-9\.\-/]+)", lower_prompt)
            target_m = m.group(1) if m else "3.8"
            res = TOOL_REGISTRY["set_ai_model"](model_name=target_m)
            return res.get("message", f"Sir, model {target_m} par set kardiya hai.")
        
        # 1. Fast Path for instantaneous sub-second execution (non-vision queries & actions)
        if not needs_vision and config.GROQ_API_KEY:
            fast_result = self._process_with_groq_fast_path(
                user_prompt=user_prompt,
                on_status_change=on_status_change,
                on_tool_event=on_tool_event
            )
            if fast_result:
                return fast_result
                
        # 2. Multimodal Vision Path (Gemini Flash)
        try:
            content_parts = []
            
            # Attach screen only if vision is requested
            if include_screen and needs_vision:
                try:
                    screen_bytes = screen_vision.capture_screen_bytes()
                    screen_part = types.Part.from_bytes(data=screen_bytes, mime_type="image/jpeg")
                    content_parts.append(screen_part)
                except Exception as e:
                    logger.warning(f"Failed to capture screen for vision: {e}")
                    
            content_parts.append(types.Part.from_text(text=user_prompt))
            user_content = types.Content(role="user", parts=content_parts)
            self.chat_history.append(user_content)
            
            generate_config = types.GenerateContentConfig(
                system_instruction=config.SYSTEM_INSTRUCTION,
                temperature=0.6,
                tools=TOOL_DECLARATIONS
            )
            
            max_turns = 6
            current_turn = 0
            
            # Multi-Key Rotation with Persistent Active Index
            api_keys = config.GEMINI_API_KEYS if config.GEMINI_API_KEYS else ([config.GEMINI_API_KEY] if config.GEMINI_API_KEY else [])
            num_keys = len(api_keys)
            
            fallback_models = [
                "gemini-2.5-flash",
                "gemini-3.5-flash",
                "gemini-3.1-flash-lite",
                "gemini-flash-latest",
            ]
            
            while current_turn < max_turns:
                current_turn += 1
                response = None
                last_error = None
                
                # Try all keys starting from currently active key
                for offset in range(max(1, num_keys)):
                    key_idx = (getattr(self, 'current_key_idx', 0) + offset) % max(1, num_keys)
                    current_key = api_keys[key_idx] if api_keys else ""
                    
                    if not current_key:
                        continue
                        
                    try:
                        active_client = genai.Client(api_key=current_key)
                    except Exception as client_err:
                        continue
                        
                    for model_candidate in fallback_models:
                        try:
                            response = active_client.models.generate_content(
                                model=model_candidate,
                                contents=self.chat_history,
                                config=generate_config
                            )
                            if response and (response.text or response.candidates):
                                self.client = active_client
                                self.current_key_idx = key_idx # Save working key
                                break
                        except Exception as model_err:
                            last_error = str(model_err)
                            err_str = str(model_err).lower()
                            if "429" in err_str or "quota" in err_str or "exhausted" in err_str:
                                logger.warning(f"Gemini Key #{key_idx+1} Quota Exhausted. Instantly rotating to Secondary Key #{((key_idx+1)%num_keys)+1}...")
                                break # Skip other models on this exhausted key, switch key immediately!
                            continue
                            
                    if response is not None:
                        break
                        
                if response is None:
                    # Final fallback to Groq
                    groq_resp = self._process_with_groq_fast_path(user_prompt, on_status_change, on_tool_event)
                    if groq_resp:
                        return groq_resp
                    return "Sir, network mein issue aya hai. Dobara hukum kijiye."
                
                candidate = response.candidates[0] if response.candidates else None
                if not candidate or not candidate.content:
                    return "Jee Sir."
                    
                model_content = candidate.content
                self.chat_history.append(model_content)
                
                # Check if model made function calls
                function_calls = [part.function_call for part in model_content.parts if part.function_call]
                
                if function_calls:
                    # Execute all function calls and gather tool responses
                    tool_response_parts = []
                    for fc in function_calls:
                        resp_part = self._execute_tool_call(fc, on_tool_event=on_tool_event)
                        tool_response_parts.append(resp_part)
                        
                    tool_content = types.Content(role="tool", parts=tool_response_parts)
                    self.chat_history.append(tool_content)
                else:
                    final_text = response.text or ""
                    if len(self.chat_history) > 15:
                        self.chat_history = self.chat_history[-15:]
                    return final_text.strip()
                    
            return "Sir, kaam mukammal kardiya gaya hai."
            
        except Exception as e:
            logger.exception("Error during agent processing")
            return f"An error occurred: {e}"
