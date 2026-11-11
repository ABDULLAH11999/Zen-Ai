import queue
import threading
import tkinter as tk
from datetime import datetime
from typing import Callable, Optional, List, Dict, Any
import math
import os
import customtkinter as ctk
import psutil
from PIL import Image, ImageTk, ImageFilter
import numpy as np

from config import config

# Set CustomTkinter Visual Theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class VisualizerCanvas(tk.Canvas):
    """
    Dual-Mode Real 3D Dense Holographic Visualizer for Z.E.N. HUD:
    1. Normal & Talk Mode: True 3D Humanoid Head Geometry directly matching the reference holographic image.
       Constructed from over 47,000 dense volumetric 3D particles with exact anatomical contours
       (sculpted cranium, brow ridge, eye sockets, 3D nose, lips, jawline, and crown specular bloom).
       Rotates in true 3D space (Yaw, Pitch, Roll) with organic gaze, genuine perspective parallax,
       real 3D speech articulation, and ultra-smooth 60 FPS live rendering.
    2. Working / Processing Mode: 3D Cyber Connectivity Cluster with rotating gyroscopic rings & traveling data packets.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(bg="#070a14", highlightthickness=0)
        self.bind("<Configure>", self._on_resize)
        self.center_x = 300
        self.center_y = 220
        self.t = 0.0
        self.current_state = "IDLE"
        self._is_animating = True
        self.tk_face = None
        self.img_id = None
        self.cached_w = 0
        self.cached_h = 0
        self.buf = None
        self.cached_grid = None

        # Organic Gaze & Angle Tracking
        self._init_gaze_controller()
        self._init_models()
        self._animate()

    def _init_gaze_controller(self):
        import time
        self.current_yaw = 0.0       # Left/Right angle in radians
        self.current_pitch = 0.0     # Up/Down angle in radians
        self.current_roll = 0.0      # Natural sympathetic tilt
        self.current_dx = 0.0        # Horizontal pan drift
        self.current_dy = 0.0        # Vertical pan drift

        self.target_yaw = 0.0
        self.target_pitch = 0.0
        self.target_roll = 0.0
        self.target_dx = 0.0
        self.target_dy = 0.0

        self.next_gaze_time = time.time() + 1.0

    def _update_gaze(self):
        import time, random
        now = time.time()
        is_speaking = ("SPEAK" in self.current_state)

        if is_speaking:
            # Face front towards user with natural speech emphasis
            self.target_yaw = math.sin(self.t * 3.2) * 0.08
            self.target_pitch = math.sin(self.t * 4.5) * 0.05
            self.target_roll = math.sin(self.t * 2.5) * 0.03
            self.target_dx = math.sin(self.t * 2.0) * 6.0
            self.target_dy = math.sin(self.t * 2.8) * 4.0
            self.next_gaze_time = now + 1.2
        elif now >= self.next_gaze_time:
            # Standby / Idle: organic random glances in true 3D
            if random.random() < 0.28:
                # Look towards center
                self.target_yaw = random.uniform(-0.05, 0.05)
                self.target_pitch = random.uniform(-0.04, 0.04)
                self.target_roll = random.uniform(-0.02, 0.02)
                self.target_dx = random.uniform(-5, 5)
                self.target_dy = random.uniform(-4, 4)
                dwell = random.uniform(1.8, 3.0)
            else:
                # Glance left or right in true 3D perspective
                self.target_yaw = random.choice([-1, 1]) * random.uniform(0.18, 0.40)
                self.target_pitch = random.uniform(-0.16, 0.16)
                self.target_roll = -self.target_yaw * random.uniform(0.10, 0.22)
                self.target_dx = self.target_yaw * 35.0
                self.target_dy = self.target_pitch * 20.0
                dwell = random.uniform(2.2, 4.0)
            self.next_gaze_time = now + dwell

        # Smooth ease-out lerp
        lerp = 0.065
        self.current_yaw += (self.target_yaw - self.current_yaw) * lerp
        self.current_pitch += (self.target_pitch - self.current_pitch) * lerp
        self.current_roll += (self.target_roll - self.current_roll) * lerp
        self.current_dx += (self.target_dx - self.current_dx) * lerp
        self.current_dy += (self.target_dy - self.current_dy) * lerp

    def _on_resize(self, event):
        self.center_x = max(150, event.width // 2)
        self.center_y = max(140, event.height // 2)

    def set_state(self, state: str):
        self.current_state = state.upper()

    def destroy(self):
        self._is_animating = False
        super().destroy()

    def _init_models(self):
        # 1. Load Dense 3D Reference Head Particles (~47k points)
        pts_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "ref_3d_points.npy")
        cols_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "ref_3d_colors.npy")

        if os.path.exists(pts_path) and os.path.exists(cols_path):
            self.raw_pts = np.load(pts_path)
            self.raw_cols = np.load(cols_path).astype(np.float32)
            # Pre-blend RGB against constant background #070a14 for zero-latency compositing
            alpha = self.raw_cols[:, 3:4] / 255.0
            bg_val = np.array([7.0, 10.0, 20.0], dtype=np.float32)
            self.preblended_rgb = np.clip(self.raw_cols[:, :3] * alpha + bg_val * (1.0 - alpha), 0, 255).astype(np.uint8)
        else:
            self.raw_pts = None
            self.raw_cols = None
            self.preblended_rgb = None

        # 2. 3D Connectivity Network Model (12 Polyhedral Nodes for Working Mode)
        phi = (1 + math.sqrt(5)) / 2
        raw_nodes = [
            (-1, phi, 0), (1, phi, 0), (-1, -phi, 0), (1, -phi, 0),
            (0, -1, phi), (0, 1, phi), (0, -1, -phi), (0, 1, -phi),
            (phi, 0, -1), (phi, 0, 1), (-phi, 0, -1), (-phi, 0, 1)
        ]
        self.connect_nodes = []
        for x, y, z in raw_nodes:
            scale = 52.0
            self.connect_nodes.append((x * scale, y * scale, z * scale))

        self.connect_edges = []
        n_count = len(self.connect_nodes)
        for i in range(n_count):
            for j in range(i + 1, n_count):
                p1 = self.connect_nodes[i]
                p2 = self.connect_nodes[j]
                dist = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2 + (p1[2]-p2[2])**2)
                if dist < 125:
                    self.connect_edges.append((i, j))

    def _project_3d(self, x, y, z, yaw, pitch):
        cos_y, sin_y = math.cos(yaw), math.sin(yaw)
        x1 = x * cos_y + z * sin_y
        z1 = -x * sin_y + z * cos_y
        cos_x, sin_x = math.cos(pitch), math.sin(pitch)
        y2 = y * cos_x - z1 * sin_x
        z2 = y * sin_x + z1 * cos_x

        fov = 430.0
        dist = 360.0
        factor = fov / (z2 + dist)
        px = self.center_x + x1 * factor
        py = self.center_y + y2 * factor
        return px, py, z2

    def _animate(self):
        if not self._is_animating:
            return
        self.t += 0.05

        is_processing = any(w in self.current_state for w in ["THINK", "PROCESS", "EXECUT"])
        if is_processing:
            self._render_3d_connectivity()
        else:
            self._render_hologram_face()

        try:
            self.after(16, self._animate)
        except Exception:
            pass

    def _render_hologram_face(self):
        """Renders Real 3D Dense Humanoid Head Object matching Reference Image at 60 FPS."""
        self._update_gaze()

        w = self.winfo_width() or 600
        h = self.winfo_height() or 400
        cx = self.center_x
        cy = self.center_y

        if self.raw_pts is None or self.preblended_rgb is None:
            return

        # Micro-breathing oscillation and 3D floating
        breathe = math.sin(self.t * 1.5)
        scale = 1.15 + 0.012 * breathe
        y_float = breathe * 3.5

        # Check / Reallocate canvas buffer if resized
        if w != self.cached_w or h != self.cached_h or self.buf is None:
            self.cached_w = w
            self.cached_h = h
            self.buf = np.full((h, w, 4), [7, 10, 20, 255], dtype=np.uint8)
            self.cached_grid = self.buf.copy()
            grid_col = np.array([12, 20, 36, 255], dtype=np.uint8)
            for gx in range(0, w, 55):
                self.cached_grid[:, gx] = grid_col
            for gy in range(0, h, 55):
                self.cached_grid[gy, :] = grid_col

        # Reset buffer to cached background grid
        self.buf[:] = self.cached_grid

        # 3D points
        is_speaking = ("SPEAK" in self.current_state)
        if is_speaking:
            pts = self.raw_pts.copy()
            mouth_open = (math.sin(self.t * 16) * 0.5 + 0.5) * 8.0
            jaw_mask = (pts[:, 1] > 35) & (pts[:, 1] < 90) & (pts[:, 2] > 0)
            if np.any(jaw_mask):
                jaw_y = pts[jaw_mask, 1]
                t_j = (jaw_y - 35) / 55.0
                pts[jaw_mask, 1] += mouth_open * np.sin(t_j * np.pi)
        else:
            pts = self.raw_pts

        # 3D Matrix Rotations
        cos_y, sin_y = math.cos(self.current_yaw), math.sin(self.current_yaw)
        cos_x, sin_x = math.cos(self.current_pitch), math.sin(self.current_pitch)
        cos_z, sin_z = math.cos(self.current_roll), math.sin(self.current_roll)

        x = pts[:, 0] * scale
        y = pts[:, 1] * scale
        z = pts[:, 2] * scale

        # Yaw (Left/Right)
        x1 = x * cos_y + z * sin_y
        z1 = -x * sin_y + z * cos_y

        # Pitch (Up/Down)
        y2 = y * cos_x - z1 * sin_x
        z2 = y * sin_x + z1 * cos_x

        # Roll (Sympathetic Tilt)
        x3 = x1 * cos_z - y2 * sin_z
        y3 = x1 * sin_z + y2 * cos_z

        # Perspective Projection
        fov = 460.0
        dist = 380.0
        factor = fov / (z2 + dist)

        live_cx = cx + self.current_dx
        live_cy = cy + self.current_dy + y_float
        px = np.round(live_cx + x3 * factor).astype(np.int32)
        py = np.round(live_cy + y3 * factor).astype(np.int32)

        # Valid bounds
        valid = (px >= 0) & (px < w) & (py >= 0) & (py < h)
        self.buf[py[valid], px[valid], :3] = self.preblended_rgb[valid]

        # Display via ImageTk without tearing or ghosting
        self.tk_face = ImageTk.PhotoImage(Image.fromarray(self.buf))
        if self.img_id is None:
            self.delete("all")
            self.img_id = self.create_image(0, 0, image=self.tk_face, anchor="nw")
        else:
            self.itemconfig(self.img_id, image=self.tk_face)

    def _render_3d_connectivity(self):
        """Renders 3D Working Connectivity Mesh with traveling data packets & gyroscopic rings."""
        if self.img_id is not None:
            self.delete(self.img_id)
            self.img_id = None
        self.delete("all")
        w = self.winfo_width() or 600
        h = self.winfo_height() or 400
        grid_step = 60
        grid_col = "#0c1424"
        for gx in range(0, w, grid_step):
            self.create_line(gx, 0, gx, h, fill=grid_col, width=1)
        for gy in range(0, h, grid_step):
            self.create_line(0, gy, w, gy, fill=grid_col, width=1)

        yaw = self.t * 0.95
        pitch = self.t * 0.70

        # 1. Project 3D Nodes
        proj_nodes = []
        for nx, ny, nz in self.connect_nodes:
            px, py, pz = self._project_3d(nx, ny, nz, yaw, pitch)
            proj_nodes.append((px, py, pz))

        # 2. Draw Gyroscopic 3D Orbital Rings
        r_outer = 145
        # Ring 1
        ring_pts1 = []
        for i in range(24):
            th = i * 2 * math.pi / 24
            rx = r_outer * math.cos(th)
            ry = r_outer * math.sin(th) * 0.35
            px, py, pz = self._project_3d(rx, ry, 0, yaw * 1.5, pitch)
            ring_pts1.append((px, py))
        for i in range(len(ring_pts1)):
            p1 = ring_pts1[i]
            p2 = ring_pts1[(i + 1) % len(ring_pts1)]
            self.create_line(p1[0], p1[1], p2[0], p2[1], fill="#c084fc", width=1.8)

        # Ring 2 (Cross orbit)
        ring_pts2 = []
        for i in range(24):
            th = i * 2 * math.pi / 24
            rx = r_outer * math.cos(th) * 0.4
            ry = r_outer * math.sin(th)
            px, py, pz = self._project_3d(rx, ry, 0, -yaw * 1.3, pitch * 1.4)
            ring_pts2.append((px, py))
        for i in range(len(ring_pts2)):
            p1 = ring_pts2[i]
            p2 = ring_pts2[(i + 1) % len(ring_pts2)]
            self.create_line(p1[0], p1[1], p2[0], p2[1], fill="#38bdf8", width=1.5)

        # 3. Draw Synaptic Connection Edges
        for i1, i2 in self.connect_edges:
            p1 = proj_nodes[i1]
            p2 = proj_nodes[i2]
            avg_z = (p1[2] + p2[2]) / 2.0
            col = "#a855f7" if avg_z > 0 else "#4c1d95"
            line_w = 2 if avg_z > 10 else 1
            self.create_line(p1[0], p1[1], p2[0], p2[1], fill=col, width=line_w)

        # 4. Draw Traveling Data Packets
        packet_count = 16
        for p in range(packet_count):
            edge_idx = (p * 3) % len(self.connect_edges)
            i1, i2 = self.connect_edges[edge_idx]
            p1 = proj_nodes[i1]
            p2 = proj_nodes[i2]

            prog = (self.t * 2.4 + p * 0.35) % 1.0
            pak_x = p1[0] + (p2[0] - p1[0]) * prog
            pak_y = p1[1] + (p2[1] - p1[1]) * prog

            self.create_oval(pak_x - 3.5, pak_y - 3.5, pak_x + 3.5, pak_y + 3.5,
                             fill="#00f0ff", outline="#ffffff", width=1)

        # 5. Draw 3D Nodes
        sorted_indices = sorted(range(len(proj_nodes)), key=lambda idx: proj_nodes[idx][2])
        for idx in sorted_indices:
            px, py, pz = proj_nodes[idx]
            node_r = max(3.5, 6.5 + pz * 0.04)
            col_fill = "#c084fc" if pz > 0 else "#6b21a8"
            self.create_oval(px - node_r, py - node_r, px + node_r, py + node_r,
                             fill=col_fill, outline="#00f0ff" if pz > 15 else "#818cf8", width=1.5)

        # Central Power Core
        core_r = 18 + int(math.sin(self.t * 5) * 4)
        self.create_oval(self.center_x - core_r, self.center_y - core_r, self.center_x + core_r, self.center_y + core_r,
                         fill="#0d1b2a", outline="#00f0ff", width=2)
        self.create_text(self.center_x, self.center_y, text="⚡", fill="#00f0ff", font=("Segoe UI Symbol", 13, "bold"))


class JarvisGUI(ctk.CTk):
    """
    Futuristic Full-Screen & Windowed Command Center HUD for Z.E.N. Agent:
    - Left Sidebar: Live Telemetry (CPU/RAM/Battery meters) & Activity Terminal Logs
    - Center Core: Holographic Canvas Visualizer + Bottom Command Bar with Voice Dictation & Send
    - Right Sidebar: Conversation Timeline & Interactive Chat Cards (Click card to inspect full response)
    """

    def __init__(
        self,
        on_toggle_monitoring: Callable[[bool], None],
        on_send_text: Callable[[str], None],
        on_reset_context: Optional[Callable[[], None]] = None,
        on_dictate_speech: Optional[Callable[[threading.Event, Callable[[str], None], Callable[[str], None]], None]] = None,
        on_replay_speech: Optional[Callable[[str], None]] = None
    ):
        super().__init__()

        self.on_toggle_monitoring = on_toggle_monitoring
        self.on_send_text = on_send_text
        self.on_reset_context = on_reset_context
        self.on_dictate_speech = on_dictate_speech
        self.on_replay_speech = on_replay_speech

        # Thread-safe UI queue
        self.ui_queue: queue.Queue = queue.Queue()

        # Window settings
        self.title("Z.E.N. // Autonomous Multimodal Command Center")
        self.geometry("1280x780")
        self.minsize(980, 620)
        self.configure(fg_color="#070a13")

        # Fullscreen state
        self.is_fullscreen = False
        self.bind("<F11>", lambda event: self.toggle_fullscreen())
        self.bind("<Escape>", lambda event: self.exit_fullscreen())

        # Dictation state
        self.is_dictating = False
        self.dictate_stop_event = threading.Event()
        self.dictate_thread: Optional[threading.Thread] = None

        # State & Chat storage
        self.is_monitoring_active = True
        self.current_status = "IDLE"
        self.chat_history: List[Dict[str, Any]] = []

        self._build_panoramic_layout()
        self._start_queue_listener()
        self._start_vitals_poller()

    # ==========================================
    # Fullscreen Controls
    # ==========================================

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        btn_text = "🗗 Window" if self.is_fullscreen else "⛶ Fullscreen"
        self.fullscreen_btn.configure(text=btn_text)

    def exit_fullscreen(self):
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.attributes("-fullscreen", False)
            self.fullscreen_btn.configure(text="⛶ Fullscreen")

    # ==========================================
    # UI Layout Construction (3-Column Cyber Grid)
    # ==========================================

    def _build_panoramic_layout(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0, minsize=310)  # Left: Telemetry & Logs
        self.grid_columnconfigure(1, weight=1)              # Center: HUD Visualizer & Input
        self.grid_columnconfigure(2, weight=0, minsize=330)  # Right: Chat History & Inspector

        self._build_left_sidebar()
        self._build_center_core()
        self._build_right_sidebar()

    # ------------------------------------------
    # 1. Left Sidebar: Telemetry & Activity Logs
    # ------------------------------------------
    def _build_left_sidebar(self):
        left_frame = ctk.CTkFrame(
            self, fg_color="#0b111e", corner_radius=0, border_width=1, border_color="#172238"
        )
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=0)
        left_frame.grid_rowconfigure(2, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        # Header
        head_box = ctk.CTkFrame(left_frame, fg_color="transparent")
        head_box.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))

        lbl = ctk.CTkLabel(
            head_box,
            text="⚡ TELEMETRY & LOGS",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color="#38bdf8"
        )
        lbl.pack(side="left")

        # Hardware Vitals Card
        vitals_card = ctk.CTkFrame(
            left_frame, fg_color="#0f172a", corner_radius=12, border_width=1, border_color="#1e293b"
        )
        vitals_card.grid(row=1, column=0, sticky="ew", padx=14, pady=8)

        # CPU Meter
        cpu_box = ctk.CTkFrame(vitals_card, fg_color="transparent")
        cpu_box.pack(fill="x", padx=12, pady=(10, 4))
        self.cpu_label = ctk.CTkLabel(
            cpu_box, text="CPU: 0%", font=ctk.CTkFont(family="Consolas", size=11), text_color="#94a3b8"
        )
        self.cpu_label.pack(side="left")
        self.cpu_bar = ctk.CTkProgressBar(vitals_card, height=6, progress_color="#38bdf8", fg_color="#1e293b")
        self.cpu_bar.set(0.1)
        self.cpu_bar.pack(fill="x", padx=12, pady=(0, 6))

        # RAM Meter
        ram_box = ctk.CTkFrame(vitals_card, fg_color="transparent")
        ram_box.pack(fill="x", padx=12, pady=(4, 4))
        self.ram_label = ctk.CTkLabel(
            ram_box, text="RAM: 0%", font=ctk.CTkFont(family="Consolas", size=11), text_color="#94a3b8"
        )
        self.ram_label.pack(side="left")
        self.ram_bar = ctk.CTkProgressBar(vitals_card, height=6, progress_color="#a855f7", fg_color="#1e293b")
        self.ram_bar.set(0.4)
        self.ram_bar.pack(fill="x", padx=12, pady=(0, 6))

        # Battery Gauge
        batt_box = ctk.CTkFrame(vitals_card, fg_color="transparent")
        batt_box.pack(fill="x", padx=12, pady=(4, 10))
        self.batt_label = ctk.CTkLabel(
            batt_box, text="BATTERY: 100% ⚡", font=ctk.CTkFont(family="Consolas", size=11), text_color="#34d399"
        )
        self.batt_label.pack(side="left")

        # Live Activity Feed Console
        log_box = ctk.CTkFrame(
            left_frame, fg_color="#080d19", corner_radius=12, border_width=1, border_color="#1e293b"
        )
        log_box.grid(row=2, column=0, sticky="nsew", padx=14, pady=8)
        log_box.grid_rowconfigure(1, weight=1)
        log_box.grid_columnconfigure(0, weight=1)

        log_head = ctk.CTkLabel(
            log_box,
            text="TERMINAL ACTIVITY FEED",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#64748b"
        )
        log_head.grid(row=0, column=0, sticky="w", padx=12, pady=(8, 4))

        self.log_textbox = ctk.CTkTextbox(
            log_box,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#050811",
            text_color="#e2e8f0",
            corner_radius=8,
            border_width=1,
            border_color="#172238"
        )
        self.log_textbox.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        # Text color tags
        self.log_textbox.tag_config("user", foreground="#38bdf8")
        self.log_textbox.tag_config("jarvis", foreground="#34d399")
        self.log_textbox.tag_config("tool", foreground="#fbbf24")
        self.log_textbox.tag_config("system", foreground="#94a3b8")
        self.log_textbox.tag_config("error", foreground="#f87171")
        self.log_textbox.tag_config("timestamp", foreground="#475569")

        # Bottom Actions in Left Sidebar
        bottom_left = ctk.CTkFrame(left_frame, fg_color="transparent")
        bottom_left.grid(row=3, column=0, sticky="ew", padx=14, pady=(4, 14))

        clear_btn = ctk.CTkButton(
            bottom_left,
            text="Clear Feed",
            height=28,
            width=100,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(size=11),
            command=self._clear_logs
        )
        clear_btn.pack(side="left", padx=(0, 6))

        reset_btn = ctk.CTkButton(
            bottom_left,
            text="Reset Context",
            height=28,
            width=110,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(size=11),
            command=self._on_reset_clicked
        )
        reset_btn.pack(side="right")

    # ------------------------------------------
    # 2. Center Core: Futuristic HUD & Command
    # ------------------------------------------
    def _build_center_core(self):
        center_frame = ctk.CTkFrame(self, fg_color="#070a14", corner_radius=0)
        center_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=0)
        center_frame.grid_rowconfigure(1, weight=1)
        center_frame.grid_columnconfigure(0, weight=1)

        # Header Bar
        header = ctk.CTkFrame(
            center_frame, fg_color="#0c1220", corner_radius=12, border_width=1, border_color="#1e293b"
        )
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))

        title_lbl = ctk.CTkLabel(
            header,
            text="⚡ Z.E.N. // MULTIMODAL AGENT",
            font=ctk.CTkFont(family="Consolas", size=18, weight="bold"),
            text_color="#00f0ff"
        )
        title_lbl.pack(side="left", padx=16, pady=10)

        # Voice & Screen Switch
        self.switch_var = ctk.StringVar(value="on")
        self.toggle_switch = ctk.CTkSwitch(
            header,
            text="Monitoring",
            variable=self.switch_var,
            onvalue="on",
            offvalue="off",
            command=self._on_switch_toggled,
            font=ctk.CTkFont(size=12, weight="bold"),
            progress_color="#0284c7"
        )
        self.toggle_switch.pack(side="left", padx=14, pady=10)

        # Fullscreen Toggle Button
        self.fullscreen_btn = ctk.CTkButton(
            header,
            text="⛶ Fullscreen",
            width=100,
            height=30,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.toggle_fullscreen
        )
        self.fullscreen_btn.pack(side="right", padx=14, pady=10)

        # Status Badge
        self.status_badge = ctk.CTkLabel(
            header,
            text="● IDLE",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            fg_color="#064e3b",
            text_color="#34d399",
            corner_radius=8,
            padx=12,
            pady=4
        )
        self.status_badge.pack(side="right", padx=6, pady=10)

        # Futuristic AI Canvas Visualizer
        canvas_container = ctk.CTkFrame(
            center_frame, fg_color="#080d19", corner_radius=16, border_width=1, border_color="#172238"
        )
        canvas_container.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        canvas_container.grid_rowconfigure(0, weight=1)
        canvas_container.grid_columnconfigure(0, weight=1)

        self.visualizer = VisualizerCanvas(canvas_container)
        self.visualizer.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        # Floating Bottom Command Bar (With Mic inside right before Send)
        cmd_bar = ctk.CTkFrame(
            center_frame, fg_color="#0c1322", corner_radius=16, border_width=1, border_color="#1e293b"
        )
        cmd_bar.grid(row=2, column=0, sticky="ew", padx=16, pady=(8, 16))

        # Command text input entry
        self.entry = ctk.CTkEntry(
            cmd_bar,
            placeholder_text="Hukum kijiye Sir, ya mic se Roman Urdu / English mein boliye...",
            font=ctk.CTkFont(size=13),
            fg_color="#080c18",
            border_color="#1e293b",
            height=44
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(12, 6), pady=10)
        self.entry.bind("<Return>", lambda event: self._send_text_command())

        # Integrated Voice Dictation Mic Button (Red-boxed by user right before Send)
        self.mic_btn = ctk.CTkButton(
            cmd_bar,
            text="🎙️ Mic",
            width=80,
            height=44,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._toggle_voice_dictation
        )
        self.mic_btn.pack(side="left", padx=4, pady=10)

        # Send Button
        self.send_btn = ctk.CTkButton(
            cmd_bar,
            text="⚡ Send",
            width=84,
            height=44,
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._send_text_command
        )
        self.send_btn.pack(side="right", padx=(4, 12), pady=10)

    # ------------------------------------------
    # 3. Right Sidebar: Conversation History & Inspector
    # ------------------------------------------
    def _build_right_sidebar(self):
        right_frame = ctk.CTkFrame(
            self, fg_color="#0b111e", corner_radius=0, border_width=1, border_color="#172238"
        )
        right_frame.grid(row=0, column=2, sticky="nsew", padx=(2, 0), pady=0)
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_rowconfigure(3, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        # Header
        head_box = ctk.CTkFrame(right_frame, fg_color="transparent")
        head_box.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))

        title = ctk.CTkLabel(
            head_box,
            text="💬 CHATS & ACTIONS",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color="#38bdf8"
        )
        title.pack(anchor="w")

        sub = ctk.CTkLabel(
            head_box,
            text="Click card to inspect full response & tool",
            font=ctk.CTkFont(size=11),
            text_color="#64748b"
        )
        sub.pack(anchor="w", pady=(3, 0))

        # Scrollable Cards Feed
        self.cards_scroll = ctk.CTkScrollableFrame(
            right_frame, fg_color="#070a14", corner_radius=12, border_width=1, border_color="#1e293b"
        )
        self.cards_scroll.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
        self.cards_scroll.grid_columnconfigure(0, weight=1)

        # Inspector Panel Header
        insp_header = ctk.CTkLabel(
            right_frame,
            text="RESPONSE INSPECTOR",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#64748b"
        )
        insp_header.grid(row=2, column=0, sticky="w", padx=14, pady=(8, 2))

        # Inspector Box (Shows final response for clicked chat)
        insp_box = ctk.CTkFrame(
            right_frame, fg_color="#080d19", corner_radius=12, border_width=1, border_color="#1e293b"
        )
        insp_box.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 14))
        insp_box.grid_rowconfigure(1, weight=1)
        insp_box.grid_columnconfigure(0, weight=1)

        self.inspector_title = ctk.CTkLabel(
            insp_box,
            text="Select any card above to view details",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#94a3b8"
        )
        self.inspector_title.grid(row=0, column=0, sticky="w", padx=12, pady=(8, 4))

        self.inspector_textbox = ctk.CTkTextbox(
            insp_box,
            wrap="word",
            font=ctk.CTkFont(size=12),
            fg_color="#050811",
            text_color="#e2e8f0",
            corner_radius=8,
            border_width=1,
            border_color="#172238"
        )
        self.inspector_textbox.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

    # ==========================================
    # Live Voice Dictation Handler
    # ==========================================

    def _toggle_voice_dictation(self):
        """Toggles real-time microphone dictation directly into the text input box."""
        if not self.is_dictating:
            self.is_dictating = True
            self.dictate_stop_event.clear()
            self.mic_btn.configure(
                text="🔴 Dictating...",
                fg_color="#dc2626",
                hover_color="#b91c1c"
            )
            self.set_status("DICTATING")
            self.append_log("Dictation", "Voice dictation started. Speak in English or Urdu...", tag="system")

            if self.on_dictate_speech:
                self.dictate_thread = threading.Thread(
                    target=self.on_dictate_speech,
                    args=(
                        self.dictate_stop_event,
                        lambda text: self.ui_queue.put(("dictated_text", text)),
                        lambda status: self.ui_queue.put(("dictate_status", status))
                    ),
                    daemon=True
                )
                self.dictate_thread.start()
        else:
            self._stop_voice_dictation()

    def _stop_voice_dictation(self):
        self.is_dictating = False
        self.dictate_stop_event.set()
        self.mic_btn.configure(
            text="🎙️ Mic",
            fg_color="#1e293b",
            hover_color="#334155"
        )
        self.set_status("IDLE")
        self.append_log("Dictation", "Voice dictation stopped.", tag="system")

    # ==========================================
    # Event Handlers & Chat History
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

    def _clear_logs(self):
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

    def _send_text_command(self):
        text = self.entry.get().strip()
        if not text:
            return
        if self.is_dictating:
            self._stop_voice_dictation()
        self.entry.delete(0, "end")
        self.append_log("You", text, tag="user")
        self.add_chat_card(prompt=text)
        self.on_send_text(text)

    def add_chat_card(self, prompt: str):
        """Creates an interactive chat card in the right sidebar."""
        card_id = len(self.chat_history)
        timestamp = datetime.now().strftime("%H:%M:%S")
        record = {
            "id": card_id,
            "timestamp": timestamp,
            "prompt": prompt,
            "response": "Processing command...",
            "status": "In Progress"
        }
        self.chat_history.append(record)

        card = ctk.CTkFrame(
            self.cards_scroll,
            fg_color="#0f172a",
            corner_radius=10,
            border_width=1,
            border_color="#1e293b",
            cursor="hand2"
        )
        card.pack(fill="x", padx=4, pady=4)

        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=10, pady=(8, 2))

        time_lbl = ctk.CTkLabel(
            top_row, text=f"[{timestamp}]", font=ctk.CTkFont(family="Consolas", size=10), text_color="#64748b"
        )
        time_lbl.pack(side="left")

        status_pill = ctk.CTkLabel(
            top_row,
            text="⚡ Running",
            font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
            fg_color="#1e1b4b",
            text_color="#c084fc",
            corner_radius=6,
            padx=6,
            pady=2
        )
        status_pill.pack(side="right")
        record["status_pill"] = status_pill

        prompt_lbl = ctk.CTkLabel(
            card,
            text=prompt if len(prompt) < 42 else prompt[:40] + "...",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#e2e8f0",
            anchor="w"
        )
        prompt_lbl.pack(fill="x", padx=10, pady=(2, 8))

        # Make card and its children clickable to inspect
        def _on_card_click(event=None, cid=card_id):
            self.inspect_chat(cid)

        card.bind("<Button-1>", _on_card_click)
        top_row.bind("<Button-1>", _on_card_click)
        time_lbl.bind("<Button-1>", _on_card_click)
        status_pill.bind("<Button-1>", _on_card_click)
        prompt_lbl.bind("<Button-1>", _on_card_click)

    def update_last_chat_card(self, response: str):
        """Updates the most recent chat card with the final response."""
        if self.chat_history:
            last = self.chat_history[-1]
            last["response"] = response
            last["status"] = "Completed"
            if "status_pill" in last and last["status_pill"].winfo_exists():
                last["status_pill"].configure(
                    text="✓ Done",
                    fg_color="#064e3b",
                    text_color="#34d399"
                )
            # Auto-inspect current response
            self.inspect_chat(last["id"])

    def inspect_chat(self, card_id: int):
        """Displays chat details & response in the Inspector panel."""
        if 0 <= card_id < len(self.chat_history):
            item = self.chat_history[card_id]
            self.inspector_title.configure(text=f"Card #{item['id']+1} // [{item['timestamp']}]")
            self.inspector_textbox.configure(state="normal")
            self.inspector_textbox.delete("1.0", "end")
            self.inspector_textbox.insert("end", f"PROMPT:\n{item['prompt']}\n\n", "prompt")
            self.inspector_textbox.insert("end", f"STATUS: {item['status']}\n\n", "status")
            self.inspector_textbox.insert("end", f"ZEN RESPONSE:\n{item['response']}\n", "response")
            self.inspector_textbox.configure(state="disabled")

    # ==========================================
    # Thread-Safe UI Helpers
    # ==========================================

    def append_log(self, sender: str, message: str, tag: str = "system"):
        self.ui_queue.put(("log", sender, message, tag))

    def set_status(self, status: str):
        self.ui_queue.put(("status", status))

    def insert_dictated_text(self, text: str):
        self.ui_queue.put(("dictated_text", text))

    def notify_chat_completed(self, response: str):
        self.ui_queue.put(("chat_complete", response))

    def _start_queue_listener(self):
        try:
            while not self.ui_queue.empty():
                item = self.ui_queue.get_nowait()
                msg_type = item[0]
                if msg_type == "log":
                    _, sender, message, tag = item
                    self._render_log(sender, message, tag)
                elif msg_type == "status":
                    _, status = item
                    self._render_status(status)
                elif msg_type == "dictated_text":
                    _, text = item
                    self._render_dictated_text(text)
                elif msg_type == "dictate_status":
                    _, status = item
                    self._render_status(f"DICTATE_{status}")
                elif msg_type == "chat_complete":
                    _, response = item
                    self.update_last_chat_card(response)
        except Exception:
            pass
        self.after(40, self._start_queue_listener)

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
        self.visualizer.set_state(self.current_status)
        styles = {
            "IDLE": ("● IDLE", "#064e3b", "#34d399"),
            "LISTENING": ("◉ LISTENING...", "#78350f", "#fbbf24"),
            "THINKING": ("⚡ THINKING...", "#1e1b4b", "#818cf8"),
            "SPEAKING": ("🔊 SPEAKING...", "#0c4a6e", "#38bdf8"),
            "DICTATING": ("🔴 DICTATING...", "#7f1d1d", "#f87171"),
            "DICTATE_LISTENING": ("🔴 SPEAK NOW...", "#7f1d1d", "#f87171"),
            "DICTATE_TRANSCRIBING": ("⚡ TRANSCRIBING...", "#1e1b4b", "#c084fc"),
            "MUTED": ("⊗ MUTED", "#7f1d1d", "#f87171"),
        }
        text, fg, txt_color = styles.get(self.current_status, (f"● {self.current_status}", "#1f2937", "#94a3b8"))
        self.status_badge.configure(text=text, fg_color=fg, text_color=txt_color)

    def _render_dictated_text(self, text: str):
        """Inserts speech-dictated text directly into entry field."""
        curr = self.entry.get().strip()
        new_val = f"{curr} {text}".strip() if curr else text
        self.entry.delete(0, "end")
        self.entry.insert(0, new_val)
        self.entry.icursor("end")

    # ==========================================
    # System Hardware Vitals Poller
    # ==========================================

    def _start_vitals_poller(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            self.cpu_label.configure(text=f"CPU: {cpu:.0f}%")
            self.cpu_bar.set(max(0.05, min(1.0, cpu / 100.0)))
            self.ram_label.configure(text=f"RAM: {ram:.0f}%")
            self.ram_bar.set(max(0.05, min(1.0, ram / 100.0)))

            batt = psutil.sensors_battery()
            if batt:
                p = batt.percent
                icon = "⚡" if batt.power_plugged else "🔋"
                self.batt_label.configure(text=f"BATTERY: {p}% {icon}")
            else:
                self.batt_label.configure(text="POWER: AC ONLINE ⚡")
        except Exception:
            pass
        self.after(2000, self._start_vitals_poller)
