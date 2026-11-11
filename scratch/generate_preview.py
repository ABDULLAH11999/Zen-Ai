import os
import math
import numpy as np
from PIL import Image, ImageDraw

# Create a 600x480 preview canvas image
w, h = 600, 480
img = Image.new("RGBA", (w, h), (7, 10, 20, 255))
draw = ImageDraw.Draw(img)

# Cyber grid
for gx in range(0, w, 50):
    draw.line([(gx, 0), (gx, h)], fill=(12, 20, 36, 255), width=1)
for gy in range(0, h, 50):
    draw.line([(0, gy), (w, gy)], fill=(12, 20, 36, 255), width=1)

cx, cy = w // 2, h // 2

# Background glow rings
r_ring = 155
draw.ellipse([cx - r_ring, cy - r_ring, cx + r_ring, cy + r_ring], outline=(13, 33, 55, 255), width=2)
draw.arc([cx - r_ring - 4, cy - r_ring - 4, cx + r_ring + 4, cy + r_ring + 4], start=45, end=115, fill=(0, 240, 255, 255), width=3)
draw.arc([cx - r_ring - 4, cy - r_ring - 4, cx + r_ring + 4, cy + r_ring + 4], start=225, end=275, fill=(56, 189, 248, 255), width=2)

# Load blended face
face = Image.open(r"F:\Ai Tools\Zen Agent\Zen Ai\models\hologram_face.png")
target_w, target_h = int(face.width * 0.9), int(face.height * 0.9)
face_scaled = face.resize((target_w, target_h), Image.Resampling.BILINEAR)

# Paste with alpha
paste_x = cx - target_w // 2
paste_y = cy - target_h // 2
img.paste(face_scaled, (paste_x, paste_y), face_scaled)

# Vertical scan wave line
scan_y = cy + 10
draw.line([(cx - int(target_w * 0.42), scan_y), (cx + int(target_w * 0.42), scan_y)], fill=(224, 247, 250, 255), width=2)
draw.line([(cx - int(target_w * 0.48), scan_y), (cx + int(target_w * 0.48), scan_y)], fill=(0, 240, 255, 255), width=1)

# Sparkling cyber dust
np.random.seed(42)
for _ in range(50):
    px = cx + int(np.random.uniform(-140, 140))
    py = cy + int(np.random.uniform(-150, 150))
    sz = np.random.choice([1, 2])
    col = (255, 255, 255, 255) if sz == 2 else (56, 189, 248, 255)
    draw.ellipse([px - sz, py - sz, px + sz, py + sz], fill=col)

out_preview = r"F:\Ai Tools\Zen Agent\Zen Ai\scratch\preview_real_face.png"
img.save(out_preview, "PNG")
print("Saved preview to:", out_preview)

