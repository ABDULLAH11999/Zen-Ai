from PIL import Image, ImageFilter
import numpy as np
import os

img_path = r'C:/Users/LapStore/.gemini/antigravity/brain/844ac597-d85a-478b-890f-14cbed3033cd/.user_uploaded/media_1794334000075_480d22b4.jpg'
orig = Image.open(img_path).convert("RGBA")

# Let's inspect the corner pixels to find background color
arr = np.array(orig)
print("Top-left pixel (RGB):", arr[0, 0, :3])
print("Bottom-left pixel (RGB):", arr[-1, 0, :3])

# In Image 1, the background is dark navy-black: RGB ~(7, 18, 28)
# We can create a smooth alpha mask based on luminance so the head cleanly blends into any dark background
# High brightness -> 100% opaque. Very dark background -> 0% alpha with smooth cubic roll-off.
r, g, b, a = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]
# Luminance
lum = 0.299 * r + 0.587 * g + 0.114 * b

# Background cutoff around lum ~ 25
bg_thresh = 22.0
alpha = np.clip((lum - bg_thresh) / (120.0 - bg_thresh), 0.0, 1.0)
# Smoothstep
alpha = alpha * alpha * (3.0 - 2.0 * alpha)
arr[:,:,3] = (alpha * 255).astype(np.uint8)

# Color boost: Enhance the cyan/teal glow of the particles
# boost cyan: g and b channels slightly
arr[:,:,1] = np.clip(arr[:,:,1].astype(np.float32) * 1.15, 0, 255).astype(np.uint8)
arr[:,:,2] = np.clip(arr[:,:,2].astype(np.float32) * 1.25, 0, 255).astype(np.uint8)

blended_face = Image.fromarray(arr)
out_dir = r"F:\Ai Tools\Zen Agent\Zen Ai\models"
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "hologram_face.png")
blended_face.save(out_path, "PNG")
print("Saved blended transparent hologram face to:", out_path)

