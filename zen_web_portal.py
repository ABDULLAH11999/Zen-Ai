import os
import io
import sys
import time
import json
import base64
import logging
import asyncio
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import config
from agent_core import JarvisAgent
from system_tools import (
    get_system_status,
    manage_windows_power,
    unlock_workstation,
    search_and_open_in_browser,
    close_application,
    check_git_repo_status
)
from screen_vision import screen_vision

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] (WebPortal) %(message)s")
logger = logging.getLogger("ZENWebPortal")

app = FastAPI(title="Z.E.N. Mobile Web Audio Portal", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared agent instance
agent = JarvisAgent()

async def generate_tts_base64(text: str) -> Optional[str]:
    """Synthesizes text to speech with Edge-TTS and returns base64 MP3."""
    if not text:
        return None
    try:
        import edge_tts
        voices_to_try = [
            getattr(config, "TTS_VOICE_HINDI", "hi-IN-MadhurNeural"),
            "hi-IN-SwaraNeural",
            getattr(config, "TTS_VOICE_URDU", "ur-PK-AsadNeural"),
            "en-GB-RyanNeural"
        ]
        
        for voice in voices_to_try:
            try:
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=voice,
                    rate=config.TTS_RATE,
                    pitch=config.TTS_PITCH
                )
                audio_stream = io.BytesIO()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_stream.write(chunk["data"])
                
                audio_bytes = audio_stream.getvalue()
                if audio_bytes and len(audio_bytes) > 200:
                    return base64.b64encode(audio_bytes).decode("utf-8")
            except Exception as v_err:
                logger.warning(f"Voice {voice} failed ({v_err}), trying next fallback...")
                continue
    except Exception as e:
        logger.error(f"Error generating TTS audio: {e}")
    return None

@app.get("/api/status")
async def api_status():
    """Returns live PC telemetry."""
    status_info = get_system_status()
    return {
        "status": "online",
        "agent": "ZEN 2.0",
        "owner": config.OWNER_NAME,
        "telemetry": status_info
    }

@app.get("/api/screenshot")
async def api_screenshot():
    """Returns real-time desktop screenshot."""
    try:
        jpeg_bytes = screen_vision.capture_screen_bytes()
        return Response(content=jpeg_bytes, media_type="image/jpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/text_command")
async def api_text_command(payload: dict):
    """Processes typed command from mobile browser."""
    prompt = payload.get("text", "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Empty text prompt")
        
    logger.info(f"Mobile Text Command: '{prompt}'")
    response_text = agent.process_query(prompt, include_screen=False)
    tts_b64 = await generate_tts_base64(response_text)
    
    return {
        "status": "success",
        "user_prompt": prompt,
        "reply_text": response_text,
        "audio_base64": tts_b64
    }

@app.post("/api/voice_command")
async def api_voice_command(audio: UploadFile = File(...)):
    """Receives recorded voice from iPhone Safari Mic, transcribes, executes, and returns speech."""
    try:
        audio_bytes = await audio.read()
        logger.info(f"Received mobile voice recording: {len(audio_bytes)} bytes ({audio.content_type})")
        
        if len(audio_bytes) < 1000:
            return {
                "status": "error",
                "reply_text": "Audio bohot chhota tha, dobara bolein.",
                "transcription": ""
            }
            
        # Transcribe with Groq Whisper
        from groq import Groq
        groq_client = Groq(api_key=config.GROQ_API_KEY, timeout=6.0)
        
        # Explicit language parameter for clean Urdu/Hindi understanding
        groq_lang = "hi" if config.JARVIS_LANGUAGE in ["hindi", "bilingual"] else ("ur" if config.JARVIS_LANGUAGE == "urdu" else None)
        prompt_text = "ज़ेन (ZEN) वॉयस असिस्टेंट। Urdu, Hindi, Roman Urdu, Chrome, YouTube, Binance, AntiGravity, Desktop, GitHub, VS Code, open karo, close karo, band karo."
        
        transcription_resp = groq_client.audio.transcriptions.create(
            file=("recording.wav", audio_bytes, "audio/wav"),
            model="whisper-large-v3-turbo",
            language=groq_lang,
            prompt=prompt_text,
            temperature=0.0
        )
        
        transcription = transcription_resp.text.strip() if transcription_resp else ""
        logger.info(f"Mobile Whisper Transcribed: '{transcription}'")
        
        if not transcription:
            return {
                "status": "error",
                "reply_text": "Aapki awaz samajh nahi aayi, dobara bolein.",
                "transcription": ""
            }
            
        # Execute query via ZEN Agent
        response_text = agent.process_query(transcription, include_screen=False)
        tts_b64 = await generate_tts_base64(response_text)
        
        return {
            "status": "success",
            "transcription": transcription,
            "reply_text": response_text,
            "audio_base64": tts_b64
        }
    except Exception as e:
        logger.exception("Error processing mobile voice command")
        return {
            "status": "error",
            "reply_text": f"Error: {str(e)}",
            "transcription": ""
        }

