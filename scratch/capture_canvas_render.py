import sys; sys.path.insert(0, ".")
import math
import tkinter as tk
from gui import VisualizerCanvas
from PIL import Image

root = tk.Tk()
root.geometry("600x450")
root.configure(bg="#070a14")
vc = VisualizerCanvas(root, width=600, height=450)
vc.pack(fill="both", expand=True)

# Turn head 20 deg right
vc.current_yaw = math.radians(20)
vc.current_pitch = math.radians(-8)
vc.current_roll = math.radians(-2)
vc.current_dx = 20.0
vc.current_dy = -8.0

# Render 1 frame
vc._render_hologram_face()
root.update()

print("VisualizerCanvas initialized and rendered live 3D dense frame!")
print("Face object type:", type(vc.tk_face))
root.destroy()

