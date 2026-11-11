import math
import time
import numpy as np
from PIL import Image, ImageDraw

from test_3d_point_cloud_head import create_humanoid_head_point_cloud

points, intensities = create_humanoid_head_point_cloud()
num_pts = len(points)

def render_3d_head(yaw_deg, pitch_deg, roll_deg=0.0, w=500, h=500):
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    roll = math.radians(roll_deg)
    
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    cos_x, sin_x = math.cos(pitch), math.sin(pitch)
    cos_z, sin_z = math.cos(roll), math.sin(roll)
    
    # 1. Yaw rotation
    x = points[:, 0]
    y = points[:, 1]
    z = points[:, 2]
    
    x1 = x * cos_y + z * sin_y
    z1 = -x * sin_y + z * cos_y
    
    # 2. Pitch rotation
    y2 = y * cos_x - z1 * sin_x
    z2 = y * sin_x + z1 * cos_x
    
    # 3. Roll rotation
    x3 = x1 * cos_z - y2 * sin_z
    y3 = x1 * sin_z + y2 * cos_z
    
    # 4. Perspective projection
    fov = 420.0
    dist = 340.0
    factor = fov / (z2 + dist)
    
    cx, cy = w // 2, h // 2
    px = cx + x3 * factor
    py = cy + y3 * factor
    
    # Render onto dark RGBA image (#070a14 = 7, 10, 20)
    img = Image.new("RGBA", (w, h), (7, 10, 20, 255))
    draw = ImageDraw.Draw(img)
    
    # Sort points by depth z2 (back to front)
    sort_idx = np.argsort(z2)
    
    # Draw particles with depth-based brightness and size
    for idx in sort_idx:
        p_z = z2[idx]
        # Back-face cull or heavy fade for points far in back
        if p_z < -30:
            continue
            
        p_x = px[idx]
        p_y = py[idx]
        base_int = intensities[idx]
        
        # Depth shading
        # z2 ranges roughly from -30 to +80
        z_norm = np.clip((p_z - (-30)) / 100.0, 0.0, 1.0)
        final_int = base_int * (0.35 + 0.65 * z_norm)
        
        # Color gradient matching Image 1: deep cyan to brilliant cyan-white
        if final_int > 0.85 and p_z > 25:
            col = (224, 247, 250, 255) # brilliant cyan-white
            sz = 1.5
        elif final_int > 0.65 and p_z > 5:
            col = (103, 232, 249, 240) # light cyan
            sz = 1.2
        elif final_int > 0.45:
            col = (6, 182, 212, 200) # vibrant cyan
            sz = 1.0
        elif final_int > 0.30:
            col = (8, 145, 178, 160) # medium teal
            sz = 0.8
        else:
            col = (14, 116, 144, 110) # deep teal
            sz = 0.6
            
        draw.ellipse([p_x - sz, p_y - sz, p_x + sz, p_y + sz], fill=col)
        
    return img

print("Rendering angles...")
t0 = time.time()
img_front = render_3d_head(0, 0)
img_right = render_3d_head(28, -6, 4)
img_left = render_3d_head(-28, -6, -4)
img_tilt_up = render_3d_head(12, 18, 0)
print(f"Rendered 4 views in {time.time()-t0:.3f}s")

# Combine 4 views into a grid preview
combined = Image.new("RGBA", (1000, 1000), (7, 10, 20, 255))
combined.paste(img_front, (0, 0))
combined.paste(img_right, (500, 0))
combined.paste(img_left, (0, 500))
combined.paste(img_tilt_up, (500, 500))

combined.save("scratch/preview_real_3d_angles.png")
print("Saved scratch/preview_real_3d_angles.png successfully!")

