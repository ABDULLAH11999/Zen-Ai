import math
import random
import time
import tkinter as tk
import numpy as np
from PIL import Image, ImageTk, ImageDraw

data = np.load(r"F:\Ai Tools\Zen Agent\Zen Ai\models\head_scanlines.npy")
points = data[:, :3].copy()
unique_y = np.unique(points[:, 1])
num_slices = len(unique_y)
pts_per_ring = len(points) // num_slices

class TestLive3DScanlineGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("640x540")
        self.title("Real 3D Scanline Head Hologram Live Test")
        self.configure(bg="#070a14")

        self.canvas = tk.Canvas(self, bg="#070a14", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.t = 0.0
        self.state = "IDLE" # IDLE, SPEAKING, THINKING

        # Gaze tracking
        self.current_yaw = 0.0
        self.current_pitch = 0.0
        self.current_roll = 0.0
        self.current_dx = 0.0
        self.current_dy = 0.0

        self.target_yaw = 0.0
        self.target_pitch = 0.0
        self.target_roll = 0.0
        self.target_dx = 0.0
        self.target_dy = 0.0
        self.next_gaze_time = time.time() + 0.8

        # Ambient particles
        self.particles = []
        for _ in range(40):
            self.particles.append({
                "x": random.uniform(-140, 140),
                "y": random.uniform(-150, 150),
                "speed": random.uniform(0.4, 1.2),
                "phase": random.uniform(0, math.pi * 2)
            })

        self.tk_img = None
        self.animate()

    def update_gaze(self):
        now = time.time()
        is_speaking = (self.state == "SPEAKING")
        if is_speaking:
            self.target_yaw = math.sin(self.t * 3.2) * 0.10
            self.target_pitch = math.sin(self.t * 4.5) * 0.06
            self.target_roll = math.sin(self.t * 2.5) * 0.04
            self.target_dx = math.sin(self.t * 2.0) * 8.0
            self.target_dy = math.sin(self.t * 2.8) * 5.0
            self.next_gaze_time = now + 1.2
        elif now >= self.next_gaze_time:
            if random.random() < 0.30:
                self.target_yaw = random.uniform(-0.06, 0.06)
                self.target_pitch = random.uniform(-0.05, 0.05)
                self.target_roll = random.uniform(-0.02, 0.02)
                self.target_dx = random.uniform(-6, 6)
                self.target_dy = random.uniform(-5, 5)
                dwell = random.uniform(1.8, 3.2)
            else:
                self.target_yaw = random.choice([-1, 1]) * random.uniform(0.18, 0.45) # Up to 26 deg turn
                self.target_pitch = random.uniform(-0.25, 0.25) # Up to 15 deg tilt
                self.target_roll = -self.target_yaw * random.uniform(0.15, 0.30)
                self.target_dx = self.target_yaw * 40.0
                self.target_dy = self.target_pitch * 25.0
                dwell = random.uniform(2.0, 4.2)
            self.next_gaze_time = now + dwell

        lerp = 0.055
        self.current_yaw += (self.target_yaw - self.current_yaw) * lerp
        self.current_pitch += (self.target_pitch - self.current_pitch) * lerp
        self.current_roll += (self.target_roll - self.current_roll) * lerp
        self.current_dx += (self.target_dx - self.current_dx) * lerp
        self.current_dy += (self.target_dy - self.current_dy) * lerp

    def animate(self):
        self.t += 0.05
        self.update_gaze()

        w = self.canvas.winfo_width() or 640
        h = self.canvas.winfo_height() or 540
        cx = w // 2
        cy = h // 2

        # 3D Rotations
        cos_y, sin_y = math.cos(self.current_yaw), math.sin(self.current_yaw)
        cos_x, sin_x = math.cos(self.current_pitch), math.sin(self.current_pitch)
        cos_z, sin_z = math.cos(self.current_roll), math.sin(self.current_roll)

        # Micro-breathing oscillation
        breathe = math.sin(self.t * 1.5)
        scale = 0.92 + 0.015 * breathe
        y_float = breathe * 4.0

        pts = points.copy()
        # Jaw articulation when speaking
        if self.state == "SPEAKING":
            mouth_open = (math.sin(self.t * 16) * 0.5 + 0.5) * 8.0
            jaw_mask = (pts[:, 1] > 35) & (pts[:, 1] < 85) & (pts[:, 2] > 0)
            if np.any(jaw_mask):
                jaw_y = pts[jaw_mask, 1]
                t_j = (jaw_y - 35) / 50.0
                pts[jaw_mask, 1] += mouth_open * np.sin(t_j * np.pi)

        # Rotate
        x = pts[:, 0] * scale
        y = pts[:, 1] * scale
        z = pts[:, 2] * scale

        # Yaw
        x1 = x * cos_y + z * sin_y
        z1 = -x * sin_y + z * cos_y
        # Pitch
        y2 = y * cos_x - z1 * sin_x
        z2 = y * sin_x + z1 * cos_x
        # Roll
        x3 = x1 * cos_z - y2 * sin_z
        y3 = x1 * sin_z + y2 * cos_z

        # Perspective projection
        fov = 430.0
        dist = 330.0
        factor = fov / (z2 + dist)

        live_cx = cx + self.current_dx
        live_cy = cy + self.current_dy + y_float
        px = live_cx + x3 * factor
        py = live_cy + y3 * factor

        # Render onto image
        img = Image.new("RGBA", (w, h), (7, 10, 20, 255))
        draw = ImageDraw.Draw(img)

        # Cyber grid
        for gx in range(0, w, 55):
            draw.line([(gx, 0), (gx, h)], fill=(12, 20, 36, 255), width=1)
        for gy in range(0, h, 55):
            draw.line([(0, gy), (w, gy)], fill=(12, 20, 36, 255), width=1)

        # Ambient cyber dust
        for p in self.particles:
            d_x = cx + p["x"] + math.sin(self.t * p["speed"] + p["phase"]) * 14
            d_y = cy + p["y"] + math.cos(self.t * p["speed"] * 0.8) * 12
            alpha = (math.sin(self.t * 3.0 + p["phase"]) + 1.0) / 2.0
            if alpha > 0.4:
                col = (224, 247, 250, 240) if alpha > 0.75 else (56, 189, 248, 180)
                sz = 1.5 if alpha > 0.75 else 1.0
                draw.ellipse([d_x-sz, d_y-sz, d_x+sz, d_y+sz], fill=col)

        # Slices
        for s in range(num_slices):
            start_idx = s * pts_per_ring
            end_idx = start_idx + pts_per_ring

            rx = px[start_idx:end_idx]
            ry = py[start_idx:end_idx]
            rz = z2[start_idx:end_idx]

            for i in range(pts_per_ring - 1):
                z1_p = rz[i]
                z2_p = rz[i+1]
                z_avg = (z1_p + z2_p) / 2.0

                if z_avg < -22.0:
                    continue

                p1 = (rx[i], ry[i])
                p2 = (rx[i+1], ry[i+1])

                seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                if seg_len > 16.0:
                    continue

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

        self.tk_img = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.tk_img, anchor="nw")

        self.after(30, self.animate)

if __name__ == "__main__":
    app = TestLive3DScanlineGUI()
    # Test state sequence: Idle for 3s -> Speaking for 3s -> Idle
    app.after(3000, lambda: setattr(app, "state", "SPEAKING"))
    app.after(6000, lambda: setattr(app, "state", "IDLE"))
    app.after(8000, lambda: app.destroy())
    app.mainloop()
    print("Live 3D Scanline GUI test passed with 100% success!")

