import math
import time
import numpy as np
from PIL import Image, ImageDraw

pts = np.load("models/dense_head_points.npy")
cols = np.load("models/dense_head_colors.npy")

num_slices = 130
pts_per_slice = 200

def render_dense_head(yaw_deg, pitch_deg, roll_deg=0.0, w=520, h=520):
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)
    roll = math.radians(roll_deg)
    
    cos_y, sin_y = math.cos(yaw), math.sin(yaw)
    cos_x, sin_x = math.cos(pitch), math.sin(pitch)
    cos_z, sin_z = math.cos(roll), math.sin(roll)
    
    x = pts[:, 0]
    y = pts[:, 1]
    z = pts[:, 2]
    
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
        
    # Ambient cyber dust sparkles
    np.random.seed(101)
    for _ in range(40):
        d_x = cx + int(np.random.uniform(-150, 150))
        d_y = cy + int(np.random.uniform(-160, 160))
        draw.ellipse([d_x-1, d_y-1, d_x+1, d_y+1], fill=(56, 189, 248, 170))

    # Render horizontal scanline curves with depth shading
    for s in range(num_slices):
        start_idx = s * pts_per_slice
        end_idx = start_idx + pts_per_slice
        
        rx = px[start_idx:end_idx]
        ry = py[start_idx:end_idx]
        rz = z2[start_idx:end_idx]
        rc = cols[start_idx:end_idx]
        
        # Connect adjacent points in this horizontal slice
        for i in range(pts_per_slice - 1):
            z_avg = (rz[i] + rz[i+1]) / 2.0
            
            # Clip back points to preserve crisp silhouette and prevent back-face occlusion
            if z_avg < -20.0:
                continue
                
            p1 = (rx[i], ry[i])
            p2 = (rx[i+1], ry[i+1])
            
            seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if seg_len > 12.0:
                continue
                
            # Line color blended from point colors
            c1 = rc[i]
            c2 = rc[i+1]
            c_avg = ((int(c1[0]) + int(c2[0])) // 2,
                     (int(c1[1]) + int(c2[1])) // 2,
                     (int(c1[2]) + int(c2[2])) // 2,
                     (int(c1[3]) + int(c2[3])) // 2)
            
            # Line width: 2px on bright highlights, 1px on rest
            lw = 2 if (z_avg > 35 and c_avg[0] > 150) else 1
            draw.line([p1, p2], fill=c_avg, width=lw)
            
            # Micro-glitter sparkles along scanline
            if i % 4 == 0 and z_avg > 5:
                if c_avg[0] > 180 or c_avg[1] > 220:
                    draw.ellipse([p1[0]-1, p1[1]-1, p1[0]+1, p1[1]+1], fill=(255, 255, 255, 240))
                elif c_avg[2] > 190 and i % 8 == 0:
                    draw.ellipse([p1[0]-0.8, p1[1]-0.8, p1[0]+0.8, p1[1]+0.8], fill=(103, 232, 249, 200))
                    
    return img

print("Rendering dense reference head...")
t0 = time.time()
img_front = render_dense_head(0, 0)
img_right = render_dense_head(26, -5, 3)
img_left = render_dense_head(-26, -5, -3)
img_tilt_up = render_dense_head(10, 16, 0)
print(f"Rendered 4 views in {time.time()-t0:.3f}s")

combined = Image.new("RGBA", (1040, 1040), (7, 10, 20, 255))
combined.paste(img_front, (0, 0))
combined.paste(img_right, (520, 0))
combined.paste(img_left, (0, 520))
combined.paste(img_tilt_up, (520, 520))

combined.save("scratch/preview_dense_reference_head.png")
print("Saved scratch/preview_dense_reference_head.png successfully!")

