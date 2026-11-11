import time
import tkinter as tk
from PIL import Image, ImageTk, ImageEnhance
import numpy as np

img_path = r'C:/Users/LapStore/.gemini/antigravity/brain/844ac597-d85a-478b-890f-14cbed3033cd/.user_uploaded/media_1794334000075_480d22b4.jpg'
base_img = Image.open(img_path).convert("RGBA")

# Measure performance of creating 50 frames
start = time.time()
for i in range(50):
    scale = 1.0 + 0.02 * np.sin(i * 0.1)
    w = int(240 * scale)
    h = int(250 * scale)
    resized = base_img.resize((w, h), Image.Resampling.BILINEAR)
elapsed = time.time() - start
print(f"50 resizes took {elapsed:.3f}s ({50/elapsed:.1f} FPS)")

