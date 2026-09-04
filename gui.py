import queue
import threading
import tkinter as tk
from datetime import datetime
from typing import Callable, Optional
import customtkinter as ctk

from config import config

# Set CustomTkinter Visual Theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class JarvisGUI(ctk.CTk):
    """Modern, futuristic Desktop Interface & HUD for CYRO Voice Agent."""
    
    def __init__(
        self,
        on_toggle_monitoring: Callable[[bool], None],
        on_send_text: Callable[[str], None],
        on_reset_context: Optional[Callable[[], None]] = None
    ):
        super().__init__()
        
        self.on_toggle_monitoring = on_toggle_monitoring
        self.on_send_text = on_send_text
        self.on_reset_context = on_reset_context
        
        # Thread-safe UI update queue
        self.ui_queue: queue.Queue = queue.Queue()
        
        # Window configuration
        self.title("Z.E.N. // System Controller")
        self.geometry("720x650")
        self.minsize(580, 500)
        self.configure(fg_color="#0b0f19")
        
        # State
        self.is_monitoring_active = True
        self.current_status = "IDLE"
        
        self._build_ui()
        self._start_queue_listener()

    def _build_ui(self):
        # 1. Header Frame
        header_frame = ctk.CTkFrame(self, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1f2937")
        header_frame.pack(fill="x", padx=16, pady=(16, 8))
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="⚡ Z.E.N.",
            font=ctk.CTkFont(family="Consolas", size=22, weight="bold"),
            text_color="#38bdf8"
        )
        title_label.pack(side="left", padx=16, pady=12)
        
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Autonomous Multimodal Desktop Agent",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        subtitle_label.pack(side="left", padx=4, pady=12)
        
        # Live Status Badge
        self.status_badge = ctk.CTkLabel(
            header_frame,
            text="● IDLE",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            fg_color="#064e3b",
            text_color="#34d399",
            corner_radius=8,
            padx=12,
            pady=4
        )
        self.status_badge.pack(side="right", padx=16, pady=12)

        # 2. Control Bar Frame
        control_frame = ctk.CTkFrame(self, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1f2937")
        control_frame.pack(fill="x", padx=16, pady=8)
        
        # Monitoring Switch
        self.switch_var = ctk.StringVar(value="on")
        self.toggle_switch = ctk.CTkSwitch(
            control_frame,
            text="Voice & Screen Monitoring",
            variable=self.switch_var,
            onvalue="on",
            offvalue="off",
            command=self._on_switch_toggled,
            font=ctk.CTkFont(size=13, weight="bold"),
            progress_color="#0284c7"
        )
        self.toggle_switch.pack(side="left", padx=16, pady=12)
        
        # Wake words display
        wake_text = f"Hotwords: {', '.join(config.WAKE_WORDS)}"
        wake_label = ctk.CTkLabel(
            control_frame,
            text=wake_text,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#64748b"
        )
        wake_label.pack(side="left", padx=12, pady=12)
        
        # Reset Context Button
        reset_btn = ctk.CTkButton(
            control_frame,
            text="Reset Context",
            width=110,
            height=30,
            fg_color="#374151",
            hover_color="#4b5563",
            font=ctk.CTkFont(size=12),
            command=self._on_reset_clicked
        )
        reset_btn.pack(side="right", padx=16, pady=12)

        # 3. Live Terminal / Chat Log Area
        log_container = ctk.CTkFrame(self, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1f2937")
        log_container.pack(fill="both", expand=True, padx=16, pady=8)
        
        log_header = ctk.CTkLabel(
            log_container,
            text="ACTIVITY FEED & TELEMETRY",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color="#64748b"
        )
        log_header.pack(anchor="w", padx=14, pady=(10, 4))
        
        self.log_textbox = ctk.CTkTextbox(
            log_container,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#090d16",
            text_color="#e2e8f0",
            corner_radius=8,
            border_width=1,
            border_color="#1e293b"
        )
        self.log_textbox.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        
        # Configure text color tags in underlying tkinter Text widget
        self.log_textbox.tag_config("user", foreground="#38bdf8")
        self.log_textbox.tag_config("jarvis", foreground="#34d399")
        self.log_textbox.tag_config("tool", foreground="#fbbf24")
        self.log_textbox.tag_config("system", foreground="#94a3b8")
        self.log_textbox.tag_config("error", foreground="#f87171")
        self.log_textbox.tag_config("timestamp", foreground="#475569")

        # 4. Interactive Command Input Box (for dual voice/keyboard control)
        input_frame = ctk.CTkFrame(self, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1f2937")
        input_frame.pack(fill="x", padx=16, pady=(8, 16))
        
        self.entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Type command or query for Jarvis (or speak into your mic)...",
            font=ctk.CTkFont(size=13),
            fg_color="#090d16",
            border_color="#1e293b",
            height=40
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(12, 8), pady=10)
        self.entry.bind("<Return>", lambda event: self._send_text_command())
        
        send_btn = ctk.CTkButton(
            input_frame,
            text="Send",
            width=80,
            height=40,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._send_text_command
        )
        send_btn.pack(side="right", padx=(0, 12), pady=10)

    # ==========================================
    # Event Handlers & Callbacks
    # ==========================================

    def _on_switch_toggled(self):
        is_on = (self.switch_var.get() == "on")
        self.is_monitoring_active = is_on
        self.on_toggle_monitoring(is_on)
        status_text = "Monitoring ON" if is_on else "Monitoring MUTED"
        self.append_log("System", status_text, tag="system")
        if not is_on:
            self.set_status("MUTED")
        else:
            self.set_status("IDLE")

    def _on_reset_clicked(self):
        if self.on_reset_context:
            self.on_reset_context()
        self.append_log("System", "Memory context cleared.", tag="system")

    def _send_text_command(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        self.append_log("You", text, tag="user")
        self.on_send_text(text)

    # ==========================================
    # Thread-Safe UI Update Helpers
    # ==========================================

    def append_log(self, sender: str, message: str, tag: str = "system"):
        """Queues a log message to be safely added in the main GUI thread."""
        self.ui_queue.put(("log", sender, message, tag))

    def set_status(self, status: str):
        """Queues a status change (IDLE, LISTENING, THINKING, SPEAKING, MUTED)."""
        self.ui_queue.put(("status", status))

    def _start_queue_listener(self):
        """Processes queued UI events periodically."""
        try:
            while not self.ui_queue.empty():
                item = self.ui_queue.get_nowait()
                if item[0] == "log":
                    _, sender, message, tag = item
                    self._render_log(sender, message, tag)
                elif item[0] == "status":
                    _, status = item
                    self._render_status(status)
        except Exception:
            pass
        self.after(50, self._start_queue_listener)

    def _render_log(self, sender: str, message: str, tag: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"[{timestamp}] ", "timestamp")
        self.log_textbox.insert("end", f"[{sender}]: ", tag)
        self.log_textbox.insert("end", f"{message}\n\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def _render_status(self, status: str):
        self.current_status = status.upper()
        styles = {
            "IDLE": ("● IDLE", "#064e3b", "#34d399"),
            "LISTENING": ("◉ LISTENING...", "#78350f", "#fbbf24"),
            "THINKING": ("⚡ THINKING...", "#1e1b4b", "#818cf8"),
            "SPEAKING": ("🔊 SPEAKING...", "#0c4a6e", "#38bdf8"),
            "MUTED": ("⊗ MUTED", "#7f1d1d", "#f87171"),
        }
        text, fg, txt_color = styles.get(self.current_status, (f"● {self.current_status}", "#1f2937", "#94a3b8"))
        self.status_badge.configure(text=text, fg_color=fg, text_color=txt_color)
