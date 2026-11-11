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
    """Synthesizes text to speech with Edge-TTS (with timeout) and returns base64 MP3.
    Natural Male voice with smooth Roman Urdu pronunciation and fast flow.
    """
    if not text:
        return None
        
    import re
    # 1. Clean Markdown & Code artifacts
    cleaned = re.sub(r'[*_#`~]', '', text).strip()
    
    # 2. Phonetic Normalization for Roman Urdu:
    # Fixes 'hai' / 'he' -> 'hh' so TTS pronounces crisp short 'hh' instead of dragging 'haa-eey'
    cleaned = re.sub(r'\b(hai|he)\b', 'heh', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bhain\b', 'hein', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bmain\b', 'mein', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bkia\b', 'kya', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\bboht\b', 'bohot', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    if not cleaned:
        return None

    # Preferred male voices: Madhur (natural fluent Hinglish/Urdu flow) followed by Asad
    male_voices = [
        getattr(config, "TTS_VOICE_HINDI", "hi-IN-MadhurNeural"),
        getattr(config, "TTS_VOICE_URDU", "ur-PK-AsadNeural"),
        "ur-IN-SalmanNeural"
    ]
    pitch = getattr(config, "TTS_PITCH", "-3Hz")
    rate = getattr(config, "TTS_RATE", "+12%")

    try:
        import edge_tts
        for voice in male_voices:
            try:
                communicate = edge_tts.Communicate(
                    text=cleaned,
                    voice=voice,
                    rate=rate,
                    pitch=pitch
                )
                audio_stream = io.BytesIO()
                
                async def _stream():
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_stream.write(chunk["data"])
                            
                # Allow 14s timeout for full network stream completion
                await asyncio.wait_for(_stream(), timeout=14.0)
                audio_bytes = audio_stream.getvalue()
                if audio_bytes and len(audio_bytes) > 200:
                    logger.info(f"Edge-TTS Natural Male voice [{voice}] generated {len(audio_bytes)} bytes")
                    return base64.b64encode(audio_bytes).decode("utf-8")
            except Exception as v_err:
                logger.debug(f"Male voice [{voice}] notice ({v_err}), trying next fallback...")
                continue
    except Exception as e:
        logger.warning(f"Edge-TTS male voice engine notice: {e}")

    # 2. Emergency Fallback: Google TTS (Only if all male Edge voices are unreachable)
    try:
        from gtts import gTTS
        gtts_lang = "hi" if config.JARVIS_LANGUAGE in ["urdu", "hindi", "bilingual"] else "en"
        def _run_gtts():
            stream = io.BytesIO()
            tts = gTTS(text=cleaned, lang=gtts_lang)
            tts.write_to_fp(stream)
            return stream.getvalue()
            
        gtts_bytes = await asyncio.to_thread(_run_gtts)
        if gtts_bytes and len(gtts_bytes) > 200:
            logger.info(f"Emergency gTTS generated {len(gtts_bytes)} bytes")
            return base64.b64encode(gtts_bytes).decode("utf-8")
    except Exception as ge:
        logger.error(f"Error in emergency fallback: {ge}")

    return None

@app.get("/static/web_3d_particles.json")
async def get_web_3d_particles():
    """Serves real 3D dense reference particles for web portal."""
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "web_3d_particles.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return Response(content=f.read(), media_type="application/json")
    raise HTTPException(status_code=404, detail="3D particles not found")

@app.get("/static/head_scanlines.json")
async def get_head_scanlines():
    """Serves real 3D head scanline mesh points."""
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "head_scanlines.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return Response(content=f.read(), media_type="application/json")
    raise HTTPException(status_code=404, detail="Head scanlines not found")

@app.get("/static/hologram_face.png")
async def get_hologram_face():
    """Serves the real 3D blended hologram face texture matching Image 1."""
    face_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "hologram_face.png")
    if os.path.exists(face_path):
        with open(face_path, "rb") as f:
            return Response(content=f.read(), media_type="image/png")
    raise HTTPException(status_code=404, detail="Hologram face texture not found")

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

@app.post("/api/dictate_stt")
async def api_dictate_stt(audio: UploadFile = File(...)):
    """Receives recorded audio from browser mic and transcribes into English or Roman Urdu using English alphabets."""
    try:
        audio_bytes = await audio.read()
        if len(audio_bytes) < 600:
            return {"status": "error", "text": ""}

        from groq import Groq
        groq_client = Groq(api_key=config.GROQ_API_KEY, timeout=6.0)

        prompt_guide = (
            "Transcribe speech accurately. If speech is in English, transcribe in standard English. "
            "If speech is in Urdu or Hindi, transcribe strictly in Roman Urdu using English alphabets (Latin characters), "
            "e.g.: kya haal he, brightness 25 kardo, scalper bot check karo, reports dikhao, system status batao."
        )

        transcription_resp = groq_client.audio.transcriptions.create(
            file=("dictation.wav", audio_bytes, "audio/wav"),
            model="whisper-large-v3-turbo",
            prompt=prompt_guide,
            temperature=0.0
        )
        text = transcription_resp.text.strip() if transcription_resp else ""

        # Check if non-Latin Urdu/Arabic or Devanagari script is present
        has_non_latin = any(('\u0600' <= c <= '\u06FF') or ('\u0900' <= c <= '\u097F') for c in text)
        if has_non_latin and config.GROQ_API_KEY:
            try:
                import re
                resp = groq_client.chat.completions.create(
                    model=config.GROQ_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a transliterator. Transliterate Urdu or Hindi text into natural Roman Urdu using standard English alphabet (e.g. 'kya haal he', 'brightness 25 kardo'). Keep English words in English. Return ONLY the Roman Urdu text without explanations or quotes."
                        },
                        {"role": "user", "content": text}
                    ],
                    temperature=0.0,
                    max_tokens=80
                )
                roman = resp.choices[0].message.content.strip()
                roman = re.sub(r"<think>.*?</think>", "", roman, flags=re.DOTALL).strip('\"\' ')
                if roman:
                    text = roman
            except Exception as tr_err:
                logger.debug(f"Transliteration error: {tr_err}")

        return {"status": "success", "text": text}
    except Exception as e:
        logger.error(f"Error in api_dictate_stt: {e}")
        return {"status": "error", "text": "", "error": str(e)}

