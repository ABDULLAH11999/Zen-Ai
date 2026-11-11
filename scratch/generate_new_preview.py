import math
import numpy as np
from PIL import Image, ImageDraw

w, h = 600, 480
img = Image.new("RGBA", (w, h), (7, 10, 20, 255))
draw = ImageDraw.Draw(img)

# Cyber grid
for gx in range(0, w, 55):
    draw.line([(gx, 0), (gx, h)], fill=(12, 20, 36, 255), width=1)
for gy in range(0, h, 55):
    draw.line([(0, gy), (w, gy)], fill=(12, 20, 36, 255), width=1)

cx, cy = w // 2, h // 2

# Ambient glittering cyber dust particles
np.random.seed(101)
for _ in range(50):
    px = cx + int(np.random.uniform(-140, 140))
    py = cy + int(np.random.uniform(-150, 150))
    sz = np.random.choice([1, 2])
    col = (255, 255, 255, 255) if sz == 2 else (56, 189, 248, 255)
    draw.ellipse([px - sz, py - sz, px + sz, py + sz], fill=col)

# Load face and apply perspective angle (glancing slightly to the right & up)
face = Image.open(r"F:\Ai Tools\Zen Agent\Zen Ai\models\hologram_face.png").convert("RGBA")
fw, fh = face.size

yaw = 0.20   # looking slightly right
pitch = -0.12 # looking slightly up
roll = -0.04

dx = math.sin(yaw) * 18.0
dy = math.sin(pitch) * 15.0

dst = np.array([
    [-dx * 0.75, dy * 0.8],
    [fw - dx * 0.75, -dy * 0.8],
    [fw + dx * 0.75, fh - dy * 0.8],
    [dx * 0.75, fh + dy * 0.8]
])
src = np.array([[0, 0], [fw, 0], [fw, fh], [0, fh]], dtype=float)

matrix = []
for p1, p2 in zip(dst, src):
    matrix.append([p1[0], p1[1], 1, 0, 0, 0, -p2[0]*p1[0], -p2[0]*p1[1]])
    matrix.append([0, 0, 0, p1[0], p1[1], 1, -p2[1]*p1[0], -p2[1]*p1[1]])
coeffs = np.linalg.solve(matrix, src.reshape(8))

warped = face.transform((fw, fh), Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BILINEAR)
scale = 0.90
target_w = int(fw * scale)
target_h = int(fh * scale)
scaled = warped.resize((target_w, target_h), Image.Resampling.BILINEAR)
scaled = scaled.rotate(math.degrees(roll), resample=Image.Resampling.BICUBIC, expand=False)

# Paste with gaze translation
live_cx = cx + int(yaw * 42.0)
live_cy = cy + int(pitch * 28.0)
img.paste(scaled, (live_cx - target_w // 2, live_cy - target_h // 2), scaled)

out_preview = r"F:\Ai Tools\Zen Agent\Zen Ai\scratch\preview_clean_gaze.png"
img.save(out_preview, "PNG")
print("Saved preview_clean_gaze.png successfully!")

