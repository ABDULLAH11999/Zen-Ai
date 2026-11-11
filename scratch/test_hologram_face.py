import tkinter as tk
import math
import random

class HologramHeadVisualizer(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(bg="#070a14", highlightthickness=0)
        self.bind("<Configure>", self._on_resize)
        self.cx = 300
        self.cy = 220
        self.t = 0.0
        self.state = "IDLE"
        self._is_animating = True
        self._init_head_slices()
        self._animate()

    def _on_resize(self, event):
        self.cx = event.width // 2
        self.cy = event.height // 2

    def _init_head_slices(self):
        # Generate 55 horizontal slices along Y axis from -110 (cranium) to +115 (neck)
        self.slices = []
        num_slices = 58
        y_min, y_max = -105.0, 115.0
        
        # Pre-generate floating ambient particles (like Image 1 sparkling cyber dust)
        self.ambient_particles = []
        for _ in range(35):
            self.ambient_particles.append({
                "x": random.uniform(-80, 80),
                "y": random.uniform(-110, 120),
                "z": random.uniform(-40, 60),
                "speed": random.uniform(0.2, 0.8),
                "phase": random.uniform(0, math.pi * 2)
            })

        for i in range(num_slices):
            t_slice = i / (num_slices - 1)
            y = y_min + t_slice * (y_max - y_min)
            
            # Anatomical width and depths based on human head profile
            if y < -60: # Cranium dome
                t_c = (y - (-105)) / 45.0
                rad_x = 55 * math.sin(t_c * math.pi * 0.5)
                rad_z = 62 * math.sin(t_c * math.pi * 0.5)
                z_center = -5
                feature = "cranium"
            elif y < -25: # Forehead
                rad_x = 56
                rad_z = 64
                z_center = 0
                feature = "forehead"
            elif y < -5: # Eye sockets & Brow
                rad_x = 54
                rad_z = 58
                z_center = 2
                feature = "eyes"
            elif y < 25: # Nose & Cheekbones
                rad_x = 50 - (y - (-5)) * 0.2
                rad_z = 55
                z_center = 8 # Protrusion
                feature = "nose"
            elif y < 55: # Mouth & Upper Jaw
                rad_x = 42 - (y - 25) * 0.2
                rad_z = 48
                z_center = 10
                feature = "mouth"
            elif y < 85: # Chin & Lower Jaw
                t_j = (y - 55) / 30.0
                rad_x = 36 * (1.0 - t_j * 0.45)
                rad_z = 42 * (1.0 - t_j * 0.35)
                z_center = 8 * (1.0 - t_j)
                feature = "jaw"
            else: # Neck & Upper Trapezius
                t_n = (y - 85) / 30.0
                rad_x = 22 + t_n * 26
                rad_z = 24 + t_n * 16
                z_center = -10
                feature = "neck"

            self.slices.append({
                "base_y": y,
                "rad_x": max(1.0, rad_x),
                "rad_z": max(1.0, rad_z),
                "z_center": z_center,
                "feature": feature
            })

    def _project_3d(self, x, y, z, yaw, pitch):
        cos_y, sin_y = math.cos(yaw), math.sin(yaw)
        x1 = x * cos_y + z * sin_y
        z1 = -x * sin_y + z * cos_y
        cos_x, sin_x = math.cos(pitch), math.sin(pitch)
        y2 = y * cos_x - z1 * sin_x
        z2 = y * sin_x + z1 * cos_x
        
        fov = 420.0
        dist = 360.0
        factor = fov / (z2 + dist)
        px = self.cx + x1 * factor
        py = self.cy + y2 * factor
        return px, py, z2

    def _animate(self):
        if not self._is_animating:
            return
        self.delete("all")
        self.t += 0.05
        
        self._render_hologram_face()
        self.after(30, self._animate)

    def _render_hologram_face(self):
        # 3D rotational breathing
        yaw = math.sin(self.t * 0.6) * 0.20
        pitch = math.cos(self.t * 0.45) * 0.10
        
        is_speaking = (self.state == "SPEAKING")
        mouth_open = 0.0
        if is_speaking:
            mouth_open = (math.sin(self.t * 14) * 0.5 + 0.5) * 12.0 + (math.sin(self.t * 22) * 0.3) * 5.0

        # Scan-line vertical luminescence wave
        scan_wave_y = math.sin(self.t * 2.5) * 80.0

        # Draw ambient glittering cyber particles around the head
        for p in self.ambient_particles:
            py_live = p["y"] + math.sin(self.t * p["speed"] + p["phase"]) * 10
            px, py, pz = self._project_3d(p["x"], py_live, p["z"], yaw, pitch)
            # Twinkle brightness
            alpha = (math.sin(self.t * 3.0 + p["phase"]) + 1.0) / 2.0
            if alpha > 0.4:
                col = "#e0f7fa" if alpha > 0.75 else "#38bdf8"
                sz = 1.5 if alpha > 0.75 else 1.0
                self.create_oval(px - sz, py - sz, px + sz, py + sz, fill=col, outline="")

        # Render dense horizontal scan-line slices
        for s_idx, s in enumerate(self.slices):
            y_base = s["base_y"]
            
            # Articulate mouth & jaw on speaking
            if s["feature"] in ["mouth", "jaw"]:
                if s["feature"] == "mouth":
                    y_base += mouth_open * 0.5
                else:
                    y_base += mouth_open * 0.85
                    
            rad_x = s["rad_x"]
            rad_z = s["rad_z"]
            zc = s["z_center"]
            
            # Segment the horizontal ellipse into points (front facing semi-ellipse)
            pts = []
            num_pts = 22 # Density per scanline
            for p_i in range(num_pts):
                th = -math.pi * 0.5 + (p_i / (num_pts - 1)) * math.pi
                
                # Base ellipse
                px = rad_x * math.sin(th)
                pz = zc + rad_z * math.cos(th)
                
                # Morph facial details:
                # 1. Nose protrusion
                if s["feature"] == "nose" and abs(th) < 0.35:
                    pz += 16.0 * math.cos(th / 0.35 * (math.pi / 2))
                # 2. Eye cavity indentation
                elif s["feature"] == "eyes":
                    if 0.25 < abs(th) < 0.75:
                        pz -= 10.0 * math.sin((abs(th) - 0.25) / 0.5 * math.pi)
                # 3. Lips prominence
                elif s["feature"] == "mouth" and abs(th) < 0.4:
                    pz += 8.0 * math.cos(th / 0.4 * (math.pi / 2))
                # 4. Chin prominence
                elif s["feature"] == "jaw" and abs(th) < 0.4:
                    pz += 7.0 * math.cos(th / 0.4 * (math.pi / 2))

                proj_x, proj_y, proj_z = self._project_3d(px, y_base, pz, yaw, pitch)
                pts.append((proj_x, proj_y, proj_z))

            # Luminescence ripple based on vertical scan-line wave
            dist_to_wave = abs(y_base - scan_wave_y)
            is_wave_highlight = dist_to_wave < 18.0

            # Draw the horizontal holographic slice segments
            for seg in range(len(pts) - 1):
                p1 = pts[seg]
                p2 = pts[seg + 1]
                avg_z = (p1[2] + p2[2]) / 2.0
                
                # Depth based color shading matching Image 1
                if is_wave_highlight and avg_z > 15:
                    col = "#e0f7fa" # Bright white-cyan laser highlight
                    width = 2.0
                elif avg_z > 30:
                    col = "#4eeffa" # High specular cyan
                    width = 1.6
                elif avg_z > 5:
                    col = "#1ba3c6" # Mid cyan-blue
                    width = 1.2
                elif avg_z > -20:
                    col = "#0f5a7a" # Darker depth cyan
                    width = 1.0
                else:
                    col = "#093148" # Deep shadow contour
                    width = 0.8

                self.create_line(p1[0], p1[1], p2[0], p2[1], fill=col, width=width)
                
                # Add glittering point-cloud dots on the scan lines (exact texture of Image 1!)
                if seg % 3 == 0 and avg_z > 10:
                    dot_sparkle = math.sin(self.t * 4.0 + s_idx * 0.7 + seg)
                    if dot_sparkle > 0.4:
                        dot_col = "#ffffff" if dot_sparkle > 0.85 else "#67e8f9"
                        self.create_oval(p1[0] - 1, p1[1] - 1, p1[0] + 1, p1[1] + 1, fill=dot_col, outline="")

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("600x480")
    vis = HologramHeadVisualizer(root)
    vis.pack(fill="both", expand=True)
    root.after(8000, lambda: root.destroy())
    root.mainloop()

