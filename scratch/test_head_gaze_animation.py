import math
import random
import time
import tkinter as tk
import numpy as np
from PIL import Image, ImageTk

class TestHeadGaze(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("640x520")
        self.title("Real 3D Organic Head Gaze Test (No Circles, No Scanline)")
        self.configure(bg="#070a14")

        self.canvas = tk.Canvas(self, bg="#070a14", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.raw_img = Image.open(r"F:\Ai Tools\Zen Agent\Zen Ai\models\hologram_face.png").convert("RGBA")
        self.w, self.h = self.raw_img.size

        # Ambient particles
        self.particles = []
        for _ in range(40):
            self.particles.append({
                "x": random.uniform(-140, 140),
                "y": random.uniform(-150, 150),
                "speed": random.uniform(0.4, 1.2),
                "phase": random.uniform(0, math.pi * 2)
            })

        self.t = 0.0

        # Organic Gaze & Angle Controller
        self.current_yaw = 0.0       # Left/Right angle (-1.0 to 1.0)
        self.current_pitch = 0.0     # Up/Down angle (-1.0 to 1.0)
        self.current_roll = 0.0      # Subtle head tilt (-1.0 to 1.0)
        self.current_dx = 0.0        # Horizontal pan drift
        self.current_dy = 0.0        # Vertical pan drift

        self.target_yaw = 0.0
        self.target_pitch = 0.0
        self.target_roll = 0.0
        self.target_dx = 0.0
        self.target_dy = 0.0

        self.next_gaze_time = time.time() + 1.0
        self.tk_face = None

        self.animate()

    def update_gaze_targets(self):
        now = time.time()
        if now >= self.next_gaze_time:
            # Pick a new organic looking angle
            # 30% chance to look back towards center
            if random.random() < 0.30:
                self.target_yaw = random.uniform(-0.06, 0.06)
                self.target_pitch = random.uniform(-0.05, 0.05)
                self.target_roll = random.uniform(-0.02, 0.02)
                self.target_dx = random.uniform(-6, 6)
                self.target_dy = random.uniform(-5, 5)
                dwell = random.uniform(1.8, 3.2)
            else:
                # Random glance: left/right or up/down
                # Random yaw in radians (-0.32 to +0.32 radians ~ -18 to +18 deg)
                self.target_yaw = random.choice([-1, 1]) * random.uniform(0.12, 0.32)
                # Random pitch in radians (-0.22 to +0.22 radians ~ -12 to +12 deg)
                self.target_pitch = random.uniform(-0.20, 0.22)
                # Subtle sympathetic roll
                self.target_roll = -self.target_yaw * random.uniform(0.15, 0.30)
                # Slight head translation in direction of gaze
                self.target_dx = self.target_yaw * 50.0
                self.target_dy = self.target_pitch * 35.0
                dwell = random.uniform(2.2, 4.0)

            self.next_gaze_time = now + dwell

    def get_perspective_face(self, yaw, pitch, roll, scale):
        """Generates 3D perspective foreshortening and angular warp."""
        target_w = int(self.w * scale)
        target_h = int(self.h * scale)

        # Displacements for corners
        dx = math.sin(yaw) * 18.0
        dy = math.sin(pitch) * 15.0

        dst = np.array([
            [-dx * 0.75, dy * 0.8],
            [self.w - dx * 0.75, -dy * 0.8],
            [self.w + dx * 0.75, self.h - dy * 0.8],
            [dx * 0.75, self.h + dy * 0.8]
        ])
        src = np.array([[0, 0], [self.w, 0], [self.w, self.h], [0, self.h]], dtype=float)

        matrix = []
        for p1, p2 in zip(dst, src):
            matrix.append([p1[0], p1[1], 1, 0, 0, 0, -p2[0]*p1[0], -p2[0]*p1[1]])
            matrix.append([0, 0, 0, p1[0], p1[1], 1, -p2[1]*p1[0], -p2[1]*p1[1]])
        coeffs = np.linalg.solve(matrix, src.reshape(8))

        warped = self.raw_img.transform((self.w, self.h), Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BILINEAR)
        scaled = warped.resize((target_w, target_h), Image.Resampling.BILINEAR)

        # Apply roll tilt
        roll_deg = math.degrees(roll)
        if abs(roll_deg) > 0.2:
            scaled = scaled.rotate(roll_deg, resample=Image.Resampling.BICUBIC, expand=False)

        return scaled

    def animate(self):
        self.canvas.delete("all")
        self.t += 0.05
        cx = self.canvas.winfo_width() // 2 or 320
        cy = self.canvas.winfo_height() // 2 or 260
        w = self.canvas.winfo_width() or 640
        h = self.canvas.winfo_height() or 520

        # Background HUD grid
        for gx in range(0, w, 55):
            self.canvas.create_line(gx, 0, gx, h, fill="#0c1424", width=1)
        for gy in range(0, h, 55):
            self.canvas.create_line(0, gy, w, gy, fill="#0c1424", width=1)

        # 1. Update Gaze Targets
        self.update_gaze_targets()

        # Smooth interpolation (ease-out lerp)
        lerp_speed = 0.055
        self.current_yaw += (self.target_yaw - self.current_yaw) * lerp_speed
        self.current_pitch += (self.target_pitch - self.current_pitch) * lerp_speed
        self.current_roll += (self.target_roll - self.current_roll) * lerp_speed
        self.current_dx += (self.target_dx - self.current_dx) * lerp_speed
        self.current_dy += (self.target_dy - self.current_dy) * lerp_speed

        # Micro-breathing oscillation
        breathe = math.sin(self.t * 1.5)
        y_breathe = breathe * 4.0
        scale = 0.90 + 0.012 * breathe

        # 2. Ambient Glittering Particles
        for p in self.particles:
            px = cx + p["x"] + math.sin(self.t * p["speed"] + p["phase"]) * 14
            py = cy + p["y"] + math.cos(self.t * p["speed"] * 0.8) * 12
            alpha = (math.sin(self.t * 3.0 + p["phase"]) + 1.0) / 2.0
            if alpha > 0.4:
                col = "#e0f7fa" if alpha > 0.75 else "#38bdf8"
                sz = 1.5 if alpha > 0.75 else 1.0
                self.canvas.create_oval(px - sz, py - sz, px + sz, py + sz, fill=col, outline="")

        # 3. Render 3D Perspective Face (No circle, no scanline)
        live_cx = cx + self.current_dx
        live_cy = cy + self.current_dy + y_breathe

        face_frame = self.get_perspective_face(
            self.current_yaw,
            self.current_pitch,
            self.current_roll,
            scale
        )
        self.tk_face = ImageTk.PhotoImage(face_frame)
        self.canvas.create_image(live_cx, live_cy, image=self.tk_face, anchor="center")

        self.after(30, self.animate)

if __name__ == "__main__":
    app = TestHeadGaze()
    app.after(5000, lambda: app.destroy())
    app.mainloop()
    print("Test finished successfully!")