@app.get("/api/system_vitals")
async def api_system_vitals():
    """Returns real-time CPU, RAM, and Battery percentages for portal telemetry."""
    import psutil
    try:
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        batt = psutil.sensors_battery()
        batt_pct = batt.percent if batt else 100
        is_plugged = batt.power_plugged if batt else True
        return {
            "status": "success",
            "cpu": cpu,
            "ram": ram,
            "battery": batt_pct,
            "plugged": is_plugged
        }
    except Exception:
        return {"status": "error", "cpu": 0, "ram": 0, "battery": 100, "plugged": True}

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
    """Returns stunning Cyberpunk Panoramic Web Portal for Desktop & Mobile."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Z.E.N. // Command Center HUD</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #060911;
            --card-bg: rgba(14, 20, 32, 0.85);
            --card-border: rgba(0, 240, 255, 0.18);
            --cyan-glow: #00f0ff;
            --blue-accent: #0284c7;
            --purple-glow: #a855f7;
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
                radial-gradient(circle at 50% 0%, rgba(0, 240, 255, 0.09) 0%, transparent 50%),
                radial-gradient(circle at 100% 100%, rgba(168, 85, 247, 0.08) 0%, transparent 50%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        /* Responsive Panoramic Grid */
        .portal-layout {
            width: 100%;
            max-width: 480px;
            display: flex;
            flex-direction: column;
            gap: 16px;
            padding-bottom: 24px;
            transition: all 0.3s ease;
        }

        @media (min-width: 1024px) {
            .portal-layout {
                max-width: 1440px;
                display: grid;
                grid-template-columns: 310px 1fr 340px;
                gap: 20px;
                align-items: start;
            }
        }

        .side-col {
            display: none;
            flex-direction: column;
            gap: 16px;
        }

        @media (min-width: 1024px) {
            .side-col {
                display: flex;
            }
        }

        .center-col {
            display: flex;
            flex-direction: column;
            gap: 16px;
            width: 100%;
        }

        /* Generic Glass Card */
        .glass-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 18px;
            padding: 16px;
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        }

        /* Header */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 14px 18px;
            border-radius: 18px;
            backdrop-filter: blur(12px);
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .brand-icon {
            width: 34px;
            height: 34px;
            border-radius: 10px;
            background: linear-gradient(135deg, var(--cyan-glow), var(--purple-glow));
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 17px;
            color: #000;
            box-shadow: 0 0 16px rgba(0, 240, 255, 0.45);
        }

        .brand-title {
            font-weight: 700;
            font-size: 18px;
            letter-spacing: 1px;
            color: #fff;
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .fullscreen-btn {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid var(--card-border);
            color: #00f0ff;
            padding: 6px 12px;
            border-radius: 10px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .fullscreen-btn:hover {
            background: rgba(0, 240, 255, 0.15);
            border-color: var(--cyan-glow);
        }

        .status-badge {
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            font-weight: 600;
            padding: 5px 11px;
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

        /* Canvas AI Hologram Visualizer */
        .canvas-card {
            background: #080d1a;
            border: 1px solid var(--card-border);
            border-radius: 22px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            position: relative;
            overflow: hidden;
            box-shadow: 0 8px 35px rgba(0,0,0,0.6);
        }

        #visualizer-canvas {
            width: 100%;
            max-width: 440px;
            height: 220px;
            display: block;
        }

        /* Voice Central Controller */
        .voice-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 22px;
            padding: 20px 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            position: relative;
            overflow: hidden;
        }

        .mic-btn-wrapper {
            position: relative;
            margin: 12px 0;
        }

        .mic-glow {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 130px;
            height: 130px;
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
            width: 88px;
            height: 88px;
            border-radius: 50%;
            background: linear-gradient(135deg, #121d2d, #1a273b);
            border: 2px solid var(--cyan-glow);
            color: var(--cyan-glow);
            font-size: 34px;
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
            font-size: 14px;
            font-weight: 600;
            color: var(--text-dim);
            margin-top: 4px;
        }

        .voice-status-text.active {
            color: var(--cyan-glow);
            text-shadow: 0 0 10px rgba(0, 240, 255, 0.5);
        }

        /* Dialogue Box */
        .dialogue-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 18px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .card-header {
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
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
            line-height: 1.45;
        }

        .user-bubble {
            background: rgba(0, 240, 255, 0.08);
            border-left: 3px solid var(--cyan-glow);
            color: #fff;
        }

        .zen-bubble {
            background: rgba(168, 85, 247, 0.1);
            border-left: 3px solid var(--purple-glow);
            color: #e0d4ff;
        }

        /* Controls Grid */
        .controls-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }

        .action-btn {
            background: rgba(18, 26, 42, 0.85);
            border: 1px solid rgba(0, 240, 255, 0.15);
            padding: 13px 12px;
            border-radius: 14px;
            color: var(--text-main);
            font-family: 'Outfit', sans-serif;
            font-size: 13.5px;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .action-btn:hover {
            border-color: var(--cyan-glow);
            background: rgba(0, 240, 255, 0.12);
        }

        .action-btn:active {
            transform: scale(0.96);
        }

        /* Typed Command Bar with Integrated Dictation Mic */
        .text-input-bar {
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(14, 20, 32, 0.95);
            border: 1px solid var(--card-border);
            padding: 6px 8px 6px 14px;
            border-radius: 16px;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.7);
        }

        .text-input-bar input {
            flex: 1;
            background: transparent;
            border: none;
            color: #fff;
            font-family: 'Outfit', sans-serif;
            font-size: 14px;
            outline: none;
        }

        .dictate-btn {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(0, 240, 255, 0.3);
            color: #00f0ff;
            padding: 9px 13px;
            border-radius: 10px;
            font-size: 15px;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .dictate-btn.active {
            background: #ff0055;
            border-color: #ff0055;
            color: #fff;
            animation: pulse 1.2s infinite;
        }

        .send-btn {
            background: var(--blue-accent);
            color: #fff;
            border: none;
            border-radius: 10px;
            padding: 10px 18px;
            font-weight: 700;
            font-size: 13.5px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .send-btn:hover {
            background: #0369a1;
            box-shadow: 0 0 15px rgba(2, 132, 199, 0.5);
        }

        /* Left Sidebar: Telemetry & Terminal Logs */
        .vitals-meter {
            margin-bottom: 12px;
        }

        .meter-label {
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-dim);
            margin-bottom: 4px;
        }

        .meter-bar {
            width: 100%;
            height: 6px;
            background: #172238;
            border-radius: 4px;
            overflow: hidden;
        }

        .meter-fill {
            height: 100%;
            width: 0%;
            background: var(--cyan-glow);
            transition: width 0.5s ease;
        }

        .terminal-box {
            background: #050811;
            border: 1px solid #172238;
            border-radius: 12px;
            height: 340px;
            overflow-y: auto;
            padding: 10px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            line-height: 1.6;
        }

        .log-entry {
            margin-bottom: 6px;
        }

        .log-time { color: #475569; }
        .log-user { color: #38bdf8; }
        .log-tool { color: #fbbf24; }
        .log-zen { color: #34d399; }
        .log-sys { color: #94a3b8; }
        .log-err { color: #f87171; }

        /* Right Sidebar: Chat History Cards & Inspector */
        .chat-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 380px;
            overflow-y: auto;
            padding-right: 4px;
        }

        .chat-card {
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 10px 12px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .chat-card:hover {
            border-color: var(--cyan-glow);
            background: #131d35;
        }

        .chat-card-top {
            display: flex;
            justify-content: space-between;
            font-size: 10px;
            font-family: 'JetBrains Mono', monospace;
            color: #64748b;
            margin-bottom: 4px;
        }

        .chat-card-pill {
            padding: 2px 6px;
            border-radius: 6px;
            font-weight: 700;
            background: #1e1b4b;
            color: #c084fc;
        }

        .chat-card-pill.done {
            background: #064e3b;
            color: #34d399;
        }

        .chat-card-prompt {
            font-size: 12.5px;
            font-weight: 600;
            color: #e2e8f0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .inspector-box {
            background: #050811;
            border: 1px solid #172238;
            border-radius: 12px;
            padding: 12px;
            font-size: 12.5px;
            line-height: 1.5;
            color: #e2e8f0;
            max-height: 240px;
            overflow-y: auto;
        }
    </style>
</head>
<body>

<div class="portal-layout">
    <!-- LEFT SIDEBAR: Telemetry & Logs -->
    <div class="side-col">
        <div class="glass-card">
            <div class="card-header" style="margin-bottom: 12px;">
                <span>⚡ SYSTEM TELEMETRY</span>
                <span id="vitals-status" style="color: var(--success); font-size: 10px;">LIVE</span>
            </div>
            
            <div class="vitals-meter">
                <div class="meter-label">
                    <span>CPU LOAD</span>
                    <span id="cpu-val">0%</span>
                </div>
                <div class="meter-bar"><div class="meter-fill" id="cpu-fill"></div></div>
            </div>

            <div class="vitals-meter">
                <div class="meter-label">
                    <span>RAM USAGE</span>
                    <span id="ram-val">0%</span>
                </div>
                <div class="meter-bar"><div class="meter-fill" id="ram-fill" style="background: var(--purple-glow);"></div></div>
            </div>

            <div class="vitals-meter" style="margin-bottom: 6px;">
                <div class="meter-label">
                    <span>BATTERY</span>
                    <span id="batt-val">100% ⚡</span>
                </div>
            </div>

            <div style="font-size: 10.5px; color: #64748b; font-family: 'JetBrains Mono', monospace; margin-top: 8px; border-top: 1px solid #1e293b; padding-top: 8px;">
                CORE: Groq LPU + Gemini 3.7<br>
                VOICE: hi-IN-MadhurNeural (+12%)
            </div>
        </div>

        <div class="glass-card" style="flex: 1;">
            <div class="card-header" style="margin-bottom: 8px;">
                <span>TERMINAL LOGS</span>
                <button onclick="clearTerminal()" style="background: transparent; border: none; color: #64748b; font-size: 10px; cursor: pointer;">Clear</button>
            </div>
            <div class="terminal-box" id="terminal-feed">
                <div class="log-entry"><span class="log-time">[System]</span> <span class="log-sys">ZEN Panoramic HUD Initialized.</span></div>
                <div class="log-entry"><span class="log-time">[System]</span> <span class="log-sys">Dual Engine Ready: Groq LPU + Gemini.</span></div>
            </div>
        </div>
    </div>

    <!-- CENTER COLUMN: Holographic Core & Command -->
    <div class="center-col">
        <!-- Top Header -->
        <div class="header">
            <div class="brand">
                <div class="brand-icon">⚡</div>
                <div>
                    <div class="brand-title">Z.E.N. // CORE</div>
                    <div style="font-size: 11px; color: var(--text-dim);">Autonomous Workstation Controller</div>
                </div>
            </div>
            <div class="header-actions">
                <button class="fullscreen-btn" onclick="toggleFullscreen()">⛶ Fullscreen</button>
                <div class="status-badge" id="portal-status">
                    <div class="status-dot"></div>
                    <span id="portal-status-text">ONLINE</span>
                </div>
            </div>
        </div>

        <!-- Futuristic Holographic Visualizer Canvas -->
        <div class="canvas-card">
            <canvas id="visualizer-canvas" width="440" height="220"></canvas>
            
        </div>

        <!-- Dialogue Bubble -->
        <div class="dialogue-card">
            <div class="card-header">
                <span>Live Dialogue</span>
                <span id="audio-indicator" style="color: var(--success); font-size: 11px; cursor: pointer;" onclick="replayLastAudio()">🔊 Speaker Active</span>
            </div>
            <div class="speech-bubble user-bubble" id="user-transcript">
                Tap the mic below or type command to execute.
            </div>
            <div class="speech-bubble zen-bubble" id="zen-reply">
                <div id="zen-reply-text">Sir, ZEN Command Center online hai. Hukum kijiye?</div>
                <div style="margin-top: 8px; display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 10px; color: var(--text-dim);">🔊 Natural Male Voice Active</span>
                    <button id="replay-btn" onclick="replayLastAudio()" style="background: rgba(0,240,255,0.15); border: 1px solid rgba(0,240,255,0.4); color: #00f0ff; padding: 4px 10px; border-radius: 8px; font-size: 11.5px; font-weight: 600; cursor: pointer;">🔊 Replay</button>
                </div>
            </div>
        </div>

        <!-- Interactive Typed Command Bar (With Dictation Mic inside before Send) -->
        <form class="text-input-bar" onsubmit="sendTextMessage(event)">
            <input type="text" id="cmd-input" placeholder="Type command in Roman Urdu / English, or use mic..." autocomplete="off" />
            <button type="button" class="dictate-btn" id="dictate-btn" onclick="toggleTextDictation()" title="Voice Dictation (English / Roman Urdu)">
                🎙️ <span id="dictate-label" style="font-size: 11px; font-weight: 700;">Mic</span>
            </button>
            <button type="submit" class="send-btn" id="send-btn">⚡ Send</button>
        </form>

        <!-- Quick Control Actions -->
        <div class="controls-grid">
            <button class="action-btn toggle-display-btn" id="display-toggle-btn" style="grid-column: span 2; background: linear-gradient(135deg, rgba(0, 240, 255, 0.15), rgba(168, 85, 247, 0.15)); border-color: rgba(0, 240, 255, 0.4); font-size: 14.5px; padding: 14px;" onclick="toggleDisplayPower()">
                🖥️ Display: ON (Tap to Black)
            </button>
            <button class="action-btn" onclick="toggleScreen()">
                🖥️ View Screen
            </button>
            <button class="action-btn" onclick="triggerAction('close_apps')">
                🛑 Close Apps
            </button>
            <button class="action-btn" onclick="triggerAction('toggle_bt')">
                📶 Bluetooth
            </button>
            <button class="action-btn" onclick="triggerAction('check_bot')">
                🤖 Check Bot
            </button>
            <button class="action-btn" onclick="triggerAction('backtest_report')">
                📈 Backtest Report
            </button>
            <button class="action-btn" onclick="confirmShutdown()" style="color: #ff3366;">
                ⚡ Shutdown PC
            </button>
        </div>

        <!-- Desktop Screen Modal -->
        <div id="screen-container" style="display: none; width: 100%; flex-direction: column; gap: 8px; background: rgba(16, 22, 34, 0.9); border: 1px solid var(--card-border); padding: 12px; border-radius: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 13px; color: var(--cyan-glow); font-family: 'JetBrains Mono', monospace;">
                <span>🖥️ Live Desktop Feed</span>
                <div style="display: flex; gap: 8px;">
                    <button onclick="refreshScreen()" style="background: rgba(0,240,255,0.15); color: #00f0ff; border: 1px solid rgba(0,240,255,0.4); padding: 5px 12px; border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer;">🔄 Refresh</button>
                    <button onclick="toggleScreen()" style="background: rgba(255,0,85,0.15); color: #ff0055; border: 1px solid rgba(255,0,85,0.4); padding: 5px 12px; border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer;">✕ Close</button>
                </div>
            </div>
            <img id="desktop-screen-img" alt="Desktop Screen" style="display: block; width: 100%; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);" />
        </div>
    </div>

    <!-- RIGHT SIDEBAR: Chat History & Response Inspector -->
    <div class="side-col">
        <div class="glass-card" style="flex: 1;">
            <div class="card-header" style="margin-bottom: 4px;">
                <span>💬 CHATS & ACTIONS</span>
                <span style="font-size: 10px; color: #64748b;" id="chat-count">0 items</span>
            </div>
            <div style="font-size: 10.5px; color: var(--text-dim); margin-bottom: 10px;">Click card to inspect full response</div>
            
            <div class="chat-list" id="chat-cards-list">
                <!-- Chat cards dynamically appended here -->
            </div>
        </div>

        <div class="glass-card">
            <div class="card-header" style="margin-bottom: 8px;">
                <span>RESPONSE INSPECTOR</span>
            </div>
            <div class="inspector-box" id="inspector-content">
                Select any card above to view execution details and final response.
            </div>
        </div>
    </div>
</div>

<!-- Shutdown Modal -->
<div id="shutdown-modal" style="display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.85); z-index: 99999; backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); align-items: center; justify-content: center; padding: 20px;">
    <div style="background: #0e1422; border: 1px solid rgba(255, 0, 85, 0.5); border-radius: 20px; padding: 24px; max-width: 360px; width: 100%; box-shadow: 0 0 35px rgba(255, 0, 85, 0.35); text-align: center; display: flex; flex-direction: column; gap: 14px;">
        <div style="font-size: 40px; filter: drop-shadow(0 0 10px rgba(255, 0, 85, 0.6));">⚠️</div>
        <div style="font-family: 'Outfit', sans-serif; font-size: 18px; font-weight: 700; color: #fff;">Confirm PC Shutdown?</div>
        <div style="font-size: 13.5px; color: var(--text-dim); line-height: 1.45;">Sir, kya aap sach mein PC shutdown karna chahte hain? Tamam running tasks close ho jayenge.</div>
        <div style="display: flex; gap: 10px; margin-top: 8px;">
            <button onclick="closeShutdownModal()" style="flex: 1; background: rgba(255,255,255,0.08); border: 1px solid var(--card-border); color: #fff; padding: 12px; border-radius: 12px; font-weight: 600; font-size: 14px; cursor: pointer;">Cancel</button>
            <button onclick="executeShutdown()" style="flex: 1; background: linear-gradient(135deg, #ff0055, #ff3366); border: none; color: #fff; padding: 12px; border-radius: 12px; font-weight: 700; font-size: 14px; cursor: pointer; box-shadow: 0 0 18px rgba(255, 0, 85, 0.5);">Yes, Shutdown</button>
        </div>
    </div>
</div>

<audio id="tts-audio" playsinline preload="auto"></audio>

<script>
    // State
    let isRecording = false;
    let isDictating = false;
    let dictationRecorder = null;
    let dictationChunks = [];
    let lastAudioBase64 = null;
    let lastAudioBlobUrl = null;
    let chatCardsData = [];
    let currentAgentState = "IDLE";

    const userTranscript = document.getElementById('user-transcript');
    const zenReplyText = document.getElementById('zen-reply-text');
    const ttsAudio = document.getElementById('tts-audio');
    const audioIndicator = document.getElementById('audio-indicator');
    const cmdInput = document.getElementById('cmd-input');
    const dictateBtn = document.getElementById('dictate-btn');
    const dictateLabel = document.getElementById('dictate-label');
    const terminalFeed = document.getElementById('terminal-feed');
    const chatCardsList = document.getElementById('chat-cards-list');
    const inspectorContent = document.getElementById('inspector-content');
    const visualizerStatus = document.getElementById('visualizer-status-text');

    // Canvas Hologram Setup
    const canvas = document.getElementById('visualizer-canvas');
    const ctx = canvas.getContext('2d');

    // Real 3D Dense Holographic Head & Connectivity Engine
    let headPoints = null;
    let headColors = null;

    fetch("/static/web_3d_particles.json")
        .then(r => r.json())
        .then(data => {
            headPoints = new Float32Array(data.pts.flat());
            headColors = data.cols;
        })
        .catch(err => console.error("Error loading 3D particles:", err));

    // Organic Gaze & Angle Tracking
    let currentYaw = 0.0, currentPitch = 0.0, currentRoll = 0.0, currentDx = 0.0, currentDy = 0.0;
    let targetYaw = 0.0, targetPitch = 0.0, targetRoll = 0.0, targetDx = 0.0, targetDy = 0.0;
    let nextGazeTime = Date.now() + 1000;

    const phi = (1 + Math.sqrt(5)) / 2;
    const rawNodes = [
        [-1, phi, 0], [1, phi, 0], [-1, -phi, 0], [1, -phi, 0],
        [0, -1, phi], [0, 1, phi], [0, -1, -phi], [0, 1, -phi],
        [phi, 0, -1], [phi, 0, 1], [-phi, 0, -1], [-phi, 0, 1]
    ];
    const connectNodes = rawNodes.map(([x, y, z]) => [x * 46, y * 46, z * 46]);
    const connectEdges = [];
    for (let i = 0; i < connectNodes.length; i++) {
        for (let j = i + 1; j < connectNodes.length; j++) {
            const [x1, y1, z1] = connectNodes[i];
            const [x2, y2, z2] = connectNodes[j];
            const d = Math.sqrt((x1-x2)**2 + (y1-y2)**2 + (z1-z2)**2);
            if (d < 110) connectEdges.push([i, j]);
        }
    }

    function project3D(x, y, z, yaw, pitch, cx, cy) {
        const cosY = Math.cos(yaw), sinY = Math.sin(yaw);
        const x1 = x * cosY + z * sinY;
        const z1 = -x * sinY + z * cosY;
        const cosX = Math.cos(pitch), sinX = Math.sin(pitch);
        const y2 = y * cosX - z1 * sinX;
        const z2 = y * sinX + z1 * cosX;
        const fov = 380, dist = 320;
        const factor = fov / (z2 + dist);
        return [cx + x1 * factor, cy + y2 * factor, z2];
    }

    let t3d = 0.0;

    function renderVisualizer() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const cx = canvas.width / 2;
        const cy = canvas.height / 2;
        t3d += 0.05;

        const isProcessing = (currentAgentState === "THINKING" || currentAgentState === "PROCESSING" || currentAgentState === "EXECUTING");

        if (isProcessing) {
            // Render 3D Connectivity Working Cluster
            const yaw = t3d * 0.95, pitch = t3d * 0.70;
            const proj = connectNodes.map(([x, y, z]) => project3D(x, y, z, yaw, pitch, cx, cy));

            // Gyroscopic Rings
            ctx.strokeStyle = "#c084fc";
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            for (let i = 0; i <= 24; i++) {
                const th = i * Math.PI * 2 / 24;
                const [px, py] = project3D(120 * Math.cos(th), 120 * Math.sin(th) * 0.35, 0, yaw * 1.5, pitch, cx, cy);
                if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
            }
            ctx.stroke();

            ctx.strokeStyle = "#38bdf8";
            ctx.beginPath();
            for (let i = 0; i <= 24; i++) {
                const th = i * Math.PI * 2 / 24;
                const [px, py] = project3D(120 * Math.cos(th), 120 * Math.sin(th), 0, -yaw * 1.3, pitch * 1.4, cx, cy);
                if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
            }
            ctx.stroke();

            // Connections
            for (const [i1, i2] of connectEdges) {
                const [x1, y1, z1] = proj[i1];
                const [x2, y2, z2] = proj[i2];
                ctx.strokeStyle = (z1 + z2 > 0) ? "#a855f7" : "#4c1d95";
                ctx.lineWidth = (z1 + z2 > 10) ? 2 : 1;
                ctx.beginPath();
                ctx.moveTo(x1, y1);
                ctx.lineTo(x2, y2);
                ctx.stroke();
            }

            // Data Packets traveling
            for (let p = 0; p < 12; p++) {
                const [i1, i2] = connectEdges[(p * 3) % connectEdges.length];
                const [x1, y1] = proj[i1];
                const [x2, y2] = proj[i2];
                const prog = (t3d * 2.5 + p * 0.4) % 1.0;
                const pakX = x1 + (x2 - x1) * prog;
                const pakY = y1 + (y2 - y1) * prog;
                ctx.fillStyle = "#00f0ff";
                ctx.beginPath();
                ctx.arc(pakX, pakY, 3, 0, Math.PI * 2);
                ctx.fill();
            }

            // Nodes
            const sortedNodes = proj.map((p, i) => ({ p, i })).sort((a, b) => a.p[2] - b.p[2]);
            for (const item of sortedNodes) {
                const [px, py, pz] = item.p;
                const r = Math.max(3, 5.5 + pz * 0.035);
                ctx.fillStyle = pz > 0 ? "#c084fc" : "#6b21a8";
                ctx.strokeStyle = pz > 10 ? "#00f0ff" : "#818cf8";
                ctx.lineWidth = 1.2;
                ctx.beginPath();
                ctx.arc(px, py, r, 0, Math.PI * 2);
                ctx.fill();
                ctx.stroke();
            }

            // Power core
            ctx.fillStyle = "#0d1b2a";
            ctx.strokeStyle = "#00f0ff";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(cx, cy, 14, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();
            ctx.fillStyle = "#00f0ff";
            ctx.font = "bold 11px monospace";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText("⚡", cx, cy);

        } else {
            // Render Dense Real 3D Head Object matching Reference Image
            const now = Date.now();
            const isSpeaking = (currentAgentState === "SPEAKING");

            if (isSpeaking) {
                targetYaw = Math.sin(t3d * 3.2) * 0.08;
                targetPitch = Math.sin(t3d * 4.5) * 0.05;
                targetRoll = Math.sin(t3d * 2.5) * 0.03;
                targetDx = Math.sin(t3d * 2.0) * 5.0;
                targetDy = Math.sin(t3d * 2.8) * 3.5;
                nextGazeTime = now + 1200;
            } else if (now >= nextGazeTime) {
                if (Math.random() < 0.28) {
                    targetYaw = (Math.random() - 0.5) * 0.08;
                    targetPitch = (Math.random() - 0.5) * 0.06;
                    targetRoll = (Math.random() - 0.5) * 0.03;
                    targetDx = (Math.random() - 0.5) * 8;
                    targetDy = (Math.random() - 0.5) * 6;
                    nextGazeTime = now + 1800 + Math.random() * 1400;
                } else {
                    targetYaw = (Math.random() > 0.5 ? 1 : -1) * (0.16 + Math.random() * 0.24);
                    targetPitch = (Math.random() - 0.5) * 0.36;
                    targetRoll = -targetYaw * (0.12 + Math.random() * 0.12);
                    targetDx = targetYaw * 32.0;
                    targetDy = targetPitch * 20.0;
                    nextGazeTime = now + 2000 + Math.random() * 2200;
                }
            }

            const lerp = 0.055;
            currentYaw += (targetYaw - currentYaw) * lerp;
            currentPitch += (targetPitch - currentPitch) * lerp;
            currentRoll += (targetRoll - currentRoll) * lerp;
            currentDx += (targetDx - currentDx) * lerp;
            currentDy += (targetDy - currentDy) * lerp;

            const breathe = Math.sin(t3d * 1.5);
            const yBreathe = breathe * 3.5;
            const scale = 0.80 + 0.010 * breathe;

            // Draw Dense 3D Particles at 60 FPS
            if (headPoints !== null && headColors !== null) {
                const cosY = Math.cos(currentYaw), sinY = Math.sin(currentYaw);
                const cosX = Math.cos(currentPitch), sinX = Math.sin(currentPitch);
                const cosZ = Math.cos(currentRoll), sinZ = Math.sin(currentRoll);
                const fov = 350.0, dist = 280.0;
                const liveCx = cx + currentDx;
                const liveCy = cy + currentDy + yBreathe;

                const mouthOpen = isSpeaking ? (Math.sin(t3d * 16) * 0.5 + 0.5) * 7.0 : 0.0;
                const totalPts = headColors.length;

                for (let i = 0; i < totalPts; i++) {
                    let ox = headPoints[i * 3] * scale;
                    let oy = headPoints[i * 3 + 1] * scale;
                    let oz = headPoints[i * 3 + 2] * scale;

                    if (isSpeaking && oy > 20 && oy < 60 && oz > 0) {
                        const tj = (oy - 20) / 40.0;
                        oy += mouthOpen * Math.sin(tj * Math.PI);
                    }

                    // Yaw
                    const x1 = ox * cosY + oz * sinY;
                    const z1 = -ox * sinY + oz * cosY;
                    // Pitch
                    const y2 = oy * cosX - z1 * sinX;
                    const z2 = oy * sinX + z1 * cosX;
                    // Roll
                    const x3 = x1 * cosZ - y2 * sinZ;
                    const y3 = x1 * sinZ + y2 * cosZ;

                    const factor = fov / (z2 + dist);
                    const px = Math.round(liveCx + x3 * factor);
                    const py = Math.round(liveCy + y3 * factor);

                    if (px < 0 || px >= canvas.width || py < 0 || py >= canvas.height) continue;

                    const col = headColors[i];
                    const a = col[3] / 255.0;
                    ctx.fillStyle = "rgba(" + col[0] + "," + col[1] + "," + col[2] + "," + a.toFixed(2) + ")";
                    ctx.fillRect(px, py, 1.4, 1.4);
                }
            }
        }

        requestAnimationFrame(renderVisualizer);
    }
    requestAnimationFrame(renderVisualizer);

    function setAgentState(state) {
        currentAgentState = state.toUpperCase();
        const map = {
            "IDLE": "NEURAL CORE ONLINE // STANDBY",
            "LISTENING": "MIC ACTIVE // LISTENING...",
            "THINKING": "NEURAL INFERENCE // EXECUTING TOOLS...",
            "SPEAKING": "SYNTHESIZING SPEECH // TRANSMITTING...",
            "DICTATING": "VOICE DICTATION // SPEAK NOW (EN/ROMAN URDU)..."
        };
        if (visualizerStatus) { visualizerStatus.textContent = map[currentAgentState] || ("STATE: " + currentAgentState); }
    }

    // Fullscreen Toggle
    function toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch(() => {});
        } else {
            if (document.exitFullscreen) document.exitFullscreen();
        }
    }

    // Append Terminal Log
    function addTerminalLog(sender, text, tag) {
        const time = new Date().toLocaleTimeString();
        const entry = document.createElement('div');
        entry.className = "log-entry";
        entry.innerHTML = `<span class="log-time">[${time}]</span> <span class="log-${tag}">[${sender}]:</span> ${text}`;
        terminalFeed.appendChild(entry);
        terminalFeed.scrollTop = terminalFeed.scrollHeight;
    }

    function clearTerminal() {
        terminalFeed.innerHTML = "";
    }

    // Chat History Cards
    function addChatCard(prompt) {
        const id = chatCardsData.length;
        const time = new Date().toLocaleTimeString();
        const cardObj = { id, time, prompt, response: "Processing...", status: "In Progress" };
        chatCardsData.push(cardObj);

        const card = document.createElement('div');
        card.className = "chat-card";
        card.id = `chat-card-${id}`;
        card.onclick = () => inspectChat(id);
        card.innerHTML = `
            <div class="chat-card-top">
                <span>[${time}]</span>
                <span class="chat-card-pill" id="card-pill-${id}">⚡ Running</span>
            </div>
            <div class="chat-card-prompt">${prompt}</div>
        `;
        chatCardsList.prepend(card);
        document.getElementById('chat-count').textContent = chatCardsData.length + " items";
        return id;
    }

    function updateChatCard(id, response) {
        if (chatCardsData[id]) {
            chatCardsData[id].response = response;
            chatCardsData[id].status = "Completed";
            const pill = document.getElementById(`card-pill-${id}`);
            if (pill) {
                pill.textContent = "✓ Done";
                pill.className = "chat-card-pill done";
            }
            inspectChat(id);
        }
    }

    function inspectChat(id) {
        if (chatCardsData[id]) {
            const item = chatCardsData[id];
            inspectorContent.innerHTML = `
                <div style="font-size: 11px; color: var(--cyan-glow); font-family: 'JetBrains Mono', monospace; margin-bottom: 6px;">[CARD #${id+1} // ${item.time}]</div>
                <div style="color: #94a3b8; font-size: 11.5px; margin-bottom: 4px;"><strong>PROMPT:</strong></div>
                <div style="color: #fff; margin-bottom: 10px; font-weight: 600;">${item.prompt}</div>
                <div style="color: #94a3b8; font-size: 11.5px; margin-bottom: 4px;"><strong>ZEN REPLY:</strong></div>
                <div style="color: #34d399;">${item.response}</div>
            `;
        }
    }

    // Audio Playback
    function unlockIOSAudio() {
        if (ttsAudio) {
            ttsAudio.play().then(() => ttsAudio.pause()).catch(() => {});
        }
    }
    document.addEventListener('touchstart', unlockIOSAudio, { passive: true });
    document.addEventListener('click', unlockIOSAudio, { passive: true });

    function playTTSAudio(base64Audio) {
        if (!base64Audio) return;
        lastAudioBase64 = base64Audio;
        try {
            const binaryString = atob(base64Audio);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) bytes[i] = binaryString.charCodeAt(i);
            if (lastAudioBlobUrl) URL.revokeObjectURL(lastAudioBlobUrl);
            const blob = new Blob([bytes], { type: 'audio/mpeg' });
            lastAudioBlobUrl = URL.createObjectURL(blob);
            ttsAudio.pause();
            ttsAudio.src = lastAudioBlobUrl;
            setAgentState("SPEAKING");
            ttsAudio.play().then(() => {
                audioIndicator.textContent = "🔊 Playing Audio...";
                ttsAudio.onended = () => {
                    audioIndicator.textContent = "🔊 Speaker Active";
                    setAgentState("IDLE");
                };
            }).catch(() => {
                setAgentState("IDLE");
            });
        } catch (e) {
            console.error("Audio playback error:", e);
        }
    }

    function replayLastAudio() {
        if (lastAudioBase64) playTTSAudio(lastAudioBase64);
    }

    // Live Voice Dictation in Input Bar
    async function toggleTextDictation() {
        unlockIOSAudio();
        if (!isDictating) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                dictationChunks = [];
                dictationRecorder = new MediaRecorder(stream);
                dictationRecorder.ondataavailable = (e) => {
                    if (e.data.size > 0) dictationChunks.push(e.data);
                };
                dictationRecorder.onstop = async () => {
                    const audioBlob = new Blob(dictationChunks, { type: 'audio/wav' });
                    dictateLabel.textContent = "Transcribing...";
                    setAgentState("THINKING");
                    const formData = new FormData();
                    formData.append("audio", audioBlob, "dictation.wav");
                    try {
                        const res = await fetch("/api/dictate_stt", { method: "POST", body: formData });
                        const data = await res.json();
                        if (data.status === "success" && data.text) {
                            const curr = cmdInput.value.trim();
                            cmdInput.value = curr ? `${curr} ${data.text}` : data.text;
                            addTerminalLog("Dictation", `Recognized: "${data.text}"`, "tool");
                        }
                    } catch (err) {
                        console.error("Dictation error:", err);
                    }
                    dictateLabel.textContent = "Mic";
                    dictateBtn.classList.remove('active');
                    isDictating = false;
                    setAgentState("IDLE");
                    stream.getTracks().forEach(t => t.stop());
                };

                dictationRecorder.start();
                isDictating = true;
                dictateBtn.classList.add('active');
                dictateLabel.textContent = "Stop";
                setAgentState("DICTATING");
                addTerminalLog("Dictation", "Listening... Speak in English or Urdu", "sys");
            } catch (err) {
                alert("Microphone permission required: " + err);
            }
        } else {
            if (dictationRecorder && isDictating) {
                dictationRecorder.stop();
            }
        }
    }

    // Send Text Message
    async function sendTextMessage(e) {
        e.preventDefault();
        unlockIOSAudio();
        const text = cmdInput.value.trim();
        if (!text) return;
        cmdInput.value = "";

        const cardId = addChatCard(text);
        addTerminalLog("You", text, "user");
        userTranscript.textContent = "⌨️ " + text;
        zenReplyText.textContent = "ZEN executing...";
        setAgentState("THINKING");

        try {
            const res = await fetch("/api/text_command", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: text })
            });
            const data = await res.json();
            if (data.status === "success") {
                zenReplyText.textContent = "⚡ " + data.reply_text;
                addTerminalLog("ZEN", data.reply_text, "zen");
                updateChatCard(cardId, data.reply_text);
                if (data.audio_base64) {
                    playTTSAudio(data.audio_base64);
                } else {
                    setAgentState("IDLE");
                }
            } else {
                zenReplyText.textContent = "❌ " + data.reply_text;
                addTerminalLog("Error", data.reply_text, "err");
                updateChatCard(cardId, data.reply_text);
                setAgentState("IDLE");
            }
        } catch (err) {
            zenReplyText.textContent = "Error: " + err;
            addTerminalLog("Error", String(err), "err");
            updateChatCard(cardId, String(err));
            setAgentState("IDLE");
        }
    }

    // Quick Actions
    async function triggerAction(actionName) {
        unlockIOSAudio();
        const cardId = addChatCard(`Action: ${actionName}`);
        addTerminalLog("Action", `Triggering ${actionName}`, "tool");
        zenReplyText.textContent = "Executing " + actionName + "...";
        setAgentState("THINKING");
        try {
            const res = await fetch("/api/quick_action", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: actionName })
            });
            const data = await res.json();
            zenReplyText.textContent = "⚡ " + data.message;
            addTerminalLog("ZEN", data.message, "zen");
            updateChatCard(cardId, data.message);
            if (data.audio_base64) {
                playTTSAudio(data.audio_base64);
            } else {
                setAgentState("IDLE");
            }
        } catch (err) {
            zenReplyText.textContent = "Error: " + err;
            setAgentState("IDLE");
        }
    }

    let isDisplayOn = true;
    async function toggleDisplayPower() {
        unlockIOSAudio();
        const btn = document.getElementById('display-toggle-btn');
        isDisplayOn = !isDisplayOn;
        if (!isDisplayOn) {
            btn.innerHTML = '🌑 Display: BLACK (Tap to Wake)';
            triggerAction('screen_off');
        } else {
            btn.innerHTML = '🖥️ Display: ON (Tap to Black)';
            triggerAction('wake_screen');
        }
    }

    function toggleScreen() {
        const sc = document.getElementById('screen-container');
        if (sc.style.display === 'none' || !sc.style.display) {
            sc.style.display = 'flex';
            refreshScreen();
        } else {
            sc.style.display = 'none';
        }
    }

    function refreshScreen() {
        const img = document.getElementById('desktop-screen-img');
        img.src = '/api/screen_preview?' + new Date().getTime();
    }

    function confirmShutdown() {
        document.getElementById('shutdown-modal').style.display = 'flex';
    }
    function closeShutdownModal() {
        document.getElementById('shutdown-modal').style.display = 'none';
    }
    async function executeShutdown() {
        closeShutdownModal();
        triggerAction('shutdown');
    }

    // Telemetry Poller
    async function pollVitals() {
        try {
            const res = await fetch('/api/system_vitals');
            const data = await res.json();
            if (data.status === 'success') {
                document.getElementById('cpu-val').textContent = Math.round(data.cpu) + '%';
                document.getElementById('cpu-fill').style.width = Math.min(100, data.cpu) + '%';
                document.getElementById('ram-val').textContent = Math.round(data.ram) + '%';
                document.getElementById('ram-fill').style.width = Math.min(100, data.ram) + '%';
                const plugIcon = data.plugged ? '⚡' : '🔋';
                document.getElementById('batt-val').textContent = data.battery + '% ' + plugIcon;
            }
        } catch (e) {}
        setTimeout(pollVitals, 3000);
    }
    pollVitals();
</script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)

def start_cloudflare_tunnel(port: int = 5050, is_https: bool = False):
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
    
    if is_https:
        tunnel_cmd = [cloudflared_path, "tunnel", "--url", f"https://127.0.0.1:{port}", "--no-tls-verify"]
    else:
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

    start_cloudflare_tunnel(port, is_https=(scheme == "https"))

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
