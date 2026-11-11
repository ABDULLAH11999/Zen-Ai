import os

gui_path = r"F:\Ai Tools\Zen Agent\Zen Ai\gui.py"
with open(gui_path, "r", encoding="utf-8") as f:
    gui_code = f.read()

start_marker = "class VisualizerCanvas(tk.Canvas):"
end_marker = "class JarvisGUI(ctk.CTk):"

v_start = gui_code.find(start_marker)
v_end = gui_code.find(end_marker)

assert v_start != -1, "VisualizerCanvas not found in gui.py"
assert v_end != -1, "JarvisGUI not found in gui.py"

new_visualizer_canvas = '''class VisualizerCanvas(tk.Canvas):
    """
    Dual-Mode Real 3D Holographic Visualizer for Z.E.N. HUD:
    1. Normal & Talk Mode: True 3D Humanoid Head Geometry (sliced from 3D anatomical head mesh),
       rendered with dense continuous horizontal cybernetic scanlines, dynamic multi-axis 3D gaze
       (organic left-to-right & up-to-down turns with genuine 3D perspective parallax),
       real 3D jaw speech articulation, and ambient cyber dust.
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
            # When speaking, mostly face front towards user with natural speech emphasis
            self.target_yaw = math.sin(self.t * 3.2) * 0.10
            self.target_pitch = math.sin(self.t * 4.5) * 0.06
            self.target_roll = math.sin(self.t * 2.5) * 0.04
            self.target_dx = math.sin(self.t * 2.0) * 8.0
            self.target_dy = math.sin(self.t * 2.8) * 5.0
            self.next_gaze_time = now + 1.2
        elif now >= self.next_gaze_time:
            # Idle / Standby: Organic random glances in true 3D
            if random.random() < 0.28:
                # Look towards center
                self.target_yaw = random.uniform(-0.06, 0.06)
                self.target_pitch = random.uniform(-0.05, 0.05)
                self.target_roll = random.uniform(-0.02, 0.02)
                self.target_dx = random.uniform(-6, 6)
                self.target_dy = random.uniform(-5, 5)
                dwell = random.uniform(1.8, 3.0)
            else:
                # Random glance left or right (yaw up to +/- 28 deg for true 3D profile)
                self.target_yaw = random.choice([-1, 1]) * random.uniform(0.18, 0.48)
                # Random pitch up or down (pitch up to +/- 16 deg)
                self.target_pitch = random.uniform(-0.24, 0.24)
                # Sympathetic head roll
                self.target_roll = -self.target_yaw * random.uniform(0.15, 0.28)
                # Translation in glance direction
                self.target_dx = self.target_yaw * 45.0
                self.target_dy = self.target_pitch * 28.0
                dwell = random.uniform(2.2, 4.2)
            self.next_gaze_time = now + dwell

        # Smooth ease-out lerp
        lerp = 0.055
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
        import random
        # 1. Load Real 3D Head Scanline Points (from 3D anatomical mesh)
        mesh_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "head_scanlines.npy")
        if os.path.exists(mesh_path):
            data = np.load(mesh_path)
            self.head_points = data[:, :3].copy()
            unique_y = np.unique(self.head_points[:, 1])
            self.num_slices = len(unique_y)
            self.pts_per_ring = len(self.head_points) // self.num_slices
        else:
            self.head_points = None
            self.num_slices = 90
            self.pts_per_ring = 75

        # 2. Ambient glittering cyber dust particles
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
        self.t += 0.05

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
        """Renders Real 3D Head Object with Continuous Cyber Scanlines & Organic Gaze."""
        from PIL import ImageDraw
        self._update_gaze()

        w = self.winfo_width() or 600
        h = self.winfo_height() or 400
        cx = self.center_x
        cy = self.center_y

        if self.head_points is None:
            return

        # Micro-breathing oscillation and 3D floating
        breathe = math.sin(self.t * 1.5)
        scale = 0.90 + 0.015 * breathe
        y_float = breathe * 4.0

        # Copy points for real-time 3D transformation
        pts = self.head_points.copy()

        # Real 3D jaw speech articulation when speaking
        is_speaking = ("SPEAK" in self.current_state)
        if is_speaking:
            mouth_open = (math.sin(self.t * 16) * 0.5 + 0.5) * 8.0
            jaw_mask = (pts[:, 1] > 35) & (pts[:, 1] < 85) & (pts[:, 2] > 0)
            if np.any(jaw_mask):
                jaw_y = pts[jaw_mask, 1]
                t_j = (jaw_y - 35) / 50.0
                pts[jaw_mask, 1] += mouth_open * np.sin(t_j * np.pi)

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
        fov = 430.0
        dist = 330.0
        factor = fov / (z2 + dist)

        live_cx = cx + self.current_dx
        live_cy = cy + self.current_dy + y_float
        px = live_cx + x3 * factor
        py = live_cy + y3 * factor

        # Draw onto high-performance PIL buffer
        img = Image.new("RGBA", (w, h), (7, 10, 20, 255))
        draw = ImageDraw.Draw(img)

        # Background HUD grid
        grid_step = 60
        grid_col = (12, 20, 36, 255)
        for gx in range(0, w, grid_step):
            draw.line([(gx, 0), (gx, h)], fill=grid_col, width=1)
        for gy in range(0, h, grid_step):
            draw.line([(0, gy), (w, gy)], fill=grid_col, width=1)

        # Ambient Glittering Cyber Dust
        for p in self.ambient_particles:
            d_x = cx + p["x"] + math.sin(self.t * p["speed"] + p["phase"]) * 14
            d_y = cy + p["y"] + math.cos(self.t * p["speed"] * 0.8) * 12
            alpha = (math.sin(self.t * 3.0 + p["phase"]) + 1.0) / 2.0
            if alpha > 0.4:
                col = (224, 247, 250, 240) if alpha > 0.75 else (56, 189, 248, 180)
                sz = 1.5 if alpha > 0.75 else 1.0
                draw.ellipse([d_x-sz, d_y-sz, d_x+sz, d_y+sz], fill=col)

        # Render 3D Continuous Scanline Rings
        for s in range(self.num_slices):
            start_idx = s * self.pts_per_ring
            end_idx = start_idx + self.pts_per_ring

            rx = px[start_idx:end_idx]
            ry = py[start_idx:end_idx]
            rz = z2[start_idx:end_idx]

            for i in range(self.pts_per_ring - 1):
                z1_p = rz[i]
                z2_p = rz[i+1]
                z_avg = (z1_p + z2_p) / 2.0

                # Clip back-facing occluded points
                if z_avg < -22.0:
                    continue

                p1 = (rx[i], ry[i])
                p2 = (rx[i+1], ry[i+1])

                seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                if seg_len > 16.0:
                    continue

                # Depth shading (Image 1 palette)
                if z_avg > 40:
                    col = (220, 248, 255, 255)
                    lw = 2
                elif z_avg > 20:
                    col = (103, 232, 249, 230)
                    lw = 1
                elif z_avg > 0:
                    col = (6, 182, 212, 190)
                    lw = 1
                elif z_avg > -12:
                    col = (8, 145, 178, 140)
                    lw = 1
                else:
                    col = (14, 116, 144, 90)
                    lw = 1

                draw.line([p1, p2], fill=col, width=lw)

                # Sparkling cyber nodes along the scanline
                if i % 3 == 0 and z_avg > 2:
                    twinkle = math.sin(self.t * 4.2 + s * 0.7 + i)
                    if twinkle > 0.40:
                        dot_col = (255, 255, 255, 255) if (z_avg > 30 and twinkle > 0.8) else (103, 232, 249, 220)
                        dot_sz = 1.2 if z_avg > 30 else 0.8
                        draw.ellipse([p1[0]-dot_sz, p1[1]-dot_sz, p1[0]+dot_sz, p1[1]+dot_sz], fill=dot_col)

        self.tk_face = ImageTk.PhotoImage(img)
        self.delete("all")
        self.create_image(0, 0, image=self.tk_face, anchor="nw")

    def _render_3d_connectivity(self):
        """Renders 3D Working Connectivity Mesh with traveling data packets & gyroscopic rings."""
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


'''

updated_gui = gui_code[:v_start] + new_visualizer_canvas + gui_code[v_end:]
with open(gui_path, "w", encoding="utf-8") as f:
    f.write(updated_gui)
print("Updated gui.py with True 3D Humanoid Head Mesh Visualizer!")

