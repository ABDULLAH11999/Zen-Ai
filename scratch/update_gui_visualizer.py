import os
import math
import numpy as np

gui_path = r"F:\Ai Tools\Zen Agent\Zen Ai\gui.py"
with open(gui_path, "r", encoding="utf-8") as f:
    content = f.read()

start_marker = "class VisualizerCanvas(tk.Canvas):"
end_marker = "    def _render_3d_connectivity(self):"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

assert start_idx != -1, "start_marker not found"
assert end_idx != -1, "end_marker not found"

new_visualizer = '''class VisualizerCanvas(tk.Canvas):
    """
    Dual-Mode 3D Futuristic AI Hologram Visualizer:
    1. Normal & Talk Mode: Photorealistic 3D Holographic Particle Scan-Line Humanoid Head
       (modeled directly on Image 1), blended seamlessly into the command center canvas with
       dynamic mouth/jaw speech articulation, vertical laser scanwave, and ambient cyber dust.
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
        self._init_models()
        self._animate()

    def _on_resize(self, event):
        self.center_x = max(150, event.width // 2)
        self.center_y = max(140, event.height // 2)

    def set_state(self, state: str):
        self.current_state = state.upper()

    def destroy(self):
        self._is_animating = False
        super().destroy()

    def _init_models(self):
        import random
        # 1. Load Photorealistic Blended 3D Holographic Head (Image 1 asset)
        self.raw_face_img = None
        self.mouth_frames = {}
        model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "hologram_face.png")
        if os.path.exists(model_path):
            try:
                self.raw_face_img = Image.open(model_path).convert("RGBA")
                base_arr = np.array(self.raw_face_img)
                self.face_h, self.face_w = base_arr.shape[:2]

                # Precompute 16 mouth/jaw speech articulation levels (0 to 15 px vertical displacement)
                jaw_start = 228
                jaw_end = 340
                jaw_h = jaw_end - jaw_start

                for m in range(16):
                    if m == 0:
                        self.mouth_frames[0] = self.raw_face_img
                        continue
                    disp_map = np.zeros(self.face_h)
                    for y in range(jaw_start, jaw_end):
                        progress = (y - jaw_start) / jaw_h
                        disp_map[y] = int(m * math.sin(progress * math.pi * 0.75))

                    out_arr = base_arr.copy()
                    for y in range(self.face_h - 1, jaw_start, -1):
                        dy = int(disp_map[y])
                        if dy > 0 and (y - dy) >= 0:
                            out_arr[y, 90:245] = base_arr[y - dy, 90:245]
                    self.mouth_frames[m] = Image.fromarray(out_arr)
            except Exception as e:
                print(f"[Visualizer] Notice loading face model: {e}")
                self.raw_face_img = None

        if self.raw_face_img is None:
            self.face_w, self.face_h = 335, 348

        # 2. Ambient glittering cyber dust particles (Image 1 sparkles)
        self.ambient_particles = []
        for _ in range(45):
            self.ambient_particles.append({
                "x": random.uniform(-140, 140),
                "y": random.uniform(-150, 150),
                "speed": random.uniform(0.4, 1.2),
                "phase": random.uniform(0, math.pi * 2)
            })

        # 3. 3D Connectivity Network Model (12 Polyhedral Nodes for Working Mode)
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
        self.delete("all")
        self.t += 0.05

        # Subtle background cyber grid lines
        grid_step = 60
        grid_col = "#0c1424"
        w = self.winfo_width() or 600
        h = self.winfo_height() or 400
        for gx in range(0, w, grid_step):
            self.create_line(gx, 0, gx, h, fill=grid_col, width=1)
        for gy in range(0, h, grid_step):
            self.create_line(0, gy, w, gy, fill=grid_col, width=1)

        is_processing = any(w in self.current_state for w in ["THINK", "PROCESS", "EXECUT"])
        if is_processing:
            self._render_3d_connectivity()
        else:
            self._render_hologram_face()

        try:
            self.after(30, self._animate)
        except Exception:
            pass

    def _render_hologram_face(self):
        """Renders Photorealistic 3D Blended Holographic Head directly matching Image 1."""
        # 3D Floating and Breathing
        breathe = math.sin(self.t * 1.4)
        y_float = breathe * 6.0
        scale = 0.88 + 0.015 * breathe
        rot_angle = math.sin(self.t * 0.7) * 2.2  # Subtle 3D tilt

        is_speaking = ("SPEAK" in self.current_state)

        # Dynamic speech articulation (jaw displacement)
        if is_speaking:
            mouth_val = int(min(15, max(0, (math.sin(self.t * 16) * 0.5 + 0.5) * 11.0 + (math.sin(self.t * 26) * 0.3) * 4.0)))
        else:
            mouth_val = 0

        # Background Holographic Aura Ring
        r_ring = 155 + math.sin(self.t * 2.0) * 6
        arc_ang = (self.t * 30) % 360
        self.create_oval(self.center_x - r_ring, self.center_y + y_float - r_ring,
                         self.center_x + r_ring, self.center_y + y_float + r_ring,
                         outline="#0d2137", width=1.5)
        self.create_arc(self.center_x - r_ring - 4, self.center_y + y_float - r_ring - 4,
                        self.center_x + r_ring + 4, self.center_y + y_float + r_ring + 4,
                        start=arc_ang, extent=65, outline="#00f0ff", width=2.5, style="arc")
        self.create_arc(self.center_x - r_ring - 4, self.center_y + y_float - r_ring - 4,
                        self.center_x + r_ring + 4, self.center_y + y_float + r_ring + 4,
                        start=arc_ang + 180, extent=45, outline="#38bdf8", width=1.5, style="arc")

        # Ambient Glittering Cyber Dust (matching Image 1 particles)
        for p in self.ambient_particles:
            px = self.center_x + p["x"] + math.sin(self.t * p["speed"] + p["phase"]) * 14
            py = self.center_y + y_float + p["y"] + math.cos(self.t * p["speed"] * 0.8) * 12
            alpha = (math.sin(self.t * 3.0 + p["phase"]) + 1.0) / 2.0
            if alpha > 0.4:
                col = "#e0f7fa" if alpha > 0.75 else "#38bdf8"
                sz = 1.5 if alpha > 0.75 else 1.0
                self.create_oval(px - sz, py - sz, px + sz, py + sz, fill=col, outline="")

        # Render 3D Articulated Blended Hologram Face
        target_w = int(self.face_w * scale)
        target_h = int(self.face_h * scale)
        if self.mouth_frames and mouth_val in self.mouth_frames:
            face_img = self.mouth_frames[mouth_val]
            scaled = face_img.resize((target_w, target_h), Image.Resampling.BILINEAR)
            if abs(rot_angle) > 0.3:
                scaled = scaled.rotate(rot_angle, resample=Image.Resampling.BICUBIC, expand=False)
            self.tk_face = ImageTk.PhotoImage(scaled)
            self.create_image(self.center_x, self.center_y + y_float, image=self.tk_face, anchor="center")

        # Vertical Luminescence Laser Scanline Wave
        scan_y = self.center_y + y_float + math.sin(self.t * 2.2) * (target_h * 0.42)
        self.create_line(self.center_x - target_w * 0.38, scan_y,
                         self.center_x + target_w * 0.38, scan_y,
                         fill="#e0f7fa", width=2.0)
        self.create_line(self.center_x - target_w * 0.44, scan_y,
                         self.center_x + target_w * 0.44, scan_y,
                         fill="#00f0ff", width=1.0)

        # Dynamic Voice Ripples radiating during speech
        if is_speaking:
            for rip in range(3):
                rip_r = r_ring + ((self.t * 80 + rip * 45) % 90)
                rip_alpha = 1.0 - (rip_r - r_ring) / 90.0
                if rip_alpha > 0.05:
                    self.create_oval(self.center_x - rip_r, self.center_y + y_float - rip_r,
                                     self.center_x + rip_r, self.center_y + y_float + rip_r,
                                     outline="#00f0ff" if rip % 2 == 0 else "#38bdf8",
                                     width=1.5)

'''

updated_content = content[:start_idx] + new_visualizer + content[end_idx:]
with open(gui_path, "w", encoding="utf-8") as f:
    f.write(updated_content)

print("Updated gui.py VisualizerCanvas successfully.")

