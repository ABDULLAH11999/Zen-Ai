import math
import time
import numpy as np
from PIL import Image, ImageDraw

data = np.load("models/head_scanlines.npy")
points = data[:, :3]
intensities = data[:, 3]

def render_3d_scanline_head(yaw_deg, pitch_deg, roll_deg=0.0, w=500, h=500):
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    roll = math.radians(roll_deg)
    
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    cos_x, sin_x = math.cos(pitch), math.sin(pitch)
    cos_z, sin_z = math.cos(roll), math.sin(roll)
    
    # 1. 3D Rotation
    x = points[:, 0]
    y = points[:, 1]
    z = points[:, 2]
    
    # Yaw
    x1 = x * cos_y + z * sin_y
    z1 = -x * sin_y + z * cos_y
    
    # Pitch
    y2 = y * cos_x - z1 * sin_x
    z2 = y * sin_x + z1 * cos_x
    
    # Roll
    x3 = x1 * cos_z - y2 * sin_z
    y3 = x1 * sin_z + y2 * cos_z
    
    # Perspective projection
    fov = 440.0
    dist = 330.0
    factor = fov / (z2 + dist)
    
    cx, cy = w // 2, h // 2
    px = cx + x3 * factor
    py = cy + y3 * factor
    
    # Render onto dark canvas
    img = Image.new("RGBA", (w, h), (7, 10, 20, 255))
    draw = ImageDraw.Draw(img)
    
    # Draw subtle background grid
    for gx in range(0, w, 50):
        draw.line([(gx, 0), (gx, h)], fill=(12, 20, 36, 255), width=1)
    for gy in range(0, h, 50):
        draw.line([(0, gy), (w, gy)], fill=(12, 20, 36, 255), width=1)
        
    # Ambient cyber dust
    np.random.seed(42)
    for _ in range(40):
        d_x = cx + int(np.random.uniform(-140, 140))
        d_y = cy + int(np.random.uniform(-150, 150))
        draw.ellipse([d_x-1, d_y-1, d_x+1, d_y+1], fill=(56, 189, 248, 200))
        
    # Sort by depth Z (back to front)
    sort_idx = np.argsort(z2)
    
    for idx in sort_idx:
        p_z = z2[idx]
        # Fade back points
        if p_z < -35:
            continue
            
        p_x = px[idx]
        p_y = py[idx]
        base_int = intensities[idx]
        
        # Depth shading
        z_norm = np.clip((p_z - (-30)) / 95.0, 0.0, 1.0)
        final_int = base_int * (0.35 + 0.65 * z_norm)
        
        # Color gradient matching Image 1: deep cyan to brilliant cyan-white
        if final_int > 0.82 and p_z > 20:
            col = (224, 247, 250, 255) # brilliant cyan-white
            sz = 1.6
        elif final_int > 0.60 and p_z > 0:
            col = (103, 232, 249, 240) # light cyan
            sz = 1.3
        elif final_int > 0.40:
            col = (6, 182, 212, 210) # vibrant cyan
            sz = 1.0
        elif final_int > 0.25:
            col = (8, 145, 178, 160) # medium teal
            sz = 0.8
        else:
            col = (14, 116, 144, 110) # deep teal
            sz = 0.6
            
        draw.ellipse([p_x - sz, p_y - sz, p_x + sz, p_y + sz], fill=col)
        
    return img

print("Rendering 4 real 3D views...")
t0 = time.time()
img_front = render_3d_scanline_head(0, 0)
img_right = render_3d_scanline_head(32, -6, 3)
img_left = render_3d_scanline_head(-32, -6, -3)
img_tilt_up = render_3d_scanline_head(15, 20, 0)
print(f"Rendered in {time.time()-t0:.3f}s")

combined = Image.new("RGBA", (1000, 1000), (7, 10, 20, 255))
combined.paste(img_front, (0, 0))
combined.paste(img_right, (500, 0))
combined.paste(img_left, (0, 500))
combined.paste(img_tilt_up, (500, 500))

combined.save("scratch/preview_mesh_scanline_angles.png")
print("Saved preview_mesh_scanline_angles.png successfully!")

