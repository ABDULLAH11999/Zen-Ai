import tkinter as tk
import math
import time

class Test3DVisualizer(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(bg="#070a14", highlightthickness=0)
        self.bind("<Configure>", self._on_resize)
        self.cx = 300
        self.cy = 220
        self.t = 0.0
        self.state = "IDLE" # IDLE, LISTENING, THINKING, SPEAKING
        self._is_running = True
        self._init_models()
        self._animate()

    def _on_resize(self, event):
        self.cx = event.width // 2
        self.cy = event.height // 2

    def _init_models(self):
        # 1. 3D Face Model Vertices (x, y, z)
        # Normalized coordinates scaled to ~80-100 units
        self.face_vertices = {
            # Cranium / Forehead top
            "f_top": (0, -95, 20),
            "f_l1": (-40, -85, 0),
            "f_r1": (40, -85, 0),
            "f_l2": (-65, -60, -20),
            "f_r2": (65, -60, -20),
            # Brows
            "b_mid": (0, -35, 45),
            "b_l": (-35, -38, 38),
            "b_r": (35, -38, 38),
            "b_l_out": (-60, -32, 10),
            "b_r_out": (60, -32, 10),
            # Eyes (Left & Right)
            "e_l_in": (-15, -20, 38),
            "e_l_out": (-45, -20, 28),
            "e_l_top": (-30, -28, 35),
            "e_l_bot": (-30, -12, 35),
            "e_r_in": (15, -20, 38),
            "e_r_out": (45, -20, 28),
            "e_r_top": (30, -28, 35),
            "e_r_bot": (30, -12, 35),
            # Nose
            "n_bridge": (0, -15, 48),
            "n_tip": (0, 15, 60),
            "n_l": (-14, 18, 45),
            "n_r": (14, 18, 45),
            # Cheeks / Temples
            "c_l": (-65, 0, 0),
            "c_r": (65, 0, 0),
            "c_l_in": (-35, 15, 30),
            "c_r_in": (35, 15, 30),
            # Upper Lip
            "lip_top": (0, 38, 48),
            "lip_l": (-22, 42, 38),
            "lip_r": (22, 42, 38),
            # Lower Lip (Dynamic for talking)
            "lip_bot": (0, 48, 46),
            # Jaw & Chin (Dynamic for talking)
            "jaw_l": (-55, 45, -10),
            "jaw_r": (55, 45, -10),
            "chin_l": (-20, 85, 30),
            "chin_r": (20, 85, 30),
            "chin_tip": (0, 92, 38)
        }

        self.face_edges = [
            # Cranium
            ("f_l2", "f_l1"), ("f_l1", "f_top"), ("f_top", "f_r1"), ("f_r1", "f_r2"),
            ("f_l2", "b_l_out"), ("f_r2", "b_r_out"),
            # Forehead to Brows
            ("f_top", "b_mid"), ("f_l1", "b_l"), ("f_r1", "b_r"),
            ("b_l_out", "b_l"), ("b_l", "b_mid"), ("b_mid", "b_r"), ("b_r", "b_r_out"),
            # Left Eye
            ("e_l_in", "e_l_top"), ("e_l_top", "e_l_out"), ("e_l_out", "e_l_bot"), ("e_l_bot", "e_l_in"),
            # Right Eye
            ("e_r_in", "e_r_top"), ("e_r_top", "e_r_out"), ("e_r_out", "e_r_bot"), ("e_r_bot", "e_r_in"),
            # Nose
            ("b_mid", "n_bridge"), ("n_bridge", "n_tip"),
            ("n_tip", "n_l"), ("n_tip", "n_r"), ("n_l", "n_bridge"), ("n_r", "n_bridge"),
            # Cheekbones
            ("b_l_out", "c_l"), ("b_r_out", "c_r"),
            ("c_l", "c_l_in"), ("c_r", "c_r_in"),
            ("c_l_in", "n_l"), ("c_r_in", "n_r"),
            # Mouth
            ("lip_l", "lip_top"), ("lip_top", "lip_r"),
            ("lip_l", "lip_bot"), ("lip_bot", "lip_r"),
            ("n_tip", "lip_top"),
            # Jawline
            ("c_l", "jaw_l"), ("c_r", "jaw_r"),
            ("jaw_l", "chin_l"), ("jaw_r", "chin_r"),
            ("chin_l", "chin_tip"), ("chin_r", "chin_tip"),
            ("lip_bot", "chin_tip"),
            ("lip_l", "c_l_in"), ("lip_r", "c_r_in")
        ]

        # 2. 3D Connectivity Network Model (12 Nodes in a 3D Cluster)
        phi = (1 + math.sqrt(5)) / 2 # golden ratio
        raw_nodes = [
            (-1, phi, 0), (1, phi, 0), (-1, -phi, 0), (1, -phi, 0),
            (0, -1, phi), (0, 1, phi), (0, -1, -phi), (0, 1, -phi),
            (phi, 0, -1), (phi, 0, 1), (-phi, 0, -1), (-phi, 0, 1)
        ]
        self.connect_nodes = []
        for x, y, z in raw_nodes:
            scale = 48.0
            self.connect_nodes.append((x * scale, y * scale, z * scale))
            
        self.connect_edges = []
        n_count = len(self.connect_nodes)
        for i in range(n_count):
            for j in range(i + 1, n_count):
                p1 = self.connect_nodes[i]
                p2 = self.connect_nodes[j]
                dist = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2 + (p1[2]-p2[2])**2)
                if dist < 115: # Connect nearest neighbors
                    self.connect_edges.append((i, j))

    def _project_3d(self, x, y, z, yaw, pitch, roll=0.0):
        # 3D rotation around Y (yaw)
        cos_y, sin_y = math.cos(yaw), math.sin(yaw)
        x1 = x * cos_y + z * sin_y
        z1 = -x * sin_y + z * cos_y
        # 3D rotation around X (pitch)
        cos_x, sin_x = math.cos(pitch), math.sin(pitch)
        y2 = y * cos_x - z1 * sin_x
        z2 = y * sin_x + z1 * cos_x
        
        # Perspective projection
        fov = 380.0
        camera_dist = 340.0
        factor = fov / (z2 + camera_dist)
        px = self.cx + x1 * factor
        py = self.cy + y2 * factor
        return px, py, z2

    def _animate(self):
        if not self._is_running:
            return
        self.delete("all")
        self.t += 0.05
        
        # Draw background HUD grid
        w = self.winfo_width() or 600
        h = self.winfo_height() or 400
        for gx in range(0, w, 50):
            self.create_line(gx, 0, gx, h, fill="#0b1324", width=1)
        for gy in range(0, h, 50):
            self.create_line(0, gy, w, gy, fill="#0b1324", width=1)

        is_processing = (self.state in ["THINKING", "PROCESSING"])
        
        if is_processing:
            self._render_3d_connectivity()
        else:
            self._render_3d_face()
            
        self.after(30, self._animate)

    def _render_3d_face(self):
        # Subtle 3D breathing yaw & pitch
        yaw = math.sin(self.t * 0.8) * 0.22
        pitch = math.cos(self.t * 0.6) * 0.12
        
        # Talking mouth articulation
        is_speaking = (self.state == "SPEAKING")
        is_listening = (self.state == "LISTENING")
        
        mouth_open = 0.0
        if is_speaking:
            # Complex multi-frequency speech articulation
            mouth_open = (math.sin(self.t * 14) * 0.5 + 0.5) * 16.0 + (math.sin(self.t * 22) * 0.3) * 8.0
        elif is_listening:
            mouth_open = 2.0
            
        # Color palette
        if is_speaking:
            primary_col = "#00f0ff"
            glow_col = "#38bdf8"
            eye_col = "#00ffcc"
            status_text = "3D NEURAL SPEECH SYNTHESIZER // TRANSMITTING..."
        elif is_listening:
            primary_col = "#fbbf24"
            glow_col = "#f59e0b"
            eye_col = "#fef08a"
            status_text = "3D SENSORY RECEPTOR ACTIVE // LISTENING..."
        elif self.state == "DICTATING":
            primary_col = "#ff0055"
            glow_col = "#00f0ff"
            eye_col = "#ff3366"
            status_text = "LIVE DICTATION // SPEAK NOW..."
        else:
            primary_col = "#00f0ff"
            glow_col = "#0284c7"
            eye_col = "#38bdf8"
            status_text = "3D CYBERNETIC AVATAR ONLINE // AWAITING COMMAND"

        # Project 3D Face vertices
        proj_pts = {}
        for name, (x, y, z) in self.face_vertices.items():
            adj_y = y
            # Displace jaw and lower lip when mouth opens
            if name in ["lip_bot"]:
                adj_y += mouth_open * 0.7
            elif name in ["chin_l", "chin_r", "chin_tip"]:
                adj_y += mouth_open * 0.9
            elif name in ["jaw_l", "jaw_r"]:
                adj_y += mouth_open * 0.4
                
            px, py, pz = self._project_3d(x, adj_y, z, yaw, pitch)
            proj_pts[name] = (px, py, pz)

        # Draw holographic outer orbital rings
        r_orb = 140 + math.sin(self.t * 2) * 5
        self.create_oval(self.cx - r_orb, self.cy - r_orb, self.cx + r_orb, self.cy + r_orb,
                         outline="#132238", width=1)
        arc_ang = (self.t * 40) % 360
        self.create_arc(self.cx - r_orb - 5, self.cy - r_orb - 5, self.cx + r_orb + 5, self.cy + r_orb + 5,
                        start=arc_ang, extent=65, outline=primary_col, width=2, style="arc")
        self.create_arc(self.cx - r_orb - 5, self.cy - r_orb - 5, self.cx + r_orb + 5, self.cy + r_orb + 5,
                        start=arc_ang + 180, extent=40, outline=glow_col, width=1.5, style="arc")

        # Draw Face Edges with depth-based brightness
        for v1_name, v2_name in self.face_edges:
            p1 = proj_pts[v1_name]
            p2 = proj_pts[v2_name]
            avg_z = (p1[2] + p2[2]) / 2.0
            # Higher z is closer to viewer -> brighter/thicker line
            line_w = 2 if avg_z > 20 else 1
            col = primary_col if avg_z > -10 else glow_col
            self.create_line(p1[0], p1[1], p2[0], p2[1], fill=col, width=line_w)

        # Draw Eyes Pupils & Inner Glow
        el_p = proj_pts["e_l_top"]
        er_p = proj_pts["e_r_top"]
        eye_cx_l = (proj_pts["e_l_in"][0] + proj_pts["e_l_out"][0]) / 2
        eye_cy_l = (proj_pts["e_l_top"][1] + proj_pts["e_l_bot"][1]) / 2
        eye_cx_r = (proj_pts["e_r_in"][0] + proj_pts["e_r_out"][0]) / 2
        eye_cy_r = (proj_pts["e_r_top"][1] + proj_pts["e_r_bot"][1]) / 2
        
        eye_r = 4.5 + math.sin(self.t * 3) * 1
        self.create_oval(eye_cx_l - eye_r, eye_cy_l - eye_r, eye_cx_l + eye_r, eye_cy_l + eye_r,
                         fill=eye_col, outline="#ffffff", width=1)
        self.create_oval(eye_cx_r - eye_r, eye_cy_r - eye_r, eye_cx_r + eye_r, eye_cy_r + eye_r,
                         fill=eye_col, outline="#ffffff", width=1)

        # Digital readout
        self.create_text(self.cx, self.cy + 155, text=status_text, fill=primary_col,
                         font=("Consolas", 10, "bold"))

    def _render_3d_connectivity(self):
        """Renders 3D Working Connectivity Mesh with traveling data packets & gyroscopic rings."""
        yaw = self.t * 0.9
        pitch = self.t * 0.65
        
        # 1. Project 3D Nodes
        proj_nodes = []
        for nx, ny, nz in self.connect_nodes:
            px, py, pz = self._project_3d(nx, ny, nz, yaw, pitch)
            proj_nodes.append((px, py, pz))

        # 2. Draw Gyroscopic 3D Orbital Rings (Reactor working mode)
        r_outer = 135
        # Ring 1
        ring_pts1 = []
        for i in range(24):
            th = i * 2 * math.pi / 24
            rx = r_outer * math.cos(th)
            ry = r_outer * math.sin(th) * 0.3
            px, py, pz = self._project_3d(rx, ry, 0, yaw * 1.5, pitch)
            ring_pts1.append((px, py))
        for i in range(len(ring_pts1)):
            p1 = ring_pts1[i]
            p2 = ring_pts1[(i + 1) % len(ring_pts1)]
            self.create_line(p1[0], p1[1], p2[0], p2[1], fill="#c084fc", width=1.5)

        # Ring 2 (Cross orbit)
        ring_pts2 = []
        for i in range(24):
            th = i * 2 * math.pi / 24
            rx = r_outer * math.cos(th) * 0.35
            ry = r_outer * math.sin(th)
            px, py, pz = self._project_3d(rx, ry, 0, -yaw * 1.2, pitch * 1.4)
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

        # 4. Draw Traveling Data Packets (Active connectivity working pulses)
        packet_count = 14
        for p in range(packet_count):
            edge_idx = (p * 3) % len(self.connect_edges)
            i1, i2 = self.connect_edges[edge_idx]
            p1 = proj_nodes[i1]
            p2 = proj_nodes[i2]
            
            # Progress parameter 0.0 to 1.0 traveling along edge
            prog = (self.t * 2.2 + p * 0.4) % 1.0
            pak_x = p1[0] + (p2[0] - p1[0]) * prog
            pak_y = p1[1] + (p2[1] - p1[1]) * prog
            
            # Draw glowing packet pulse
            self.create_oval(pak_x - 3, pak_y - 3, pak_x + 3, pak_y + 3,
                             fill="#00f0ff", outline="#ffffff", width=1)

        # 5. Draw 3D Nodes (Spheres with depth scaling)
        # Sort nodes back to front for proper rendering
        sorted_indices = sorted(range(len(proj_nodes)), key=lambda idx: proj_nodes[idx][2])
        for idx in sorted_indices:
            px, py, pz = proj_nodes[idx]
            node_r = max(3.0, 6.0 + pz * 0.04)
            col_fill = "#c084fc" if pz > 0 else "#6b21a8"
            self.create_oval(px - node_r, py - node_r, px + node_r, py + node_r,
                             fill=col_fill, outline="#00f0ff" if pz > 15 else "#818cf8", width=1.5)

        # Central Power Core
        core_r = 16 + math.sin(self.t * 5) * 3
        self.create_oval(self.cx - core_r, self.cy - core_r, self.cx + core_r, self.cy + core_r,
                         fill="#0d1b2a", outline="#00f0ff", width=2)
        self.create_text(self.cx, self.cy, text="⚡", fill="#00f0ff", font=("Segoe UI Symbol", 12, "bold"))

        # Working status digital readout
        status_text = "NEURAL CONNECTIVITY ACTIVE // SYNAPSES PROCESSING // WORKING..."
        self.create_text(self.cx, self.cy + 155, text=status_text, fill="#c084fc",
                         font=("Consolas", 10, "bold"))

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("600x480")
    vis = Test3DVisualizer(root)
    vis.pack(fill="both", expand=True)
    
    # State switcher test: Idle -> Speaking -> Thinking (connectivity) -> Idle
    states = ["IDLE", "SPEAKING", "THINKING", "LISTENING"]
    def switch_state(i=0):
        s = states[i % len(states)]
        print("Switching state to:", s)
        vis.state = s
        root.after(3000, lambda: switch_state(i + 1))
    root.after(2000, switch_state)
    root.after(10000, lambda: root.destroy())
    root.mainloop()

