# ⚡ J.A.R.V.I.S. - Autonomous Desktop Voice Agent

A production-ready, multimodal desktop voice assistant powered by **Google Gemini 2.0 Flash (`google-genai`)**, offline **Faster-Whisper** speech recognition, natural **Microsoft Edge TTS**, high-speed screen vision, and complete operating system / terminal tool execution.

---

## 🌟 Core Architecture & Capabilities

1. **Multimodal Vision & Brain**:
   - Google Gemini 2.0 Flash (`google-genai` SDK).
   - Real-time primary monitor capture via `mss`/`Pillow` for reading IDEs, terminal errors, download bars, browser windows, and visual state.
2. **Low-Latency Voice Pipeline**:
   - **Ears (STT)**: Offline `faster-whisper` (`base.en` / `small.en` on CPU/INT8) with real-time Voice Activity Detection (VAD) and customizable wake-words (`"Hey Jarvis"` / `"Jarvis"`).
   - **Mouth (TTS)**: Microsoft `edge-tts` (`en-US-GuyNeural`) streamed in-memory to prevent file-locking bugs.
3. **OS & Terminal Control (Hands)**:
   - Automated Function Calling for Gemini 2.0:
     - Execute terminal commands (`npm run dev`, `python`, `git`, build scripts).
     - Read, write, and list project files within safe workspace boundaries.
     - Live system telemetry (CPU, RAM, Disk, Active Focused Window).
     - Open URLs and launch desktop applications.
4. **Futuristic HUD Desktop Interface**:
   - Built with `CustomTkinter` in sleek sci-fi dark mode.
   - Master Voice & Monitoring ON/OFF toggle switch.
   - Real-time status badge (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `MUTED`).
   - Color-coded telemetry feed and text prompt bar for dual voice/keyboard control.

---

## 📁 Project Structure

```
f:\Agent\
├── .env.example              # Sample environment configuration
├── requirements.txt          # Python dependencies
├── config.py                 # Configuration settings and env loading
├── screen_vision.py          # Fast primary monitor screenshot capture & optimization
├── system_tools.py           # OS terminal execution, file system tools, and sandboxing
├── audio_engine.py           # Faster-Whisper STT, VAD, and Edge-TTS audio playback
├── agent_core.py             # Gemini 2.0 Flash multimodal engine with tool calling
├── gui.py                    # CustomTkinter Desktop HUD interface
├── main.py                   # Main orchestration entrypoint & worker threads
└── README.md                 # Documentation
```

---

## 🚀 Quick Setup Guide

### 1. Prerequisites
- Python 3.10+
- A Google Gemini API Key (from [Google AI Studio](https://aistudio.google.com/))
- Microphone and speakers

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure `.env`
Copy `.env.example` to `.env` and fill in your Gemini API key:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
WHISPER_MODEL_SIZE=base.en
WAKE_WORDS=jarvis,hey jarvis
TTS_VOICE=en-US-GuyNeural
```

### 4. Run JARVIS
```bash
python main.py
```

---

## 🎙️ How to Interact

1. **Voice Mode**:
   - Simply say: **"Hey Jarvis, what's on my screen right now?"** or **"Jarvis, run npm test in this project."**
   - The status will switch to `LISTENING` -> `THINKING` -> `SPEAKING`.
2. **Keyboard Mode**:
   - Type your instruction into the input bar at the bottom of the JARVIS window and press Enter.
3. **Mute / Sleep**:
   - Toggle the **Voice & Screen Monitoring** switch off anytime to pause background listening.
