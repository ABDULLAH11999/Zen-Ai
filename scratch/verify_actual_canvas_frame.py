import math
import numpy as np
from gui import VisualizerCanvas
import tkinter as tk
from PIL import Image

root = tk.Tk()
root.geometry("600x450")
root.configure(bg="#070a14")
vc = VisualizerCanvas(root, width=600, height=450)
vc.pack(fill="both", expand=True)

# Set an angle looking 25 deg to the right and 10 deg up
vc.current_yaw = math.radians(25)
vc.current_pitch = math.radians(-10)
vc.current_roll = math.radians(-3)
vc.current_dx = 25.0
vc.current_dy = -10.0

# Render 1 frame
vc._render_hologram_face()
root.update()

# Extract the PIL image from vc.tk_face
# Since tk_face is a PhotoImage, let's verify vc.tk_face exists
print("Successfully rendered live 3D face frame! Object:", type(vc.tk_face))
root.destroy()

