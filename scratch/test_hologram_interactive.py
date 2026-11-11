import tkinter as tk
import numpy as np
from PIL import Image, ImageTk
import math
import time

class TestHologramInteractive(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("600x520")
        self.title("Real 3D Blended Hologram Face Test")
        self.configure(bg="#070a14")

        self.canvas = tk.Canvas(self, bg="#070a14", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Load blended hologram face
        self.raw_img = Image.open(r"F:\Ai Tools\Zen Agent\Zen Ai\models\hologram_face.png")
        self.base_arr = np.array(self.raw_img)
        self.h, self.w = self.base_arr.shape[:2]

        self.t = 0.0
        self.state = "IDLE"
        self.mouth_open = 0.0

        # Ambient particles
        self.particles = []
        for _ in range(45):
            self.particles.append({
                "x": np.random.uniform(-150, 150),
                "y": np.random.uniform(-160, 160),
                "speed": np.random.uniform(0.4, 1.2),
                "phase": np.random.uniform(0, math.pi * 2)
            })

        self.animate()

    def get_articulated_face(self, mouth_amount):
        """Displaces jaw and lower lip vertically to simulate realistic speaking articulation."""
        if mouth_amount <= 0.5:
            return self.raw_img

        arr = self.base_arr.copy()
        # Mouth & jaw region: y from 225 to 330, x from 90 to 245
        jaw_start = 228
        jaw_end = 340
        jaw_h = jaw_end - jaw_start
        
        # Shift rows downwards smoothly
        disp_map = np.zeros(self.h)
        for y in range(jaw_start, jaw_end):
            progress = (y - jaw_start) / jaw_h
            # Smooth cubic curve
            disp_map[y] = int(mouth_amount * math.sin(progress * math.pi * 0.75))

        # Apply vertical displacement
        out = arr.copy()
        for y in range(self.h - 1, jaw_start, -1):
            dy = int(disp_map[y])
            if dy > 0 and (y - dy) >= 0:
                # Displace the central face columns (jaw & mouth)
                out[y, 90:245] = arr[y - dy, 90:245]
                
        return Image.fromarray(out)

    def animate(self):
        self.canvas.delete("all")
        self.t += 0.05
        cx = self.canvas.winfo_width() // 2 or 300
        cy = self.canvas.winfo_height() // 2 or 260

        # Draw subtle cyber grid
        w = self.canvas.winfo_width() or 600
        h = self.canvas.winfo_height() or 520
        for gx in range(0, w, 50):
            self.canvas.create_line(gx, 0, gx, h, fill="#0c1424", width=1)
        for gy in range(0, h, 50):
            self.canvas.create_line(0, gy, w, gy, fill="#0c1424", width=1)

        # 3D Floating and Breathing
        breathe = math.sin(self.t * 1.4)
        y_float = breathe * 6.0
        scale = 0.88 + 0.015 * breathe
        rot_angle = math.sin(self.t * 0.7) * 2.2 # Subtle 3D tilt

        # Speaking dynamics
        is_speaking = (self.state == "SPEAKING")
        if is_speaking:
            self.mouth_open = (math.sin(self.t * 16) * 0.5 + 0.5) * 11.0 + (math.sin(self.t * 26) * 0.3) * 4.0
        else:
            self.mouth_open = 0.0

        # Generate articulated face image
        face_img = self.get_articulated_face(self.mouth_open)
        
        # Scale and rotate
        target_w = int(self.w * scale)
        target_h = int(self.h * scale)
        scaled_img = face_img.resize((target_w, target_h), Image.Resampling.BILINEAR)
        if abs(rot_angle) > 0.3:
            scaled_img = scaled_img.rotate(rot_angle, resample=Image.Resampling.BICUBIC, expand=False)
            
        self.tk_face = ImageTk.PhotoImage(scaled_img)

        # 1. Background Holographic Glow & Rings
        r_ring = 155 + math.sin(self.t * 2.0) * 6
        arc_ang = (self.t * 30) % 360
        self.canvas.create_oval(cx - r_ring, cy + y_float - r_ring,
                               cx + r_ring, cy + y_float + r_ring, outline="#0d2137", width=1.5)
        self.canvas.create_arc(cx - r_ring - 4, cy + y_float - r_ring - 4,
                              cx + r_ring + 4, cy + y_float + r_ring + 4,
                              start=arc_ang, extent=65, outline="#00f0ff", width=2.5, style="arc")
        self.canvas.create_arc(cx - r_ring - 4, cy + y_float - r_ring - 4,
                              cx + r_ring + 4, cy + y_float + r_ring + 4,
                              start=arc_ang + 180, extent=45, outline="#38bdf8", width=1.5, style="arc")

        # 2. Ambient Cyber Particles (Image 1 dust)
        for p in self.particles:
            px = cx + p["x"] + math.sin(self.t * p["speed"] + p["phase"]) * 14
            py = cy + y_float + p["y"] + math.cos(self.t * p["speed"] * 0.8) * 12
            alpha = (math.sin(self.t * 3.0 + p["phase"]) + 1.0) / 2.0
            if alpha > 0.4:
                col = "#e0f7fa" if alpha > 0.75 else "#38bdf8"
                sz = 1.5 if alpha > 0.75 else 1.0
                self.canvas.create_oval(px - sz, py - sz, px + sz, py + sz, fill=col, outline="")

        # 3. Render the Real 3D Blended Hologram Face
        self.canvas.create_image(cx, cy + y_float, image=self.tk_face, anchor="center")

        # 4. Vertical Luminescence Laser Scanline Wave
        scan_y = cy + y_float + math.sin(self.t * 2.2) * (target_h * 0.42)
        # Laser beam line
        self.canvas.create_line(cx - target_w * 0.38, scan_y, cx + target_w * 0.38, scan_y,
                                fill="#e0f7fa", width=2.0)
        # Soft laser glow halo
        self.canvas.create_line(cx - target_w * 0.44, scan_y, cx + target_w * 0.44, scan_y,
                                fill="#00f0ff", width=1.0)

        # 5. If Speaking: Dynamic Voice Ripples radiating from head
        if is_speaking:
            for rip in range(3):
                rip_r = r_ring + ((self.t * 80 + rip * 45) % 90)
                rip_alpha = 1.0 - (rip_r - r_ring) / 90.0
                if rip_alpha > 0.05:
                    self.canvas.create_oval(cx - rip_r, cy + y_float - rip_r,
                                           cx + rip_r, cy + y_float + rip_r,
                                           outline="#00f0ff" if rip % 2 == 0 else "#38bdf8",
                                           width=1.5)

        self.after(30, self.animate)

if __name__ == "__main__":
    app = TestHologramInteractive()
    # Test state sequence: Idle for 3s -> Speaking for 4s -> Idle
    app.after(3000, lambda: setattr(app, "state", "SPEAKING"))
    app.after(7000, lambda: setattr(app, "state", "IDLE"))
    app.after(10000, lambda: app.destroy())
    app.mainloop()

