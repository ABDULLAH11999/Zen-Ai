import asyncio
import io
import logging
import os
import queue
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, Optional, List

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
import edge_tts
import pygame

from config import config

logger = logging.getLogger(__name__)

class SpeakerVerifier:
    """Acoustic Voice Biometrics for Speaker Verification."""
    
    def __init__(self, profile_dir: Path = config.VOICE_PROFILE_DIR, threshold: float = config.SPEAKER_SIMILARITY_THRESHOLD):
        self.profile_dir = profile_dir
        self.threshold = threshold
        self.master_embedding: Optional[np.ndarray] = None
        self.load_profiles()
        
    def _extract_features(self, audio: np.ndarray, sr: int = 16000) -> Optional[np.ndarray]:
        """Extracts normalized MFCC/Spectral acoustic fingerprint from audio."""
        if len(audio) < sr * 0.4:  # At least 400ms needed
            return None
        try:
            # Normalize
            audio = audio / (np.max(np.abs(audio)) + 1e-8)
            # Frame the signal
            frame_len = int(0.025 * sr)  # 25ms
            frame_step = int(0.010 * sr) # 10ms
            num_frames = max(1, int(np.ceil(float(np.abs(len(audio) - frame_len)) / frame_step)))
            pad_len = num_frames * frame_step + frame_len
            padded = np.pad(audio, (0, max(0, pad_len - len(audio))), 'constant')
            
            # Simple FFT Filterbank representation
            frames = np.lib.stride_tricks.sliding_window_view(padded[:pad_len], frame_len)[::frame_step]
            windowed = frames * np.hamming(frame_len)
            spectrogram = np.abs(np.fft.rfft(windowed, n=512))
            
            # Mel-scale filter approximation (energy bins)
            mel_energies = np.log(spectrogram + 1e-6)
            # Compute mean and standard deviation vector across time
            mean_vec = np.mean(mel_energies, axis=0)
            std_vec = np.std(mel_energies, axis=0)
            feature = np.concatenate([mean_vec, std_vec])
            # Unit normalize
            norm = np.linalg.norm(feature)
            return feature / (norm + 1e-8)
        except Exception as e:
            logger.debug(f"Feature extraction error: {e}")
            return None

    def load_profiles(self):
        """Loads all master voice sample audio files from voice_profile directory."""
        if not self.profile_dir.exists():
            self.profile_dir.mkdir(parents=True, exist_ok=True)
            
        audio_files = list(self.profile_dir.glob("*.wav")) + list(self.profile_dir.glob("*.mp3")) + list(self.profile_dir.glob("*.m4a"))
        if not audio_files:
            logger.info("Voice Profile Mode: OPEN TO EVERYONE (No voice profile required, accepting all voices).")
            self.master_embedding = None
            return
            
        embeddings = []
        for file in audio_files:
            try:
                import scipy.io.wavfile as wavfile
                sr, data = wavfile.read(str(file))
                if len(data.shape) > 1:
                    data = data.mean(axis=1) # Mono
                if data.dtype == np.int16:
                    data = data.astype(np.float32) / 32768.0
                feat = self._extract_features(data, sr=sr)
                if feat is not None:
                    embeddings.append(feat)
                    logger.info(f"Loaded voice profile from: {file.name}")
            except Exception as e:
                logger.warning(f"Could not load voice profile '{file.name}': {e}")
                
        if embeddings:
            self.master_embedding = np.mean(embeddings, axis=0)
            self.master_embedding /= np.linalg.norm(self.master_embedding) + 1e-8
            logger.info("Master Speaker Profile activated. JARVIS is locked to Sir's voice.")

    def verify(self, audio: np.ndarray, sr: int = 16000) -> bool:
        """Verifies if incoming audio matches Sir's master voice profile."""
        if not config.ENABLE_SPEAKER_VERIFICATION or self.master_embedding is None:
            # If verification is disabled or no profile exists, accept
            return True
            
        incoming_feat = self._extract_features(audio, sr=sr)
        if incoming_feat is None:
            return True # Inconclusive short chunk, allow pass
            
        similarity = np.dot(self.master_embedding, incoming_feat)
        logger.info(f"Speaker Verification Similarity: {similarity:.3f} (Threshold: {self.threshold:.3f})")
        return bool(similarity >= self.threshold)

