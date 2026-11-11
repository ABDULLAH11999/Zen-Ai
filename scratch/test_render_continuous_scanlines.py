import math
import time
import numpy as np
from PIL import Image, ImageDraw

data = np.load("models/head_scanlines.npy")
points = data[:, :3]
intensities = data[:, 3]

unique_y = np.unique(points[:, 1])
num_slices = len(unique_y)
pts_per_ring = len(points) // num_slices

def render_continuous_scanlines(yaw_deg, pitch_deg, roll_deg=0.0, w=520, h=520):
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    roll = math.radians(roll_deg)
    
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    cos_x, sin_x = math.cos(pitch), math.sin(pitch)
    cos_z, sin_z = math.cos(roll), math.sin(roll)
    
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
    fov = 430.0
    dist = 330.0
    factor = fov / (z2 + dist)
    
    cx, cy = w // 2, h // 2
    px = cx + x3 * factor
    py = cy + y3 * factor
    
    img = Image.new("RGBA", (w, h), (7, 10, 20, 255))
    draw = ImageDraw.Draw(img)
    
    # Subtle background HUD grid
    for gx in range(0, w, 55):
        draw.line([(gx, 0), (gx, h)], fill=(12, 20, 36, 255), width=1)
    for gy in range(0, h, 55):
        draw.line([(0, gy), (w, gy)], fill=(12, 20, 36, 255), width=1)
        
    # Ambient cyber dust
    np.random.seed(99)
    for _ in range(40):
        d_x = cx + int(np.random.uniform(-150, 150))
        d_y = cy + int(np.random.uniform(-160, 160))
        draw.ellipse([d_x-1, d_y-1, d_x+1, d_y+1], fill=(56, 189, 248, 170))

    # Slices are contiguous in data: slice s has points [s*pts_per_ring : (s+1)*pts_per_ring]
    for s in range(num_slices):
        start_idx = s * pts_per_ring
        end_idx = start_idx + pts_per_ring
        
        rx = px[start_idx:end_idx]
        ry = py[start_idx:end_idx]
        rz = z2[start_idx:end_idx]
        
        # Connect adjacent points in this ring
        for i in range(pts_per_ring - 1):
            z1_p = rz[i]
            z2_p = rz[i+1]
            z_avg = (z1_p + z2_p) / 2.0
            
            # Clip back points
            if z_avg < -22.0:
                continue
                
            p1 = (rx[i], ry[i])
            p2 = (rx[i+1], ry[i+1])
            
            # Segment length threshold to prevent wrap-around jumps
            seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if seg_len > 16.0:
                continue
                
            # Depth coloring (Image 1 gradient: deep teal -> electric cyan -> brilliant cyan highlight)
            if z_avg > 40:
                col = (220, 248, 255, 255)
                lw = 2
            elif z_avg > 20:
                col = (103, 232, 249, 230)
                lw = 1
            elif z_avg > 0:
                col = (6, 182, 212, 190)
                lw = 1
            elif z_avg > -12:
                col = (8, 145, 178, 140)
                lw = 1
            else:
                col = (14, 116, 144, 90)
                lw = 1
                
            draw.line([p1, p2], fill=col, width=lw)
            
            # Sparkling cyber dots along the scanline
            if i % 3 == 0 and z_avg > 2:
                dot_col = (255, 255, 255, 255) if (z_avg > 35 and i % 6 == 0) else (103, 232, 249, 220)
                dot_sz = 1.2 if z_avg > 30 else 0.8
                draw.ellipse([p1[0]-dot_sz, p1[1]-dot_sz, p1[0]+dot_sz, p1[1]+dot_sz], fill=dot_col)
                
    return img

print("Rendering continuous scanlines...")
t0 = time.time()
img_front = render_continuous_scanlines(0, 0)
img_right = render_continuous_scanlines(30, -6, 3)
img_left = render_continuous_scanlines(-30, -6, -3)
img_tilt_up = render_continuous_scanlines(10, 18, 0)
print(f"Rendered in {time.time()-t0:.3f}s")

combined = Image.new("RGBA", (1040, 1040), (7, 10, 20, 255))
combined.paste(img_front, (0, 0))
combined.paste(img_right, (520, 0))
combined.paste(img_left, (0, 520))
combined.paste(img_tilt_up, (520, 520))

combined.save("scratch/preview_continuous_scanlines.png")
print("Saved preview_continuous_scanlines.png successfully!")

