import os
import re

# ==========================================
# 1. Update gui.py
# ==========================================
gui_path = r"F:\Ai Tools\Zen Agent\Zen Ai\gui.py"
with open(gui_path, "r", encoding="utf-8") as f:
    gui_code = f.read()

# Locate VisualizerCanvas class
start_marker = "class VisualizerCanvas(tk.Canvas):"
end_marker = "class JarvisGUI(ctk.CTk):"

v_start = gui_code.find(start_marker)
v_end = gui_code.find(end_marker)

assert v_start != -1, "VisualizerCanvas not found in gui.py"
assert v_end != -1, "JarvisGUI not found in gui.py"

new_visualizer_canvas = '''class VisualizerCanvas(tk.Canvas):
    """
    Dual-Mode 3D Futuristic AI Hologram Visualizer:
    1. Normal & Talk Mode: Photorealistic 3D Holographic Head (Image 1 asset),
       with dynamic multi-axis organic gaze (smooth random left-to-right & up-to-down looking angles),
       subtle 3D perspective foreshortening, natural jaw speech articulation, and ambient cyber dust.
       (All outer circles, arcs, and scanner lines completely removed per Sir Abdullah's instructions).
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

        self.next_gaze_time = time.time() + 1.2

    def _update_gaze(self):
        import time, random
        now = time.time()
        is_speaking = ("SPEAK" in self.current_state)

        if is_speaking:
            # Facing more front towards the user with speech emphasis
            self.target_yaw = math.sin(self.t * 3.5) * 0.07
            self.target_pitch = math.sin(self.t * 5.0) * 0.05
            self.target_roll = math.sin(self.t * 2.8) * 0.03
            self.target_dx = math.sin(self.t * 2.0) * 5.0
            self.target_dy = math.sin(self.t * 3.0) * 3.5
            self.next_gaze_time = now + 1.5
        elif now >= self.next_gaze_time:
            # Idle / Standby: Organic random glancing
            if random.random() < 0.35:
                # Glance towards center
                self.target_yaw = random.uniform(-0.05, 0.05)
                self.target_pitch = random.uniform(-0.04, 0.04)
                self.target_roll = random.uniform(-0.02, 0.02)
                self.target_dx = random.uniform(-4, 4)
                self.target_dy = random.uniform(-4, 4)
                dwell = random.uniform(2.0, 3.5)
            else:
                # Random glance left or right (yaw -18 deg to +18 deg)
                self.target_yaw = random.choice([-1, 1]) * random.uniform(0.12, 0.28)
                # Random pitch up or down (-12 deg to +12 deg)
                self.target_pitch = random.uniform(-0.18, 0.18)
                # Sympathetic head roll
                self.target_roll = -self.target_yaw * random.uniform(0.15, 0.28)
                # Translation in glance direction
                self.target_dx = self.target_yaw * 42.0
                self.target_dy = self.target_pitch * 28.0
                dwell = random.uniform(2.2, 4.5)
            self.next_gaze_time = now + dwell

        # Smooth ease-out lerp
        lerp = 0.05
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
        """Renders Photorealistic 3D Blended Holographic Head with organic multi-axis gaze."""
        self._update_gaze()

        # Micro-breathing oscillation
        breathe = math.sin(self.t * 1.5)
        y_breathe = breathe * 4.5
        scale = 0.90 + 0.012 * breathe

        is_speaking = ("SPEAK" in self.current_state)

        # Dynamic speech articulation (jaw displacement)
        if is_speaking:
            mouth_val = int(min(15, max(0, (math.sin(self.t * 16) * 0.5 + 0.5) * 11.0 + (math.sin(self.t * 26) * 0.3) * 4.0)))
        else:
            mouth_val = 0

        # Ambient Glittering Cyber Dust (matching Image 1 particles)
        for p in self.ambient_particles:
            px = self.center_x + p["x"] + math.sin(self.t * p["speed"] + p["phase"]) * 14
            py = self.center_y + p["y"] + math.cos(self.t * p["speed"] * 0.8) * 12
            alpha = (math.sin(self.t * 3.0 + p["phase"]) + 1.0) / 2.0
            if alpha > 0.4:
                col = "#e0f7fa" if alpha > 0.75 else "#38bdf8"
                sz = 1.5 if alpha > 0.75 else 1.0
                self.create_oval(px - sz, py - sz, px + sz, py + sz, fill=col, outline="")

        # Compute 3D Perspective Face with Gaze Warp (No circles, No scanlines)
        live_cx = self.center_x + self.current_dx
        live_cy = self.center_y + self.current_dy + y_breathe

        if self.mouth_frames and mouth_val in self.mouth_frames:
            face_img = self.mouth_frames[mouth_val]
        else:
            face_img = self.raw_face_img

        if face_img is not None:
            # 3D perspective warp
            dx = math.sin(self.current_yaw) * 18.0
            dy = math.sin(self.current_pitch) * 15.0

            dst = np.array([
                [-dx * 0.75, dy * 0.8],
                [self.face_w - dx * 0.75, -dy * 0.8],
                [self.face_w + dx * 0.75, self.face_h - dy * 0.8],
                [dx * 0.75, self.face_h + dy * 0.8]
            ])
            src = np.array([[0, 0], [self.face_w, 0], [self.face_w, self.face_h], [0, self.face_h]], dtype=float)

            matrix = []
            for p1, p2 in zip(dst, src):
                matrix.append([p1[0], p1[1], 1, 0, 0, 0, -p2[0]*p1[0], -p2[0]*p1[1]])
                matrix.append([0, 0, 0, p1[0], p1[1], 1, -p2[1]*p1[0], -p2[1]*p1[1]])
            coeffs = np.linalg.solve(matrix, src.reshape(8))

            target_w = int(self.face_w * scale)
            target_h = int(self.face_h * scale)
            warped = face_img.transform((self.face_w, self.face_h), Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BILINEAR)
            scaled = warped.resize((target_w, target_h), Image.Resampling.BILINEAR)

            roll_deg = math.degrees(self.current_roll)
            if abs(roll_deg) > 0.2:
                scaled = scaled.rotate(roll_deg, resample=Image.Resampling.BICUBIC, expand=False)

            self.tk_face = ImageTk.PhotoImage(scaled)
            self.create_image(live_cx, live_cy, image=self.tk_face, anchor="center")

    def _render_3d_connectivity(self):
        """Renders 3D Working Connectivity Mesh with traveling data packets & gyroscopic rings."""
        yaw = self.t * 0.95
        pitch = self.t * 0.70

        # 1. Project 3D Nodes
        proj_nodes = []
        for nx, ny, nz in self.connect_nodes:
            px, py, pz = self._project_3d(nx, ny, nz, yaw, pitch)
            proj_nodes.append((px, py, pz))

        # 2. Draw Gyroscopic 3D Orbital Rings (Active Processing Core)
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

        # 4. Draw Traveling Data Packets (Active connectivity pulses)
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

        # 5. Draw 3D Nodes (Spheres with depth scaling)
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
print("Updated gui.py successfully with organic 3D gaze (no circles, no scanline)!")


# ==========================================
# 2. Update zen_web_portal.py
# ==========================================
portal_path = r"F:\Ai Tools\Zen Agent\Zen Ai\zen_web_portal.py"
with open(portal_path, "r", encoding="utf-8") as f:
    portal_code = f.read()

# Locate visualizer in JavaScript
p_start_marker = "// Real 3D Blended Hologram Face & Connectivity Engine"
p_end_marker = "function setAgentState(state) {"

p_start = portal_code.find(p_start_marker)
p_end = portal_code.find(p_end_marker)

assert p_start != -1, "portal visualizer marker not found"
assert p_end != -1, "portal setAgentState marker not found"

new_portal_visualizer = '''// Real 3D Blended Hologram Face & Connectivity Engine
    const faceImg = new Image();
    faceImg.src = "/static/hologram_face.png";
    let faceLoaded = false;
    faceImg.onload = () => { faceLoaded = true; };

    // Organic Gaze & Angle Tracking
    let currentYaw = 0.0, currentPitch = 0.0, currentRoll = 0.0, currentDx = 0.0, currentDy = 0.0;
    let targetYaw = 0.0, targetPitch = 0.0, targetRoll = 0.0, targetDx = 0.0, targetDy = 0.0;
    let nextGazeTime = Date.now() + 1000;

    const ambientParticles = [];
    for (let i = 0; i < 35; i++) {
        ambientParticles.push({
            x: (Math.random() - 0.5) * 160,
            y: (Math.random() - 0.5) * 170,
            speed: 0.3 + Math.random() * 0.6,
            phase: Math.random() * Math.PI * 2
        });
    }

    const phi = (1 + Math.sqrt(5)) / 2;
    const rawNodes = [
        [-1, phi, 0], [1, phi, 0], [-1, -phi, 0], [1, -phi, 0],
        [0, -1, phi], [0, 1, phi], [0, -1, -phi], [0, 1, -phi],
        [phi, 0, -1], [phi, 0, 1], [-phi, 0, -1], [-phi, 0, 1]
    ];
    const connectNodes = rawNodes.map(([x, y, z]) => [x * 46, y * 46, z * 46]);
    const connectEdges = [];
    for (let i = 0; i < connectNodes.length; i++) {
        for (let j = i + 1; j < connectNodes.length; j++) {
            const [x1, y1, z1] = connectNodes[i];
            const [x2, y2, z2] = connectNodes[j];
            const d = Math.sqrt((x1-x2)**2 + (y1-y2)**2 + (z1-z2)**2);
            if (d < 110) connectEdges.push([i, j]);
        }
    }

    function project3D(x, y, z, yaw, pitch, cx, cy) {
        const cosY = Math.cos(yaw), sinY = Math.sin(yaw);
        const x1 = x * cosY + z * sinY;
        const z1 = -x * sinY + z * cosY;
        const cosX = Math.cos(pitch), sinX = Math.sin(pitch);
        const y2 = y * cosX - z1 * sinX;
        const z2 = y * sinX + z1 * cosX;
        const fov = 380, dist = 320;
        const factor = fov / (z2 + dist);
        return [cx + x1 * factor, cy + y2 * factor, z2];
    }

    let t3d = 0.0;

    function renderVisualizer() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const cx = canvas.width / 2;
        const cy = canvas.height / 2;
        t3d += 0.05;

        const isProcessing = (currentAgentState === "THINKING" || currentAgentState === "PROCESSING" || currentAgentState === "EXECUTING");

        if (isProcessing) {
            // Render 3D Connectivity Working Cluster
            const yaw = t3d * 0.95, pitch = t3d * 0.70;
            const proj = connectNodes.map(([x, y, z]) => project3D(x, y, z, yaw, pitch, cx, cy));

            // Gyroscopic Rings
            ctx.strokeStyle = "#c084fc";
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            for (let i = 0; i <= 24; i++) {
                const th = i * Math.PI * 2 / 24;
                const [px, py] = project3D(120 * Math.cos(th), 120 * Math.sin(th) * 0.35, 0, yaw * 1.5, pitch, cx, cy);
                if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
            }
            ctx.stroke();

            ctx.strokeStyle = "#38bdf8";
            ctx.beginPath();
            for (let i = 0; i <= 24; i++) {
                const th = i * Math.PI * 2 / 24;
                const [px, py] = project3D(120 * Math.cos(th) * 0.35, 120 * Math.sin(th), 0, -yaw * 1.3, pitch * 1.4, cx, cy);
                if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
            }
            ctx.stroke();

            // Connections
            for (const [i1, i2] of connectEdges) {
                const [x1, y1, z1] = proj[i1];
                const [x2, y2, z2] = proj[i2];
                ctx.strokeStyle = (z1 + z2 > 0) ? "#a855f7" : "#4c1d95";
                ctx.lineWidth = (z1 + z2 > 10) ? 2 : 1;
                ctx.beginPath();
                ctx.moveTo(x1, y1);
                ctx.lineTo(x2, y2);
                ctx.stroke();
            }

            // Data Packets traveling
            for (let p = 0; p < 12; p++) {
                const [i1, i2] = connectEdges[(p * 3) % connectEdges.length];
                const [x1, y1] = proj[i1];
                const [x2, y2] = proj[i2];
                const prog = (t3d * 2.5 + p * 0.4) % 1.0;
                const pakX = x1 + (x2 - x1) * prog;
                const pakY = y1 + (y2 - y1) * prog;
                ctx.fillStyle = "#00f0ff";
                ctx.beginPath();
                ctx.arc(pakX, pakY, 3, 0, Math.PI * 2);
                ctx.fill();
            }

            // Nodes
            const sortedNodes = proj.map((p, i) => ({ p, i })).sort((a, b) => a.p[2] - b.p[2]);
            for (const item of sortedNodes) {
                const [px, py, pz] = item.p;
                const r = Math.max(3, 5.5 + pz * 0.035);
                ctx.fillStyle = pz > 0 ? "#c084fc" : "#6b21a8";
                ctx.strokeStyle = pz > 10 ? "#00f0ff" : "#818cf8";
                ctx.lineWidth = 1.2;
                ctx.beginPath();
                ctx.arc(px, py, r, 0, Math.PI * 2);
                ctx.fill();
                ctx.stroke();
            }

            // Power core
            ctx.fillStyle = "#0d1b2a";
            ctx.strokeStyle = "#00f0ff";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.arc(cx, cy, 14, 0, Math.PI * 2);
            ctx.fill();
            ctx.stroke();
            ctx.fillStyle = "#00f0ff";
            ctx.font = "bold 11px monospace";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText("⚡", cx, cy);

        } else {
            // Render Real Photorealistic 3D Blended Hologram Face with organic multi-axis gaze
            const now = Date.now();
            const isSpeaking = (currentAgentState === "SPEAKING");

            if (isSpeaking) {
                targetYaw = Math.sin(t3d * 3.5) * 0.07;
                targetPitch = Math.sin(t3d * 5.0) * 0.05;
                targetRoll = Math.sin(t3d * 2.8) * 0.03;
                targetDx = Math.sin(t3d * 2.0) * 5.0;
                targetDy = Math.sin(t3d * 3.0) * 3.5;
                nextGazeTime = now + 1500;
            } else if (now >= nextGazeTime) {
                if (Math.random() < 0.35) {
                    targetYaw = (Math.random() - 0.5) * 0.1;
                    targetPitch = (Math.random() - 0.5) * 0.08;
                    targetRoll = (Math.random() - 0.5) * 0.04;
                    targetDx = (Math.random() - 0.5) * 8;
                    targetDy = (Math.random() - 0.5) * 8;
                    nextGazeTime = now + 2000 + Math.random() * 1500;
                } else {
                    targetYaw = (Math.random() > 0.5 ? 1 : -1) * (0.12 + Math.random() * 0.16);
                    targetPitch = (Math.random() - 0.5) * 0.36;
                    targetRoll = -targetYaw * (0.15 + Math.random() * 0.15);
                    targetDx = targetYaw * 40.0;
                    targetDy = targetPitch * 25.0;
                    nextGazeTime = now + 2200 + Math.random() * 2200;
                }
            }

            const lerp = 0.05;
            currentYaw += (targetYaw - currentYaw) * lerp;
            currentPitch += (targetPitch - currentPitch) * lerp;
            currentRoll += (targetRoll - currentRoll) * lerp;
            currentDx += (targetDx - currentDx) * lerp;
            currentDy += (targetDy - currentDy) * lerp;

            const breathe = Math.sin(t3d * 1.5);
            const yBreathe = breathe * 3.5;
            const scale = 0.90 + 0.012 * breathe;

            // Ambient Cyber Glitter Particles (Image 1 dust)
            for (const p of ambientParticles) {
                const pyLive = p.y + Math.sin(t3d * p.speed + p.phase) * 8;
                const alpha = (Math.sin(t3d * 3.0 + p.phase) + 1.0) / 2.0;
                if (alpha > 0.4) {
                    ctx.fillStyle = alpha > 0.75 ? "#e0f7fa" : "#38bdf8";
                    ctx.beginPath();
                    ctx.arc(cx + p.x, cy + pyLive, alpha > 0.75 ? 1.5 : 1.0, 0, Math.PI * 2);
                    ctx.fill();
                }
            }

            // Draw Real Blended Hologram Face with 3D perspective angle
            if (faceLoaded && faceImg.width > 0) {
                ctx.save();
                ctx.translate(cx + currentDx, cy + currentDy + yBreathe);
                ctx.rotate(currentRoll);
                const cosYaw = Math.cos(currentYaw);
                const skewX = Math.sin(currentYaw) * 0.12;
                ctx.transform(cosYaw, 0, skewX, 1, 0, 0);

                const drawH = 175 * scale;
                const drawW = (faceImg.width / faceImg.height) * drawH;
                ctx.drawImage(faceImg, -drawW / 2, -drawH / 2, drawW, drawH);
                ctx.restore();
            }
        }

        requestAnimationFrame(renderVisualizer);
    }
    requestAnimationFrame(renderVisualizer);

    '''

updated_portal = portal_code[:p_start] + new_portal_visualizer + portal_code[p_end:]
with open(portal_path, "w", encoding="utf-8") as f:
    f.write(updated_portal)
print("Updated zen_web_portal.py successfully with organic 3D gaze (no circles, no scanline)!")

