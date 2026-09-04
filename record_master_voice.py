import sys
import time
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wavfile
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import config

def record_sir_voice_sample(duration_seconds: int = 40):
    """
    Records master voice profile of Sir with varying tones (normal, loud, whisper)
    and saves to voice_profile/master_voice.wav.
    """
    print("=" * 60)
    print("🎙️ JARVIS MASTER VOICE ENROLLMENT (SIR'S VOICE BIOMETRICS)")
    print("=" * 60)
    print(f"\nWe will record for {duration_seconds} seconds.")
    print("Please speak a few sentences in your normal tone, some in a louder tone, and some in a quiet/whisper tone.")
    print("Example: 'Hey Jarvis, check my screen. Open GTA V and run my dev server.'")
    print("\nPress ENTER when you are ready to start recording...")
    input()
    
    sr = config.AUDIO_SAMPLE_RATE
    print(f"🔴 RECORDING STARTED ({duration_seconds}s)... Speak now!")
    
    recording = sd.rec(int(duration_seconds * sr), samplerate=sr, channels=1, dtype='float32')
    
    # Progress countdown
    for remaining in range(duration_seconds, 0, -1):
        print(f"⏳ Remaining: {remaining}s...", end="\r", flush=True)
        time.sleep(1)
        
    sd.wait()
    print("\n✅ Recording finished! Processing acoustic signature...")
    
    # Normalize and convert to 16-bit PCM WAV
    audio = recording.flatten()
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val
    audio_int16 = (audio * 32767).astype(np.int16)
    
    out_file = config.VOICE_PROFILE_DIR / "master_voice.wav"
    config.VOICE_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(out_file), sr, audio_int16)
    
    print(f"🎉 Master voice successfully saved to: {out_file}")
    print("JARVIS is now locked to your voice biometric signature.")
    print("=" * 60)

if __name__ == "__main__":
    record_sir_voice_sample(duration_seconds=35)