from system_tools import (
    get_system_status,
    manage_windows_power,
    manage_screen_power,
    unlock_workstation,
    search_and_open_in_browser,
    open_url_or_application,
    close_application,
    close_all_user_applications,
    manage_bluetooth,
    check_git_repo_status,
    get_latest_backtest_report_summary,
    check_scalper_bot_status
)

# Background Keep-Awake Sentinel: Prevents Windows from Auto-Locking while portal is running
keep_awake_active = True
display_state = "on"

async def keep_awake_loop():
    """Periodically calls SetThreadExecutionState to keep session awake without locking."""
    import ctypes
    kernel32 = ctypes.windll.kernel32
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002
    
    while True:
        try:
            if keep_awake_active:
                kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
        except Exception:
            pass
        await asyncio.sleep(25)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(keep_awake_loop())
    logger.info("[Z.E.N.] Anti-Lock Keep-Awake Sentinel activated.")

@app.post("/api/quick_action")
async def api_quick_action(payload: dict):
    """Executes 1-click mobile quick actions."""
    global keep_awake_active, display_state
    action = payload.get("action", "")
    logger.info(f"Mobile Quick Action: '{action}'")
    
    msg = "Action executed."
    if action in ["toggle_display", "screen_toggle"]:
        if display_state == "on":
            manage_screen_power("off")
            display_state = "off"
            msg = "Display black kar di gayi hai, session unlocked aur apps active hain, Sir."
        else:
            manage_screen_power("on")
            display_state = "on"
            msg = "Display on kar di gayi hai, Sir."
    elif action in ["screen_off", "black_screen"]:
        manage_screen_power("off")
        display_state = "off"
        msg = "Screen black kar di gayi hai, session unlocked aur apps active hain, Sir."
    elif action in ["wake_screen", "screen_on"]:
        manage_screen_power("on")
        display_state = "on"
        msg = "Screen on kar di gayi hai, Sir."
    elif action == "lock":
        # When portal is connected, turn screen black to prevent lock screen credential barrier
        manage_screen_power("off")
        display_state = "off"
        msg = "Display black kar di gayi hai. Portal active hone ki wajah se system session unlocked hai, Sir."
    elif action == "unlock":
        manage_screen_power("on")
        display_state = "on"
        res = unlock_workstation()
        msg = res.get("message", "Screen wake & unlock triggered.")
    elif action == "close_apps":
        res = close_all_user_applications()
        msg = res.get("message", "All apps closed.")
    elif action == "toggle_bt":
        res = manage_bluetooth("toggle")
        msg = res.get("message", "Bluetooth toggled.")
    elif action == "backtest_report":
        res = get_latest_backtest_report_summary("F:\\binance_mexc_bot")
        msg = res.get("spoken_summary", res.get("message", "Backtest summary retrieved."))
    elif action == "check_bot":
        res = check_scalper_bot_status()
        msg = res.get("spoken_summary", res.get("message", "Bot status retrieved."))
    elif action == "shutdown":
        manage_windows_power("shutdown")
        msg = "Sir, system shutdown 5 seconds mein initiate ho raha hai."
        
    tts_b64 = await generate_tts_base64(msg)
    return {"status": "success", "message": msg, "audio_base64": tts_b64, "display_state": display_state}