class AudioEngine:
    """Complete Audio Engine handling offline Faster-Whisper STT, VAD, Speaker Verification, and Edge-TTS."""
    
    def __init__(self):
        self.sample_rate = config.AUDIO_SAMPLE_RATE
        self.energy_threshold = config.VAD_ENERGY_THRESHOLD
        self.silence_threshold = config.SILENCE_DURATION_THRESHOLD
        self.max_duration = config.MAX_RECORDING_DURATION
        
        # Speaker Verifier
        self.speaker_verifier = SpeakerVerifier()
        
        # STT Model (Faster-Whisper)
        logger.info(f"Loading Faster-Whisper model ({config.WHISPER_MODEL_SIZE}) on {config.WHISPER_DEVICE} ({config.WHISPER_COMPUTE_TYPE})...")
        self.whisper_model = WhisperModel(
            config.WHISPER_MODEL_SIZE,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE,
            download_root=str(config.BASE_DIR / "models")
        )
        logger.info("Faster-Whisper model initialized.")
        
        # Audio playback init (Pygame mixer)
        try:
            pygame.mixer.init(frequency=24000, size=-16, channels=2, buffer=2048)
        except Exception as e:
            logger.warning(f"Pygame mixer init fallback: {e}")
            pygame.mixer.init()
            
        self.is_listening = False
        self.is_speaking = False
        self.is_muted = False
        self._stop_listener_event = threading.Event()
        
    # ==========================================
    # Speech-to-Text (STT) & VAD Listening
    # ==========================================
    
    def transcribe_audio_array(self, audio_data: np.ndarray) -> str:
        """
        Transcribes audio using Groq Whisper-Large-v3-Turbo -> Google Speech API -> Faster-Whisper.
        Fast, accurate for Urdu, Hindi, Roman Urdu, and English even with whispers.
        """
        if len(audio_data) == 0:
            return ""
        
        # Normalize and convert to 16-bit PCM
        audio_norm = audio_data.astype(np.float32)
        max_val = np.max(np.abs(audio_norm))
        if max_val > 0:
            audio_norm = audio_norm / max_val
        int16_data = (audio_norm * 32767).astype(np.int16)
        
        # 1. Primary Engine: Groq Cloud Whisper-Large-v3-Turbo (Sub-second, High Accuracy)
        if config.GROQ_API_KEY:
            try:
                from groq import Groq
                import scipy.io.wavfile as wavfile
                client = Groq(api_key=config.GROQ_API_KEY, timeout=5.0)
                
                buf = io.BytesIO()
                wavfile.write(buf, self.sample_rate, int16_data)
                wav_bytes = buf.getvalue()
                
                # Explicit language anchor prevents Whisper from misinterpreting Urdu/Hindi words into English
                groq_lang = "hi" if config.JARVIS_LANGUAGE in ["hindi", "bilingual"] else ("ur" if config.JARVIS_LANGUAGE == "urdu" else None)
                prompt_text = "ज़ेन (ZEN) वॉयस असिस्टेंट। Urdu, Hindi, Roman Urdu, Chrome, YouTube, Binance, AntiGravity, Desktop, GitHub, VS Code, open karo, close karo, band karo."
                
                transcription = client.audio.transcriptions.create(
                    file=("speech.wav", wav_bytes, "audio/wav"),
                    model="whisper-large-v3-turbo",
                    language=groq_lang,
                    prompt=prompt_text,
                    temperature=0.0
                )
                if transcription and transcription.text:
                    raw_text = transcription.text.strip()
                    # Filter out common Whisper silence hallucination artifacts
                    hallucinations = [
                        "thank you.", "thank you", "gracias.", "gracias", "bye, jujo.", "bye.", 
                        "subscribe", "thanks for watching.", "aap kaise hain sir.", "aap kaise hain sir",
                        "zen, xzen, zzen, enn.", "zen, xzen, zzen, enn", "urdu, hindi, english."
                    ]
                    if raw_text.lower() in hallucinations:
                        logger.debug(f"Filtered silence artifact: '{raw_text}'")
                        return ""
                    if len(raw_text) > 0:
                        logger.info(f"Groq Whisper recognized: '{raw_text}'")
                        return raw_text
            except Exception as groq_err:
                logger.debug(f"Groq STT fallback to Google/Whisper ({groq_err})")
        
        # 2. Secondary Engine: Google Multilingual Speech Recognition
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            audio_obj = sr.AudioData(int16_data.tobytes(), self.sample_rate, 2)
            
            lang = "hi-IN" if config.JARVIS_LANGUAGE in ["hindi", "bilingual"] else ("ur-PK" if config.JARVIS_LANGUAGE == "urdu" else "en-US")
            text = r.recognize_google(audio_obj, language=lang)
            if text and len(text.strip()) > 0:
                logger.info(f"Google STT ({lang}) recognized: '{text}'")
                return text.strip()
        except Exception as google_err:
            logger.debug(f"Google STT fallback to local Whisper ({google_err})")
            
        # 3. Offline Backup Engine: Faster-Whisper
        try:
            initial_prompt = "ज़ेन (ZEN) वॉयस असिस्टेंट। Urdu, Hindi, Roman Urdu, Chrome, YouTube, Binance, AntiGravity, Desktop, GitHub, VS Code, open karo, close karo, band karo."
            lang_param = "en" if config.JARVIS_LANGUAGE == "english" else ("hi" if config.JARVIS_LANGUAGE in ["hindi", "bilingual"] else "ur")
            
            segments, info = self.whisper_model.transcribe(
                int16_data.astype(np.float32) / 32768.0,
                beam_size=3,
                language=lang_param,
                initial_prompt=initial_prompt,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=400)
            )
            text_segments = [seg.text.strip() for seg in segments]
            result = " ".join(text_segments).strip()
            if result.lower() in ["thank you.", "thank you", "gracias.", "aap kaise hain sir."]:
                return ""
            return result
        except Exception as whisper_err:
            logger.error(f"Whisper transcription error: {whisper_err}")
            return ""

    def extract_wake_command(self, transcription: str, is_active_session: bool = False) -> Optional[str]:
        """
        Detects wake words or active follow-up action intent.
        Returns the clean executable command.
        """
        cleaned = transcription.strip()
        lower = cleaned.lower()
        if not lower or len(cleaned) < 2:
            return None
            
        # 1. Match explicit wake words (e.g. 'zen', 'hey zen', 'xzen', 'enn')
        sorted_wake_words = sorted(config.WAKE_WORDS, key=len, reverse=True)
        for wake_word in sorted_wake_words:
            if wake_word in lower:
                import re
                cmd = re.sub(re.escape(wake_word), "", cleaned, flags=re.IGNORECASE).strip(" ,:.-?!")
                return cmd if cmd else cleaned
                
        # 2. If in active conversation session (within 45s of last interaction), accept directly
        if is_active_session:
            return cleaned
            
        # 3. Direct Action Intent Check (Even if wake word was omitted by user)
        action_indicators = [
            "open", "kholo", "close", "band", "kar do", "kardo", "type", "search",
            "batao", "btao", "fetch", "status", "lock", "unlock", "volume", "play",
            "check", "chalao", "likho", "send", "bhejo", "screen", "chrome"
        ]
        if any(act in lower for act in action_indicators):
            logger.info(f"Direct action intent detected without wake word: '{cleaned}'")
            return cleaned
            
        return None

    def record_until_silence(self, on_speech_start: Optional[Callable] = None) -> np.ndarray:
        """
        Listens to microphone stream, triggers on voice energy, records until silence persists.
        Ensures a minimum speech buffer is recorded so words are never chopped in half.
        """
        block_duration = 0.05  # 50ms per chunk
        block_size = int(self.sample_rate * block_duration)
        min_speech_duration = 0.9  # Must record at least 0.9s before checking silence cutoff
        
        audio_chunks = []
        is_speech_active = False
        silence_start_time = None
        record_start_time = None
        
        with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype='float32', blocksize=block_size) as stream:
            while not self._stop_listener_event.is_set():
                if self.is_muted or self.is_speaking:
                    time.sleep(0.05)
                    continue
                
                data, overflowed = stream.read(block_size)
                chunk = data.flatten()
                
                # Compute RMS Energy (scaled to 0-32767 equivalent)
                rms = np.sqrt(np.mean(chunk**2)) * 32768
                
                if not is_speech_active:
                    if rms > self.energy_threshold:
                        is_speech_active = True
                        record_start_time = time.time()
                        silence_start_time = None
                        audio_chunks = [chunk]
                        if on_speech_start:
                            on_speech_start()
                else:
                    audio_chunks.append(chunk)
                    elapsed = time.time() - record_start_time
                    
                    if rms < self.energy_threshold:
                        if silence_start_time is None:
                            silence_start_time = time.time()
                        elif (time.time() - silence_start_time > self.silence_threshold) and (elapsed >= min_speech_duration):
                            # User comfortably finished speaking
                            break
                    else:
                        silence_start_time = None
                        
                    # Max safety cutoff
                    if elapsed > self.max_duration:
                        break
                        
        if audio_chunks:
            return np.concatenate(audio_chunks, axis=0)
        return np.array([], dtype=np.float32)

    # ==========================================
    # Text-to-Speech (TTS) & Playback
    # ==========================================
    
    async def _generate_speech_bytes(self, text: str) -> bytes:
        """Asynchronously streams speech audio from edge-tts into memory bytes."""
        # Auto-detect if text has Hindi / Devanagari characters or use configured voice
        voice = config.TTS_VOICE
        has_devanagari = any('\u0900' <= char <= '\u097F' for char in text)
        if has_devanagari or config.JARVIS_LANGUAGE in ["hindi", "urdu", "bilingual"]:
            voice = config.TTS_VOICE_HINDI
        elif config.JARVIS_LANGUAGE == "english":
            voice = config.TTS_VOICE_ENGLISH
            
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
        return audio_stream.getvalue()

    def speak(self, text: str, on_start: Optional[Callable] = None, on_finish: Optional[Callable] = None) -> None:
        """
        Generates and plays speech audio cleanly without file locking issues.
        Runs synchronously on the calling thread or worker thread.
        """
        clean_text = text.strip()
        if not clean_text:
            return
            
        self.is_speaking = True
        if on_start:
            on_start()
            
        try:
            # Generate MP3 stream asynchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            audio_bytes = loop.run_until_complete(self._generate_speech_bytes(clean_text))
            loop.close()
            
            if not audio_bytes:
                logger.warning("Empty audio stream generated by edge-tts.")
                return
                
            # Play in-memory via Pygame Sound / BytesIO
            audio_buffer = io.BytesIO(audio_bytes)
            audio_buffer.seek(0)
            pygame.mixer.music.load(audio_buffer)
            pygame.mixer.music.play()
            
            start_play = time.time()
            max_play_time = max(5.0, len(clean_text) * 0.3)
            
            while pygame.mixer.music.get_busy():
                if self._stop_listener_event.is_set() or (time.time() - start_play > max_play_time):
                    pygame.mixer.music.stop()
                    break
                time.sleep(0.05)
                
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"Error during TTS playback: {e}")
        finally:
            self.is_speaking = False
            if on_finish:
                on_finish()

    def stop_speaking(self):
        """Immediately interrupts and stops any ongoing speech playback."""
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
        self.is_speaking = False

    def shutdown(self):
        """Cleanly releases audio resources."""
        self._stop_listener_event.set()
        self.stop_speaking()
        pygame.mixer.quit()
