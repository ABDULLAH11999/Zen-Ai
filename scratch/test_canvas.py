import tkinter as tk
import math
import time

class VisualizerCanvas(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(bg="#080d1a", highlightthickness=0)
        self.angle = 0.0
        self.inner_angle = 0.0
        self.pulse = 0.0
        self.current_state = "IDLE"
        self.bind("<Configure>", self._on_resize)
        self.center_x = 250
        self.center_y = 200
        self._animate()

    def _on_resize(self, event):
        self.center_x = event.width // 2
        self.center_y = event.height // 2

    def set_state(self, state: str):
        self.current_state = state.upper()

    def _animate(self):
        self.delete("all")
        cx, cy = self.center_x, self.center_y
        self.angle += 0.03
        self.inner_angle -= 0.04
        self.pulse += 0.08
        
        # Determine colors based on state
        if self.current_state == "LISTENING":
            color_primary = "#fbbf24"
            color_secondary = "#f59e0b"
            wave_amp = 25
            state_text = "MIC ACTIVE // LISTENING..."
        elif self.current_state == "THINKING":
            color_primary = "#a855f7"
            color_secondary = "#818cf8"
            wave_amp = 30
            state_text = "NEURAL INFERENCE // PROCESSING..."
        elif self.current_state == "SPEAKING":
            color_primary = "#00f0ff"
            color_secondary = "#38bdf8"
            wave_amp = 40
            state_text = "SYNTHESIZING SPEECH // TRANSMITTING..."
        elif self.current_state == "DICTATING":
            color_primary = "#ff0055"
            color_secondary = "#00f0ff"
            wave_amp = 35
            state_text = "LIVE DICTATION // SPEAK NOW..."
        else:
            color_primary = "#00f0ff"
            color_secondary = "#0284c7"
            wave_amp = 10
            state_text = "NEURAL CORE // STANDBY ONLINE"

        # Outer radar ring
        r_outer = 110 + int(math.sin(self.pulse * 0.5) * 4)
        self.create_oval(cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer, outline="#1e293b", width=2)
        
        # Rotating outer ticks
        num_ticks = 16
        for i in range(num_ticks):
            theta = self.angle + (i * 2 * math.pi / num_ticks)
            x1 = cx + (r_outer - 8) * math.cos(theta)
            y1 = cy + (r_outer - 8) * math.sin(theta)
            x2 = cx + (r_outer + 8) * math.cos(theta)
            y2 = cy + (r_outer + 8) * math.sin(theta)
            tick_col = color_primary if i % 4 == 0 else "#334155"
            self.create_line(x1, y1, x2, y2, fill=tick_col, width=2)

        # Rotating accent arc
        arc_angle_deg = (self.angle * 180 / math.pi) % 360
        self.create_arc(cx - r_outer - 6, cy - r_outer - 6, cx + r_outer + 6, cy + r_outer + 6,
                        start=arc_angle_deg, extent=70, outline=color_primary, width=3, style="arc")
        self.create_arc(cx - r_outer - 6, cy - r_outer - 6, cx + r_outer + 6, cy + r_outer + 6,
                        start=arc_angle_deg + 180, extent=45, outline=color_secondary, width=2, style="arc")

        # Inner ring
        r_inner = 75
        self.create_oval(cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner, outline="#1e293b", width=1)
        
        # Dynamic circular waveform bars
        bars = 24
        for b in range(bars):
            theta = self.inner_angle + (b * 2 * math.pi / bars)
            bar_height = math.sin(self.pulse + b * 0.8) * wave_amp
            if bar_height < 0:
                bar_height = abs(bar_height) * 0.5
            bx1 = cx + (r_inner - 2) * math.cos(theta)
            by1 = cy + (r_inner - 2) * math.sin(theta)
            bx2 = cx + (r_inner + bar_height + 4) * math.cos(theta)
            by2 = cy + (r_inner + bar_height + 4) * math.sin(theta)
            self.create_line(bx1, by1, bx2, by2, fill=color_primary, width=2)

        # Core glowing center orb
        core_r = 38 + int(math.sin(self.pulse) * 4)
        self.create_oval(cx - core_r - 8, cy - core_r - 8, cx + core_r + 8, cy + core_r + 8,
                         fill="", outline=color_secondary, width=1)
        self.create_oval(cx - core_r, cy - core_r, cx + core_r, cy + core_r,
                         fill="#0d1b2a", outline=color_primary, width=2)
        
        # Center AI Icon & readout
        self.create_text(cx, cy - 6, text="⚡", fill=color_primary, font=("Segoe UI Symbol", 20, "bold"))
        self.create_text(cx, cy + 14, text="ZEN", fill="#e2e8f0", font=("Consolas", 10, "bold"))
        
        # Sub-readout text under core
        self.create_text(cx, cy + r_outer + 35, text=state_text, fill=color_primary, font=("Consolas", 10, "bold"))

        self.after(30, self._animate)

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("500x450")
    vis = VisualizerCanvas(root)
    vis.pack(fill="both", expand=True)
    root.after(3000, lambda: root.destroy())
    root.mainloop()

