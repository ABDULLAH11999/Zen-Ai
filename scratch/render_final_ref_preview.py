import math
import time
import numpy as np
from PIL import Image

pts = np.load("models/ref_3d_points.npy")
cols = np.load("models/ref_3d_colors.npy").astype(np.float32)

def render_ref_3d_clean(yaw_deg, pitch_deg, roll_deg=0.0, w=500, h=500):
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    roll = math.radians(roll_deg)
    
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    cos_x, sin_x = math.cos(pitch), math.sin(pitch)
    cos_z, sin_z = math.cos(roll), math.sin(roll)
    
    scale = 0.90
    x = pts[:, 0] * scale
    y = pts[:, 1] * scale
    z = pts[:, 2] * scale
    
    # 3D Matrix Rotation
    x1 = x * cos_y + z * sin_y
    z1 = -x * sin_y + z * cos_y
    y2 = y * cos_x - z1 * sin_x
    z2 = y * sin_x + z1 * cos_x
    x3 = x1 * cos_z - y2 * sin_z
    y3 = x1 * sin_z + y2 * cos_z
    
    # Perspective Projection
    fov = 440.0
    dist = 360.0
    factor = fov / (z2 + dist)
    
    cx, cy = w // 2, h // 2
    px = np.round(cx + x3 * factor).astype(np.int32)
    py = np.round(cy + y3 * factor).astype(np.int32)
    
    # Depth sort
    sort_order = np.argsort(z2)
    px_s = px[sort_order]
    py_s = py[sort_order]
    cols_s = cols[sort_order]
    
    valid = (px_s >= 0) & (px_s < w) & (py_s >= 0) & (py_s < h)
    v_px = px_s[valid]
    v_py = py_s[valid]
    v_cols = cols_s[valid]
    
    # Base dark canvas background (#070a14 = 7, 10, 20)
    buf = np.full((h, w, 4), [7, 10, 20, 255], dtype=np.uint8)
    
    # Subtle background HUD grid
    grid_col = np.array([12, 20, 36, 255], dtype=np.uint8)
    for gx in range(0, w, 55):
        buf[:, gx] = grid_col
    for gy in range(0, h, 55):
        buf[gy, :] = grid_col
        
    # True Alpha Compositing onto dark background
    alpha = v_cols[:, 3:4] / 255.0
    bg_val = np.array([7.0, 10.0, 20.0], dtype=np.float32)
    rgb = v_cols[:, :3] * alpha + bg_val * (1.0 - alpha)
    
    buf[v_py, v_px, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    buf[:, :, 3] = 255
    
    return Image.fromarray(buf)

print("Rendering 4 views...")
t0 = time.time()
img_front = render_ref_3d_clean(0, 0)
img_right = render_ref_3d_clean(22, -4, 2)
img_left = render_ref_3d_clean(-22, -4, -2)
img_tilt_up = render_ref_3d_clean(8, 14, 0)
print(f"Rendered in {time.time()-t0:.3f}s")

combined = Image.new("RGBA", (1000, 1000), (7, 10, 20, 255))
combined.paste(img_front, (0, 0))
combined.paste(img_right, (500, 0))
combined.paste(img_left, (0, 500))
combined.paste(img_tilt_up, (500, 500))

combined.save("scratch/preview_ref_3d_final.png")
print("Saved scratch/preview_ref_3d_final.png successfully!")

