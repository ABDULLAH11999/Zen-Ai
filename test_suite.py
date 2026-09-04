import sys
import os
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

print("=" * 60)
print("⚡ J.A.R.V.I.S. AUTOMATED INTEGRATION & DIAGNOSTIC TEST SUITE")
print("=" * 60)

# 1. Test Config & API Key
print("\n[1/5] Testing Configuration & Environment Variables...")
from config import config
assert config.GEMINI_API_KEY, "ERROR: GEMINI_API_KEY is empty!"
print(f" -> GEMINI_API_KEY: {config.GEMINI_API_KEY[:8]}...{config.GEMINI_API_KEY[-4:]} (Configured)")
print(f" -> Model: {config.GEMINI_MODEL}")
print(f" -> TTS Voice: {config.TTS_VOICE}")
print(f" -> Wake Words: {config.WAKE_WORDS}")
print(" [PASS] Config test completed successfully.")

# 2. Test Screen Vision
print("\n[2/5] Testing Screen Vision Module (mss / Pillow)...")
from screen_vision import screen_vision
screen_bytes = screen_vision.capture_screen_bytes()
dims = screen_vision.get_screen_dimensions()
print(f" -> Primary Screen Dimensions: {dims[0]}x{dims[1]}")
print(f" -> Captured Screen JPEG Buffer Size: {len(screen_bytes)} bytes")
assert len(screen_bytes) > 1000, "Screen capture returned empty or corrupted buffer!"
print(" [PASS] Screen Vision test completed successfully.")

# 3. Test System Tools
print("\n[3/5] Testing System Tools (Terminal Dispatch & Hardware Telemetry)...")
from system_tools import execute_terminal_command, get_system_status
cmd_res = execute_terminal_command("echo JARVIS_TERMINAL_ONLINE")
assert cmd_res["status"] == "success", f"Command failed: {cmd_res}"
assert "JARVIS_TERMINAL_ONLINE" in cmd_res["stdout"], f"Output mismatch: {cmd_res}"
print(f" -> Terminal Subprocess Test: {cmd_res['stdout']}")

sys_res = get_system_status()
print(f" -> Hardware Telemetry: CPU: {sys_res['cpu_percent']}%, RAM: {sys_res['ram_used_percent']}%, Free Disk: {sys_res['disk_free_gb']} GB")
print(f" -> Active Window: '{sys_res['active_window']}'")
print(" [PASS] System Tools test completed successfully.")

# 4. Test Gemini 2.0 Flash Multimodal Vision & Reasoning
print("\n[4/5] Testing Gemini 2.0 Flash API Live Integration...")
from agent_core import JarvisAgent
agent = JarvisAgent()
test_prompt = "Provide a 1-sentence confirmation that you are online and can see my screen."
print(f" -> Sending live query to Gemini 2.0 Flash with screen capture: '{test_prompt}'")
response = agent.process_query(test_prompt, include_screen=True)
print(f"\n⚡ JARVIS Response: \"{response}\"\n")
assert len(response) > 5, "Empty response received from Gemini!"
print(" [PASS] Gemini 2.0 Flash Multimodal test completed successfully.")

# 5. Test Audio Engine & Speaker Verification
print("\n[5/5] Testing Audio Engine, Edge-TTS & Speaker Verification...")
import asyncio
from audio_engine import AudioEngine
audio = AudioEngine()
print(f" -> Speaker Verification Enabled: {config.ENABLE_SPEAKER_VERIFICATION}")
print(f" -> Voice Profile Dir: {config.VOICE_PROFILE_DIR}")
print(f" -> Loaded Voice Profiles: {'Active (Locked to Sir)' if audio.speaker_verifier.master_embedding is not None else 'Empty (Open to all voices or add master_voice.wav)'}")

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
tts_bytes = loop.run_until_complete(audio._generate_speech_bytes("सर, जार्विस आपकी सेवा में उपस्थित है।"))
loop.close()
print(f" -> Hindi Edge-TTS Generated Stream: {len(tts_bytes)} bytes")
assert len(tts_bytes) > 500, "TTS generation returned empty buffer!"
print(" [PASS] Audio Engine & Voice Biometrics test completed successfully.")

print("\n" + "=" * 60)
print("🎉 ALL 5/5 INTEGRATION TESTS PASSED WITH 100% SUCCESS!")
print("=" * 60)
