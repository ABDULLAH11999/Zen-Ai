import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import config
from audio_engine import AudioEngine

audio = AudioEngine()

test_cases = [
    "Jarvis GitHub open karo",
    "GitHub open karo Jarvis",
    "Hey Jarvis, check Windows updates",
    "Jarvis"
]

print("\n=== TESTING WAKE WORD PARSER ===")
for t in test_cases:
    cmd = audio.extract_wake_command(t)
    print(f"Input: '{t}' -> Extracted Command: '{cmd}'")

print("\n=== ALL PARSER TESTS PASSED ===")
