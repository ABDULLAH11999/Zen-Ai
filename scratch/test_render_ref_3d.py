import math
import time
import numpy as np
from PIL import Image

pts = np.load("models/ref_3d_points.npy")
cols = np.load("models/ref_3d_colors.npy")

# Let's downsample if needed or render full
# Test full 113k points
print(f"Loaded {len(pts)} 3D points.")

def render_ref_3d(yaw_deg, pitch_deg, roll_deg=0.0, w=500, h=500):
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    roll = math.radians(roll_deg)
    
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    cos_x, sin_x = math.cos(pitch), math.sin(pitch)
    cos_z, sin_z = math.cos(roll), math.sin(roll)
    
    x = pts[:, 0]
    y = pts[:, 1]
    z = pts[:, 2]
    
    # Scale to fit nicely in 500x500 canvas
    scale = 0.85
    x = x * scale
    y = y * scale
    z = z * scale
    
    # 1. 3D Rotation
    # Yaw
    x1 = x * cos_y + z * sin_y
    z1 = -x * sin_y + z * cos_y
    # Pitch
    y2 = y * cos_x - z1 * sin_x
    z2 = y * sin_x + z1 * cos_x
    # Roll
    x3 = x1 * cos_z - y2 * sin_z
    y3 = x1 * sin_z + y2 * cos_z
    
    # 2. Perspective Projection
    fov = 440.0
    dist = 360.0
    factor = fov / (z2 + dist)
    
    cx, cy = w // 2, h // 2
    px = np.round(cx + x3 * factor).astype(np.int32)
    py = np.round(cy + y3 * factor).astype(np.int32)
    
    # 3. Fast Vectorized Buffer Rasterization
    # Sort by depth z2 (back to front so front particles overwrite back particles)
    sort_order = np.argsort(z2)
    
    px_sorted = px[sort_order]
    py_sorted = py[sort_order]
    z_sorted = z2[sort_order]
    cols_sorted = cols[sort_order].copy()
    
    # Filter within canvas bounds
    valid = (px_sorted >= 0) & (px_sorted < w) & (py_sorted >= 0) & (py_sorted < h)
    
    # Create dark canvas background (#070a14 = 7, 10, 20)
    buf = np.full((h, w, 4), [7, 10, 20, 255], dtype=np.uint8)
    
    # Add subtle background grid lines
    grid_col = np.array([12, 20, 36, 255], dtype=np.uint8)
    for gx in range(0, w, 55):
        buf[:, gx] = grid_col
    for gy in range(0, h, 55):
        buf[gy, :] = grid_col
        
    # Rasterize points
    valid_px = px_sorted[valid]
    valid_py = py_sorted[valid]
    valid_cols = cols_sorted[valid]
    
    # Set pixels
    buf[valid_py, valid_px] = valid_cols
    
    return Image.fromarray(buf)

print("Benchmarking 4 views...")
t0 = time.time()
img_front = render_ref_3d(0, 0)
img_right = render_ref_3d(24, -5, 3)
img_left = render_ref_3d(-24, -5, -3)
img_tilt_up = render_ref_3d(10, 16, 0)
print(f"Rendered 4 views of 113,464 points in {time.time()-t0:.3f}s ({4/(time.time()-t0):.1f} FPS)")

combined = Image.new("RGBA", (1000, 1000), (7, 10, 20, 255))
combined.paste(img_front, (0, 0))
combined.paste(img_right, (500, 0))
combined.paste(img_left, (0, 500))
combined.paste(img_tilt_up, (500, 500))

combined.save("scratch/preview_ref_3d_rotations.png")
print("Saved preview_ref_3d_rotations.png successfully!")

