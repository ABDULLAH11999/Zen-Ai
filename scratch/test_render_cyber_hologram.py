import math
import time
import numpy as np
from PIL import Image, ImageDraw

data = np.load("models/head_scanlines.npy")
# data has shape (N, 4): x, y, z, intensity
points = data[:, :3]
intensities = data[:, 3]

# In models/head_scanlines.npy, how many slices?
# Let's inspect the unique y levels
unique_y = np.unique(points[:, 1])
num_slices = len(unique_y)
pts_per_ring = len(points) // num_slices
print(f"Num slices: {num_slices}, points per ring: {pts_per_ring}")

def render_cyber_hologram_3d(yaw_deg, pitch_deg, roll_deg=0.0, w=500, h=500):
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    roll = math.radians(roll_deg)
    
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    cos_x, sin_x = math.cos(pitch), math.sin(pitch)
    cos_z, sin_z = math.cos(roll), math.sin(roll)
    
    # 3D Rotation
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
    
    # Render onto dark canvas (#070a14)
    img = Image.new("RGBA", (w, h), (7, 10, 20, 255))
    draw = ImageDraw.Draw(img)
    
    # Subtle background HUD grid
    for gx in range(0, w, 55):
        draw.line([(gx, 0), (gx, h)], fill=(12, 20, 36, 255), width=1)
    for gy in range(0, h, 55):
        draw.line([(0, gy), (w, gy)], fill=(12, 20, 36, 255), width=1)
        
    # Ambient cyber dust sparkles
    np.random.seed(101)
    for _ in range(40):
        d_x = cx + int(np.random.uniform(-150, 150))
        d_y = cy + int(np.random.uniform(-160, 160))
        draw.ellipse([d_x-1, d_y-1, d_x+1, d_y+1], fill=(56, 189, 248, 180))

    # Reshape points into slices
    px_rings = px.reshape((num_slices, pts_per_ring))
    py_rings = py.reshape((num_slices, pts_per_ring))
    pz_rings = z2.reshape((num_slices, pts_per_ring))
    
    # Render each scanline ring
    # Draw horizontal scanline segments and micro-dots
    for s in range(num_slices):
        rx = px_rings[s]
        ry = py_rings[s]
        rz = pz_rings[s]
        
        # Sort points in this ring from left to right on screen
        order = np.argsort(rx)
        rx_sorted = rx[order]
        ry_sorted = ry[order]
        rz_sorted = rz[order]
        
        # Only render front-facing part of the slice (rz > -20)
        # to prevent interior clutter and give clean silhouette
        for i in range(len(rx_sorted) - 1):
            z_avg = (rz_sorted[i] + rz_sorted[i+1]) / 2.0
            if z_avg < -22.0:
                continue
                
            p1 = (rx_sorted[i], ry_sorted[i])
            p2 = (rx_sorted[i+1], ry_sorted[i+1])
            
            # Distance check to avoid connecting across back of head
            seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if seg_len > 18.0:
                continue
                
            # Depth coloring matching Image 1:
            # z_avg > 35: bright highlight
            # z_avg > 15: brilliant cyan
            # z_avg > -5: electric cyan
            # z_avg > -20: deep teal
            if z_avg > 42:
                col = (200, 245, 255, 255) # specular highlight
                lw = 2
            elif z_avg > 25:
                col = (103, 232, 249, 235) # brilliant cyan
                lw = 1
            elif z_avg > 8:
                col = (6, 182, 212, 190)  # cyan
                lw = 1
            elif z_avg > -10:
                col = (8, 145, 178, 140)  # teal
                lw = 1
            else:
                col = (14, 116, 144, 90)  # deep teal
                lw = 1
                
            draw.line([p1, p2], fill=col, width=lw)
            
            # Glittering cyber particle dots along the scanline
            if i % 3 == 0 and z_avg > 0:
                dot_col = (255, 255, 255, 255) if (z_avg > 35 and i % 6 == 0) else (103, 232, 249, 220)
                dot_sz = 1.2 if z_avg > 30 else 0.8
                draw.ellipse([p1[0]-dot_sz, p1[1]-dot_sz, p1[0]+dot_sz, p1[1]+dot_sz], fill=dot_col)
                
    return img

print("Rendering cyber hologram 3D...")
t0 = time.time()
img_front = render_cyber_hologram_3d(0, 0)
img_right = render_cyber_hologram_3d(28, -6, 3)
img_left = render_cyber_hologram_3d(-28, -6, -3)
img_tilt_up = render_cyber_hologram_3d(12, 18, 0)
print(f"Rendered 4 views in {time.time()-t0:.3f}s")

combined = Image.new("RGBA", (1000, 1000), (7, 10, 20, 255))
combined.paste(img_front, (0, 0))
combined.paste(img_right, (500, 0))
combined.paste(img_left, (0, 500))
combined.paste(img_tilt_up, (500, 500))

combined.save("scratch/preview_cyber_hologram_3d.png")
print("Saved preview_cyber_hologram_3d.png successfully!")

