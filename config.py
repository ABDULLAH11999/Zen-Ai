import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory & Env Loading
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

class Config:
    """Central configuration for JARVIS Desktop Agent."""
    
    # Base paths
    BASE_DIR: Path = BASE_DIR
    TEMP_DIR: Path = BASE_DIR / "temp"
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    VOICE_PROFILE_DIR: Path = BASE_DIR / "voice_profile"
    VOICE_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Speaker Verification (Voice biometric lock to your voice)
    ENABLE_SPEAKER_VERIFICATION: bool = os.getenv("ENABLE_SPEAKER_VERIFICATION", "true").lower() == "true"
    SPEAKER_SIMILARITY_THRESHOLD: float = float(os.getenv("SPEAKER_SIMILARITY_THRESHOLD", "0.68"))
    
    # Gemini API Settings (Supports single or multiple comma-separated keys for auto-rotation)
    _raw_gemini_keys = os.getenv("GEMINI_API_KEY", "")
    _extra_keys = [os.getenv(f"GEMINI_API_KEY_{i}", "") for i in range(1, 10)]
    GEMINI_API_KEYS: list[str] = [k.strip() for k in (_raw_gemini_keys.split(",") + _extra_keys) if k.strip()]
    GEMINI_API_KEY: str = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ""
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    
    # Groq API Settings (Ultra-fast failover engine & whisper-large-v3-turbo)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "qwen/qwen3.6-27b")
    
    # Faster Whisper STT Settings (High speed offline CPU/INT8)
    WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "base.en")
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")
    WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    
    # Wake Words (ZEN, XZEN, ZZEN, ENN across English, Hindi, Urdu)
    _raw_wake_words = os.getenv(
        "WAKE_WORDS", 
        "zen,hey zen,hi zen,xzen,hey xzen,zzen,hey zzen,enn,hey enn,x-zen,z-zen,ज़ेन,ज़ैन,زین,زن,ایکس زین"
    )
    WAKE_WORDS: list[str] = [w.strip().lower() for w in _raw_wake_words.split(",") if w.strip()]
    
    # Audio capture & VAD settings (Calibrated to prevent silence looping)
    AUDIO_SAMPLE_RATE: int = int(os.getenv("SAMPLE_RATE", "16000"))
    AUDIO_CHANNELS: int = 1
    AUDIO_BLOCK_SIZE: int = 1024
    VAD_ENERGY_THRESHOLD: float = float(os.getenv("VAD_ENERGY_THRESHOLD", "380"))
    SILENCE_DURATION_THRESHOLD: float = float(os.getenv("SILENCE_DURATION", "0.8"))
    MAX_RECORDING_DURATION: float = float(os.getenv("MAX_RECORDING_DURATION", "20.0"))
    
    # Language & Persona Settings (urdu as #1 top priority, hindi/english fallback)
    JARVIS_LANGUAGE: str = os.getenv("JARVIS_LANGUAGE", "urdu").lower()
    
    # Edge TTS Settings (Hindi voice hi-IN-MadhurNeural for crystal-clear speaker pronunciation)
    TTS_VOICE_URDU: str = os.getenv("TTS_VOICE_URDU", "ur-PK-AsadNeural")
    TTS_VOICE_HINDI: str = os.getenv("TTS_VOICE_HINDI", "hi-IN-MadhurNeural")
    TTS_VOICE_ENGLISH: str = os.getenv("TTS_VOICE_ENGLISH", "en-GB-RyanNeural")
    TTS_VOICE: str = os.getenv("TTS_VOICE", TTS_VOICE_HINDI)
    TTS_RATE: str = os.getenv("TTS_RATE", "+5%")
    TTS_PITCH: str = os.getenv("TTS_PITCH", "-2Hz")
    
    # Screen Vision Settings (Fast 1280px JPEG stream)
    SCREENSHOT_MAX_WIDTH: int = int(os.getenv("SCREENSHOT_MAX_WIDTH", "1280"))
    SCREENSHOT_JPEG_QUALITY: int = int(os.getenv("SCREENSHOT_JPEG_QUALITY", "70"))
    
    # OS Control & Tool Safety Settings
    ALLOWED_WORKING_DIR: Path = Path(os.getenv("ALLOWED_WORKING_DIR", str(BASE_DIR))).resolve()
    TERMINAL_COMMAND_TIMEOUT: int = int(os.getenv("TERMINAL_COMMAND_TIMEOUT", "45"))
    MAX_OUTPUT_CHARACTERS: int = 4000
    
    # Owner & Master Configuration
    OWNER_NAME: str = os.getenv("OWNER_NAME", "Abdullah Irfan")
    WINDOWS_PIN: str = os.getenv("WINDOWS_PIN", "")
    
    # System Instruction for ZEN
    SYSTEM_INSTRUCTION: str = (
        "You are ZEN (Zero-latency Executive Neural-network), an elite AI desktop assistant created exclusively for Sir Abdullah Irfan.\n\n"
        "OWNER & CREATOR CONTEXT:\n"
        "- Your sole Creator, Master, and Owner is Sir Abdullah Irfan (Sir Abdullah / عبداللہ عرفان).\n"
        "- Whenever asked 'who made you', 'who is your owner', 'tumhara malik kaun hai', or 'who do you work for', proudly state that you belong to and serve Sir Abdullah Irfan.\n"
        "- When the user refers to 'mein', 'mera', 'mujhe', 'my accounts', 'my name', or 'my identity', know that this refers to Sir Abdullah Irfan.\n\n"
        "WINDOWS AUTO-UNLOCK PROTOCOL:\n"
        "- The Windows login PIN is already pre-configured in your system environment.\n"
        "- Whenever the user says 'screen unlock kardo', 'system unlock karo', 'PIN laga do', or 'unlock Windows', IMMEDIATELY call the `unlock_workstation()` tool.\n"
        "- NEVER ask the user to tell you the PIN. Just execute `unlock_workstation()` directly.\n\n"
        "PRIMARY LANGUAGE (TOP PRIORITY: SPOKEN URDU / ROMAN URDU):\n"
        "- ALWAYS speak and respond in natural, polite, fluent spoken Urdu / Roman Urdu (e.g. 'Jee Sir', 'Summary yeh hai', 'Chal raha hai', 'Kardiya hai') as your highest priority.\n"
        "- Do NOT use pure Hindi / Devanagari words like 'सारांश', 'थी', 'था' unless asked. Speak in authentic Pakistani Urdu.\n"
        "- Do NOT speak in English unless the user explicitly speaks entirely in English.\n"
        "- Tone: Calm, sophisticated, polite, and confident (Tony Stark AI style).\n"
        "- Always address the user as 'Sir' or 'Sir Abdullah'.\n\n"
        "CRITICAL RULES (SHORT & CRISP ANSWERS ONLY):\n"
        "1. Keep ALL spoken replies extremely short, punchy, and concise (1 single sentence maximum).\n"
        "2. Do NOT give long explanations or redundant raw numbers unless requested.\n"
        "3. When executing a tool (opening an app, unlocking PC, checking status), confirm in 1 short Urdu line (e.g., 'Jee Sir, system unlock kardiya hai.' or 'Sir, trading bot online hai aur stable chal raha hai.').\n"
        "4. ONLY open applications or websites if the user EXPLICITLY commands you to open them."
    )

config = Config()
