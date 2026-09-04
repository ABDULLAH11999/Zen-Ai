import logging
import threading
import sys
import queue
import time
from typing import Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import config
from audio_engine import AudioEngine
from agent_core import JarvisAgent
from gui import JarvisGUI

# Setup root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("JarvisMain")

class JarvisOrchestrator:
    """Orchestrates audio, vision, agent reasoning, and GUI execution."""
    
    def __init__(self):
        self.audio_engine = AudioEngine()
        self.agent = JarvisAgent()
        self.task_queue: queue.Queue = queue.Queue()
        self.is_running = True
        
        # Initialize GUI
        self.gui = JarvisGUI(
            on_toggle_monitoring=self.on_toggle_monitoring,
            on_send_text=self.on_send_text,
            on_reset_context=self.on_reset_context
        )
        
        # Worker threads
        self.voice_thread: Optional[threading.Thread] = None
        self.agent_worker_thread: Optional[threading.Thread] = None
        self.last_interaction_time: float = 0.0

    def start(self):
        """Starts background threads and runs the GUI mainloop."""
        self.gui.append_log("System", f"ZEN Initialized. Model: {config.GEMINI_MODEL}", tag="system")
        self.gui.append_log("System", f"Dual Engine: Groq STT/LPU + Gemini Vision | TTS: {config.TTS_VOICE}", tag="system")
        
        if not config.GEMINI_API_KEY and not config.GROQ_API_KEY:
            self.gui.append_log("Error", "API keys not configured in .env! Please add your key.", tag="error")
        else:
            self.gui.append_log("System", "Ready and listening. Say 'Hey Zen' or type a command below.", tag="system")
            
        # Start background agent query worker
        self.agent_worker_thread = threading.Thread(target=self._agent_worker_loop, daemon=True)
        self.agent_worker_thread.start()
        
        # Start voice listener worker
        self.voice_thread = threading.Thread(target=self._voice_listener_loop, daemon=True)
        self.voice_thread.start()
        
        # Handle GUI close event
        self.gui.protocol("WM_DELETE_WINDOW", self.shutdown)
        
        # Run GUI loop
        self.gui.mainloop()

    def on_toggle_monitoring(self, is_active: bool):
        """Called when user switches monitoring switch."""
        self.audio_engine.is_muted = not is_active
        if not is_active:
            self.audio_engine.stop_speaking()

    def on_reset_context(self):
        """Called when reset context button is clicked."""
        self.agent.reset_history()

    def on_send_text(self, text: str):
        """Dispatches typed query to agent processing queue."""
        self.last_interaction_time = time.time()
        self.task_queue.put(text)

    def _voice_listener_loop(self):
        """Continuous background microphone listener loop with Voiceprint Verification & Wake-word handling."""
        logger.info("Voice listener thread started.")
        while self.is_running:
            try:
                if self.audio_engine.is_muted or self.audio_engine.is_speaking:
                    time.sleep(0.1)
                    continue
                    
                # Record speech when audio energy surpasses threshold
                audio_data = self.audio_engine.record_until_silence(
                    on_speech_start=lambda: self.gui.set_status("LISTENING")
                )
                
                if len(audio_data) == 0:
                    if not self.audio_engine.is_speaking and not self.audio_engine.is_muted:
                        self.gui.set_status("IDLE")
                    continue
                    
                # 1. Speaker Verification Check (Verify if audio belongs to Sir)
                is_sir = self.audio_engine.speaker_verifier.verify(audio_data, sr=self.audio_engine.sample_rate)
                if not is_sir:
                    logger.info("Ignored speech: Voice does not match Sir's master profile.")
                    self.gui.append_log("Security", "Audio ignored: Voice does not match Sir's profile.", tag="system")
                    self.gui.set_status("IDLE")
                    continue
                    
                # 2. Transcribe audio buffer
                transcription = self.audio_engine.transcribe_audio_array(audio_data)
                if not transcription:
                    self.gui.set_status("IDLE")
                    continue
                    
                logger.info(f"Captured Speech: '{transcription}'")
                
                # 3. Check for wake word or active conversational follow-up
                cleaned = transcription.strip().lower()
                is_wake_word_only = cleaned in [w.lower() for w in config.WAKE_WORDS]
                
                if is_wake_word_only:
                    self.last_interaction_time = time.time()
                    self.gui.append_log("You (Voice)", transcription, tag="user")
                    greeting = (
                        "Sir, ZEN aapki khidmat mein hazir hai. Hukum kijiye?"
                        if config.JARVIS_LANGUAGE in ["hindi", "urdu", "bilingual"]
                        else "Yes Sir, ZEN is online and ready for your command."
                    )
                    self.gui.append_log("ZEN", greeting, tag="jarvis")
                    self.gui.set_status("SPEAKING")
                    self.audio_engine.speak(
                        text=greeting,
                        on_start=lambda: self.gui.set_status("SPEAKING"),
                        on_finish=lambda: self.gui.set_status("LISTENING")
                    )
                    continue
                    
                # Active session window (within 45s of last interaction)
                is_active = (time.time() - self.last_interaction_time) < 45.0
                command = self.audio_engine.extract_wake_command(transcription, is_active_session=is_active)
                
                if command:
                    self.last_interaction_time = time.time()
                    self.gui.append_log("You (Voice)", transcription, tag="user")
                    self.task_queue.put(command)
                else:
                    self.gui.set_status("IDLE")
                    
            except Exception as e:
                logger.exception("Error in voice listener loop")
                time.sleep(0.5)

    def _agent_worker_loop(self):
        """Processes agent queries from the queue, executes tools, and generates voice output."""
        logger.info("Agent query worker thread started.")
        while self.is_running:
            try:
                prompt = self.task_queue.get()
                if prompt is None:
                    break
                    
                self.gui.set_status("THINKING")
                
                # Process with Gemini 2.0 Flash + Screen Vision + Tools
                response_text = self.agent.process_query(
                    user_prompt=prompt,
                    include_screen=True,
                    on_status_change=lambda s: self.gui.set_status(s),
                    on_tool_event=lambda msg: self.gui.append_log("Tool", msg, tag="tool")
                )
                
                # Log Response
                self.gui.append_log("ZEN", response_text, tag="jarvis")
                
                # Speak response if not muted
                if not self.audio_engine.is_muted:
                    self.gui.set_status("SPEAKING")
                    self.audio_engine.speak(
                        text=response_text,
                        on_start=lambda: self.gui.set_status("SPEAKING"),
                        on_finish=lambda: self.gui.set_status("IDLE")
                    )
                else:
                    self.gui.set_status("IDLE")
                    
                self.task_queue.task_done()
                
            except Exception as e:
                logger.exception("Error processing agent task")
                self.gui.append_log("Error", f"An error occurred: {e}", tag="error")
                self.gui.set_status("IDLE")

    def shutdown(self):
        """Gracefully closes background threads, audio engine, and closes the application."""
        logger.info("Shutting down ZEN...")
        self.is_running = False
        self.audio_engine.shutdown()
        self.task_queue.put(None)
        self.gui.destroy()
        sys.exit(0)

def main():
    orchestrator = JarvisOrchestrator()
    orchestrator.start()

if __name__ == "__main__":
    main()