@app.get("/", response_class=HTMLResponse)
async def mobile_portal_ui():
    """Returns stunning Mobile Cyberpunk Web Portal for iPhone 12 Pro."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Z.E.N. // Mobile Controller</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #07090e;
            --card-bg: rgba(16, 22, 34, 0.75);
            --card-border: rgba(0, 240, 255, 0.15);
            --cyan-glow: #00f0ff;
            --blue-accent: #0070f3;
            --purple-glow: #7928ca;
            --text-main: #f0f4fc;
            --text-dim: #8b9bb4;
            --danger: #ff0055;
            --success: #00ff88;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-base);
            background-image: 
                radial-gradient(circle at 50% 0%, rgba(0, 240, 255, 0.08) 0%, transparent 50%),
                radial-gradient(circle at 100% 100%, rgba(121, 40, 202, 0.08) 0%, transparent 50%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .container {
            width: 100%;
            max-width: 480px;
            display: flex;
            flex-direction: column;
            gap: 16px;
            padding-bottom: 24px;
        }

        /* Header */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 14px 18px;
            border-radius: 16px;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .brand-icon {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            background: linear-gradient(135deg, var(--cyan-glow), var(--purple-glow));
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 16px;
            color: #000;
            box-shadow: 0 0 15px rgba(0, 240, 255, 0.4);
        }

        .brand-title {
            font-weight: 700;
            font-size: 18px;
            letter-spacing: 1px;
            color: #fff;
        }

        .status-badge {
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 20px;
            background: rgba(0, 255, 136, 0.1);
            color: var(--success);
            border: 1px solid rgba(0, 255, 136, 0.3);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--success);
            box-shadow: 0 0 8px var(--success);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.85); }
            100% { opacity: 1; transform: scale(1); }
        }

        /* Voice Central Controller */
        .voice-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 24px 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            position: relative;
            overflow: hidden;
        }

        .mic-btn-wrapper {
            position: relative;
            margin: 16px 0;
        }

        .mic-glow {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 140px;
            height: 140px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(0, 240, 255, 0.25) 0%, transparent 70%);
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .mic-btn-wrapper.recording .mic-glow {
            opacity: 1;
            animation: pulseGlow 1.2s infinite;
        }

        @keyframes pulseGlow {
            0% { transform: translate(-50%, -50%) scale(0.9); opacity: 0.5; }
            50% { transform: translate(-50%, -50%) scale(1.3); opacity: 0.9; }
            100% { transform: translate(-50%, -50%) scale(0.9); opacity: 0.5; }
        }

        .mic-btn {
            width: 96px;
            height: 96px;
            border-radius: 50%;
            background: linear-gradient(135deg, #121d2d, #1a273b);
            border: 2px solid var(--cyan-glow);
            color: var(--cyan-glow);
            font-size: 38px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 0 25px rgba(0, 240, 255, 0.25);
            transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            outline: none;
        }

        .mic-btn:active, .mic-btn-wrapper.recording .mic-btn {
            background: linear-gradient(135deg, var(--cyan-glow), var(--purple-glow));
            color: #000;
            border-color: #fff;
            transform: scale(0.94);
            box-shadow: 0 0 40px rgba(0, 240, 255, 0.8);
        }

        .voice-status-text {
            font-size: 15px;
            font-weight: 600;
            color: var(--text-dim);
            margin-top: 6px;
        }

        .voice-status-text.active {
            color: var(--cyan-glow);
            text-shadow: 0 0 10px rgba(0, 240, 255, 0.5);
        }

        /* Live Dialogue Log */
        .dialogue-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 18px;
            padding: 16px;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .card-header {
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            color: var(--cyan-glow);
            text-transform: uppercase;
            letter-spacing: 1px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .speech-bubble {
            padding: 12px 14px;
            border-radius: 12px;
            font-size: 14px;
            line-height: 1.4;
        }

        .user-bubble {
            background: rgba(0, 240, 255, 0.08);
            border-left: 3px solid var(--cyan-glow);
            color: #fff;
        }

        .zen-bubble {
            background: rgba(121, 40, 202, 0.1);
            border-left: 3px solid var(--purple-glow);
            color: #e0d4ff;
        }

        /* Quick Control Actions */
        .controls-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }

        .action-btn {
            background: rgba(18, 26, 42, 0.85);
            border: 1px solid rgba(0, 240, 255, 0.15);
            padding: 14px 12px;
            border-radius: 14px;
            color: var(--text-main);
            font-family: 'Outfit', sans-serif;
            font-size: 14px;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .action-btn:active {
            transform: scale(0.96);
            background: rgba(0, 240, 255, 0.15);
            border-color: var(--cyan-glow);
        }

        .action-btn.unlock-btn {
            grid-column: span 2;
            background: linear-gradient(135deg, rgba(0, 240, 255, 0.15), rgba(121, 40, 202, 0.15));
            border-color: rgba(0, 240, 255, 0.4);
            font-size: 15px;
            padding: 16px;
        }

        /* Live Screen Modal / Viewer */
        .screen-preview {
            width: 100%;
            border-radius: 12px;
            border: 1px solid var(--card-border);
            display: none;
            margin-top: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        }

        /* Typed Command Bar */
        .container {
            width: 100%;
            max-width: 480px;
            display: flex;
            flex-direction: column;
            gap: 16px;
            padding-bottom: calc(110px + env(safe-area-inset-bottom));
        }

        .text-input-bar {
            display: flex;
            gap: 8px;
            background: rgba(16, 22, 34, 0.95);
            border: 1px solid var(--card-border);
            padding: 8px 8px 8px 16px;
            border-radius: 16px;
            margin-bottom: calc(40px + env(safe-area-inset-bottom));
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
        }

        .text-input-bar input {
            flex: 1;
            background: transparent;
            border: none;
            color: #fff;
            font-family: 'Outfit', sans-serif;
            font-size: 15px;
            outline: none;
        }

        .text-input-bar button {
            background: var(--cyan-glow);
            color: #000;
            border: none;
            border-radius: 10px;
            padding: 10px 18px;
            font-weight: 700;
            cursor: pointer;
        }
    </style>
</head>
<body>

<div class="container">
    <!-- Header -->
    <div class="header">
        <div class="brand">
            <div class="brand-icon">⚡</div>
            <div>
                <div class="brand-title">Z.E.N. MOBILE</div>
                <div style="font-size: 11px; color: var(--text-dim);">Sir Abdullah Irfan Portal</div>
            </div>
        </div>
        <div class="status-badge" id="portal-status">
            <div class="status-dot"></div>
            <span>CONNECTED</span>
        </div>
    </div>

    <!-- Voice Control Card -->
    <div class="voice-card">
        <div style="font-size: 13px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 1px;">iPhone Voice Stream</div>
        
        <div class="mic-btn-wrapper" id="mic-wrapper">
            <div class="mic-glow"></div>
            <button class="mic-btn" id="mic-btn">🎙️</button>
        </div>

        <div class="voice-status-text" id="voice-label">Tap to Speak with ZEN</div>
    </div>

    <!-- Dialogue Bubble -->
    <div class="dialogue-card">
        <div class="card-header">
            <span>Live Transmission</span>
            <span id="audio-indicator" style="color: var(--success); font-size: 11px; cursor: pointer;" onclick="replayLastAudio()">🔊 Speaker Active</span>
        </div>
        <div class="speech-bubble user-bubble" id="user-transcript">
            Tap the mic button or type below to send commands to your laptop.
        </div>
        <div class="speech-bubble zen-bubble" id="zen-reply">
            <div id="zen-reply-text">Sir, ZEN mobile link tayyar hai. Hukum kijiye?</div>
            <div style="margin-top: 8px; display: flex; justify-content: flex-end;">
                <button id="replay-btn" onclick="replayLastAudio()" style="background: rgba(0,240,255,0.15); border: 1px solid rgba(0,240,255,0.4); color: #00f0ff; padding: 4px 10px; border-radius: 8px; font-size: 11px; font-weight: 600; cursor: pointer;">🔊 Replay Voice</button>
            </div>
        </div>
    </div>

    <!-- Quick Control Actions -->
    <div class="controls-grid">
        <button class="action-btn toggle-display-btn" id="display-toggle-btn" style="grid-column: span 2; background: linear-gradient(135deg, rgba(0, 240, 255, 0.15), rgba(121, 40, 202, 0.15)); border-color: rgba(0, 240, 255, 0.4); font-size: 15px; padding: 15px;" onclick="toggleDisplayPower()">
            🖥️ Display: ON (Tap to Black)
        </button>
        <button class="action-btn" onclick="toggleScreen()">
            🖥️ View Screen
        </button>
        <button class="action-btn" onclick="triggerAction('close_apps')">
            🛑 Close All Windows Apps
        </button>
        <button class="action-btn" onclick="triggerAction('toggle_bt')">
            📶 Toggle Bluetooth
        </button>
        <button class="action-btn" onclick="confirmShutdown()">
            ⚡ Shutdown PC
        </button>
        <button class="action-btn" onclick="triggerAction('backtest_report')">
            📈 Backtest Report
        </button>
        <button class="action-btn" onclick="triggerAction('check_bot')">
            🤖 Check Bot
        </button>
    </div>

    <!-- Cyberpunk Confirmation Modal for Shutdown -->
    <div id="shutdown-modal" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.82); z-index: 99999; backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); align-items: center; justify-content: center; padding: 20px;">
        <div style="background: #0e1422; border: 1px solid rgba(255, 0, 85, 0.5); border-radius: 20px; padding: 24px; max-width: 360px; width: 100%; box-shadow: 0 0 35px rgba(255, 0, 85, 0.35); text-align: center; display: flex; flex-direction: column; gap: 14px;">
            <div style="font-size: 40px; filter: drop-shadow(0 0 10px rgba(255, 0, 85, 0.6));">⚠️</div>
            <div style="font-family: 'Outfit', sans-serif; font-size: 18px; font-weight: 700; color: #fff;">Confirm System Shutdown?</div>
            <div style="font-size: 13.5px; color: var(--text-dim); line-height: 1.45;">Sir, kya aap sach mein PC / Laptop shutdown karna chahte hain? Tamam running tasks close ho jayenge.</div>
            <div style="display: flex; gap: 10px; margin-top: 8px;">
                <button onclick="closeShutdownModal()" style="flex: 1; background: rgba(255,255,255,0.08); border: 1px solid var(--card-border); color: #fff; padding: 12px; border-radius: 12px; font-weight: 600; font-size: 14px; cursor: pointer;">Cancel</button>
                <button onclick="executeShutdown()" style="flex: 1; background: linear-gradient(135deg, #ff0055, #ff3366); border: none; color: #fff; padding: 12px; border-radius: 12px; font-weight: 700; font-size: 14px; cursor: pointer; box-shadow: 0 0 18px rgba(255, 0, 85, 0.5);">Yes, Shutdown</button>
            </div>
        </div>
    </div>

    <!-- Real-time Desktop Screen Viewer Container -->
    <div id="screen-container" style="display: none; width: 100%; flex-direction: column; gap: 8px; background: rgba(16, 22, 34, 0.85); border: 1px solid var(--card-border); padding: 12px; border-radius: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 13px; color: var(--cyan-glow); font-family: 'JetBrains Mono', monospace;">
            <span id="screen-status-text">🖥️ Live Desktop Feed</span>
            <div style="display: flex; gap: 8px;">
                <button onclick="refreshScreen()" style="background: rgba(0,240,255,0.15); color: #00f0ff; border: 1px solid rgba(0,240,255,0.4); padding: 5px 12px; border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer;">🔄 Refresh</button>
                <button onclick="toggleScreen()" style="background: rgba(255,0,85,0.15); color: #ff0055; border: 1px solid rgba(255,0,85,0.4); padding: 5px 12px; border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer;">✕ Close</button>
            </div>
        </div>
        <img id="desktop-screen-img" alt="Desktop Screen" style="display: block; width: 100%; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);" />
    </div>

    <!-- Typed Command Bar -->
    <form class="text-input-bar" onsubmit="sendTextMessage(event)">
        <input type="text" id="cmd-input" placeholder="Type command in Urdu, Hindi or English..." />
        <button type="submit">Send</button>
    </form>
</div>

<!-- Audio Player for ZEN Spoken Voice -->
<audio id="tts-audio" playsinline preload="auto"></audio>

<script>
    let mediaRecorder = null;
    let audioChunks = [];
    let isRecording = false;
    let lastAudioBase64 = null;
    let lastAudioBlobUrl = null;

    const micBtn = document.getElementById('mic-btn');
    const micWrapper = document.getElementById('mic-wrapper');
    const voiceLabel = document.getElementById('voice-label');
    const userTranscript = document.getElementById('user-transcript');
    const zenReplyText = document.getElementById('zen-reply-text');
    const ttsAudio = document.getElementById('tts-audio');
    const audioIndicator = document.getElementById('audio-indicator');

    let audioCtx = null;
    function unlockIOSAudio() {
        try {
            if (!audioCtx) {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            }
            if (audioCtx.state === 'suspended') {
                audioCtx.resume();
            }
            // Prime HTML5 Audio element on user tap
            ttsAudio.play().then(() => { ttsAudio.pause(); }).catch(() => {});
        } catch (e) {}
    }

    // Automatically unlock audio on first touch anywhere on iPhone screen
    document.addEventListener('touchstart', unlockIOSAudio, { passive: true });
    document.addEventListener('click', unlockIOSAudio, { passive: true });

    // Play synthesized speech audio from Base64 via Blob URL
    function playTTSAudio(base64Audio) {
        if (!base64Audio) return;
        lastAudioBase64 = base64Audio;
        
        try {
            const binaryString = atob(base64Audio);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            
            if (lastAudioBlobUrl) {
                URL.revokeObjectURL(lastAudioBlobUrl);
            }
            const blob = new Blob([bytes], { type: 'audio/mpeg' });
            lastAudioBlobUrl = URL.createObjectURL(blob);
            
            ttsAudio.pause();
            ttsAudio.src = lastAudioBlobUrl;
            ttsAudio.currentTime = 0;
            
            const p = ttsAudio.play();
            if (p !== undefined) {
                p.then(() => {
                    audioIndicator.textContent = "🔊 Playing Audio...";
                    audioIndicator.style.color = "#00f0ff";
                    ttsAudio.onended = () => {
                        audioIndicator.textContent = "🔊 Speaker Active";
                        audioIndicator.style.color = "var(--success)";
                    };
                }).catch(async (err) => {
                    console.warn("HTML5 audio play blocked, falling back to Web Audio API:", err);
                    audioIndicator.textContent = "🔊 Tap Replay to Hear";
                    audioIndicator.style.color = "#ffaa00";
                    // Fallback Web Audio
                    try {
                        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                        if (audioCtx.state === 'suspended') await audioCtx.resume();
                        const decodedBuffer = await audioCtx.decodeAudioData(bytes.buffer.slice(0));
                        const src = audioCtx.createBufferSource();
                        src.buffer = decodedBuffer;
                        src.connect(audioCtx.destination);
                        src.start(0);
                    } catch (e2) {
                        console.error("Web Audio fallback error:", e2);
                    }
                });
            }
        } catch (err) {
            console.error("playTTSAudio general error:", err);
        }
    }

    function replayLastAudio() {
        unlockIOSAudio();
        if (lastAudioBase64) {
            playTTSAudio(lastAudioBase64);
        } else if (lastAudioBlobUrl) {
            ttsAudio.src = lastAudioBlobUrl;
            ttsAudio.play().catch(e => console.log(e));
        }
    }

    // Toggle Desktop Screen Live Image
    function toggleScreen() {
        const container = document.getElementById('screen-container');
        if (container.style.display === 'flex') {
            container.style.display = 'none';
        } else {
            refreshScreen();
            container.style.display = 'flex';
            setTimeout(() => { container.scrollIntoView({ behavior: 'smooth' }); }, 150);
        }
    }

    function refreshScreen() {
        const screenImg = document.getElementById('desktop-screen-img');
        const statusText = document.getElementById('screen-status-text');
        statusText.textContent = "⏳ Capturing Desktop...";
        const newImg = new Image();
        newImg.onload = () => {
            screenImg.src = newImg.src;
            statusText.textContent = "🖥️ Live Desktop (" + new Date().toLocaleTimeString() + ")";
        };
        newImg.onerror = () => {
            statusText.textContent = "❌ Capture failed (PC locked or asleep)";
        };
        newImg.src = "/api/screenshot?t=" + new Date().getTime();
    }

    // Start / Stop Microphone Recording
    micBtn.addEventListener('click', async () => {
        if (!isRecording) {
            startRecording();
        } else {
            stopRecording();
        }
    });

    async function startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            audioChunks = [];
            
            // Prefer WAV/WebM container
            let options = {};
            if (MediaRecorder.isTypeSupported('audio/webm')) {
                options = { mimeType: 'audio/webm' };
            }
            
            mediaRecorder = new MediaRecorder(stream, options);
            mediaRecorder.ondataavailable = event => {
                if (event.data.size > 0) audioChunks.push(event.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/wav' });
                stream.getTracks().forEach(track => track.stop());
                await uploadVoiceCommand(audioBlob);
            };

            mediaRecorder.start();
            isRecording = true;
            micWrapper.classList.add('recording');
            voiceLabel.textContent = "Listening... Tap to Send";
            voiceLabel.classList.add('active');
        } catch (err) {
            alert("Microphone access permission required on iPhone: " + err);
        }
    }

    function stopRecording() {
        if (mediaRecorder && isRecording) {
            mediaRecorder.stop();
            isRecording = false;
            micWrapper.classList.remove('recording');
            voiceLabel.textContent = "Processing Command...";
            voiceLabel.classList.remove('active');
        }
    }

    async function uploadVoiceCommand(blob) {
        const formData = new FormData();
        formData.append("audio", blob, "voice.wav");

        try {
            userTranscript.textContent = "Transcribing audio from iPhone...";
            zenReplyText.textContent = "ZEN is thinking...";

            const res = await fetch("/api/voice_command", {
                method: "POST",
                body: formData
            });
            const data = await res.json();

            if (data.status === "success") {
                userTranscript.textContent = "🗣️ " + data.transcription;
                zenReplyText.textContent = "⚡ " + data.reply_text;
                voiceLabel.textContent = "Tap to Speak with ZEN";
                if (data.audio_base64) {
                    playTTSAudio(data.audio_base64);
                }
            } else {
                zenReplyText.textContent = "❌ " + data.reply_text;
                voiceLabel.textContent = "Tap to Speak with ZEN";
            }
        } catch (e) {
            zenReplyText.textContent = "Network Error: " + e;
            voiceLabel.textContent = "Tap to Speak with ZEN";
        }
    }

    async function sendTextMessage(e) {
        e.preventDefault();
        unlockIOSAudio();
        const input = document.getElementById('cmd-input');
        const text = input.value.trim();
        if (!text) return;
        input.value = "";

        userTranscript.textContent = "⌨️ " + text;
        zenReplyText.textContent = "ZEN is executing...";

        try {
            const res = await fetch("/api/text_command", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: text })
            });
            const data = await res.json();
            if (data.status === "success") {
                zenReplyText.textContent = "⚡ " + data.reply_text;
                if (data.audio_base64) {
                    playTTSAudio(data.audio_base64);
                }
            }
        } catch (err) {
            zenReplyText.textContent = "Error: " + err;
        }
    }

    let isDisplayOn = true;

    async function toggleDisplayPower() {
        unlockIOSAudio();
        const btn = document.getElementById('display-toggle-btn');
        isDisplayOn = !isDisplayOn;
        if (!isDisplayOn) {
            btn.innerHTML = '🌑 Display: BLACK (Tap to Wake)';
            btn.style.background = 'linear-gradient(135deg, rgba(121, 40, 202, 0.35), rgba(16, 22, 34, 0.8))';
            btn.style.borderColor = 'rgba(121, 40, 202, 0.6)';
            triggerAction('screen_off');
        } else {
            btn.innerHTML = '🖥️ Display: ON (Tap to Black)';
            btn.style.background = 'linear-gradient(135deg, rgba(0, 240, 255, 0.15), rgba(121, 40, 202, 0.15))';
            btn.style.borderColor = 'rgba(0, 240, 255, 0.4)';
            triggerAction('wake_screen');
        }
    }

    async function triggerAction(actionName) {
        unlockIOSAudio();
        zenReplyText.textContent = "Executing " + actionName + "...";
        try {
            const res = await fetch("/api/quick_action", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: actionName })
            });
            const data = await res.json();
            zenReplyText.textContent = "⚡ " + data.message;
            if (data.display_state) {
                const btn = document.getElementById('display-toggle-btn');
                if (data.display_state === 'off') {
                    isDisplayOn = false;
                    btn.innerHTML = '🌑 Display: BLACK (Tap to Wake)';
                    btn.style.background = 'linear-gradient(135deg, rgba(121, 40, 202, 0.35), rgba(16, 22, 34, 0.8))';
                    btn.style.borderColor = 'rgba(121, 40, 202, 0.6)';
                } else {
                    isDisplayOn = true;
                    btn.innerHTML = '🖥️ Display: ON (Tap to Black)';
                    btn.style.background = 'linear-gradient(135deg, rgba(0, 240, 255, 0.15), rgba(121, 40, 202, 0.15))';
                    btn.style.borderColor = 'rgba(0, 240, 255, 0.4)';
                }
            }
            if (data.audio_base64) {
                playTTSAudio(data.audio_base64);
            }
        } catch (e) {
            zenReplyText.textContent = "Error: " + e;
        }
    }

    function confirmShutdown() {
        unlockIOSAudio();
        const modal = document.getElementById('shutdown-modal');
        if (modal) modal.style.display = 'flex';
    }

    function closeShutdownModal() {
        const modal = document.getElementById('shutdown-modal');
        if (modal) modal.style.display = 'none';
    }

    async function executeShutdown() {
        closeShutdownModal();
        zenReplyText.textContent = "⚡ Initiating System Shutdown...";
        await triggerAction('shutdown');
    }
</script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)

def start_cloudflare_tunnel(port: int = 5050):
    """Spawns Cloudflare Tunnel to provide free public trusted HTTPS URL for iPhone Safari."""
    cloudflared_path = os.path.join(os.path.dirname(__file__), "temp", "cloudflared.exe")
    if not os.path.exists(cloudflared_path):
        cloudflared_path = r"F:\Agent\temp\cloudflared.exe"
    if not os.path.exists(cloudflared_path):
        cloudflared_path = r"F:\Zen Agent\Zen Ai\temp\cloudflared.exe"
    if not os.path.exists(cloudflared_path):
        return None
        
    import subprocess
    import threading
    import re
    
    tunnel_cmd = [cloudflared_path, "tunnel", "--url", f"http://127.0.0.1:{port}"]
    
    def run_tunnel():
        try:
            proc = subprocess.Popen(
                tunnel_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
                bufsize=1
            )
            url_printed = False
            for line in iter(proc.stdout.readline, ''):
                matches = re.findall(r"https://([a-zA-Z0-9-]+)\.trycloudflare\.com", line)
                for sub in matches:
                    if sub.lower() not in ["api", "pkg", "admin", "www"] and not url_printed:
                        public_url = f"https://{sub}.trycloudflare.com"
                        url_printed = True
                        print("\n" + "="*70)
                        print(f"🌍 100% FREE PUBLIC HTTPS LINK FOR iPHONE 12 PRO (JAZZ 4G):")
                        print(f"👉 {public_url}")
                        print(f"🔒 (Open this in iPhone Safari - Full Microphone Stream Active!)")
                        print("="*70 + "\n", flush=True)
                        break
        except Exception as e:
            logger.debug(f"Cloudflare tunnel notice: {e}")
                
    t = threading.Thread(target=run_tunnel, daemon=True)
    t.start()

def free_port(target_port: int = 5050):
    """Kills any stale process occupying the target port to prevent WinError 10048."""
    try:
        import subprocess
        ps_cmd = f"Get-NetTCPConnection -LocalPort {target_port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess"
        res = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
        current_pid = os.getpid()
        for pid_str in res.stdout.strip().split():
            try:
                pid = int(pid_str)
                if pid != current_pid and pid > 0:
                    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
            except Exception:
                pass
    except Exception:
        pass

if __name__ == "__main__":
    port = 5050
    free_port(port)
    start_cloudflare_tunnel(port)
    
    cert_path = os.path.join(os.path.dirname(__file__), "certs", "cert.pem")
    key_path = os.path.join(os.path.dirname(__file__), "certs", "key.pem")
    if not os.path.exists(cert_path):
        cert_path = r"F:\Agent\certs\cert.pem"
        key_path = r"F:\Agent\certs\key.pem"
        
    ssl_kwargs = {}
    if os.path.exists(cert_path) and os.path.exists(key_path):
        ssl_kwargs = {
            "ssl_certfile": cert_path,
            "ssl_keyfile": key_path
        }
        scheme = "https"
    else:
        scheme = "http"

    print(f"\n=======================================================")
    print(f"[Z.E.N.] MOBILE WEB AUDIO PORTAL ACTIVE (SSL SECURE)!")
    print(f"Tailscale IP: {scheme}://100.78.166.75:{port}")
    print(f"Local Wi-Fi:  {scheme}://192.168.3.14:{port}")
    print(f"=======================================================\n")
    
    # Run uvicorn server on port 5050 with SSL
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        **ssl_kwargs
    )
