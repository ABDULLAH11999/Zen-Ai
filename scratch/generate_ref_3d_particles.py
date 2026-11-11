import math
import time
import numpy as np
from PIL import Image

# Load reference image
ref_path = "C:/Users/LapStore/.gemini/antigravity/brain/844ac597-d85a-478b-890f-14cbed3033cd/.user_uploaded/media_1794404606648_9010cd88.png"
ref_img = Image.open(ref_path).convert("RGBA")
arr = np.array(ref_img).astype(np.float32)
H, W = arr.shape[:2]

# Detect background
bg = arr[0:20, 0:20, :3].mean(axis=(0, 1))
diff = np.linalg.norm(arr[:, :, :3] - bg, axis=-1)

# Mask for head pixels
mask = diff > 16.0
y_coords, x_coords = np.where(mask)

# Find head radius at each Y level
min_x_per_y = {}
max_x_per_y = {}
for y, x in zip(y_coords, x_coords):
    if y not in min_x_per_y or x < min_x_per_y[y]:
        min_x_per_y[y] = x
    if y not in max_x_per_y or x > max_x_per_y[y]:
        max_x_per_y[y] = x

points = []
colors = []

# Center of head
cx_head = 151.0
cy_head = 170.0

for y, x in zip(y_coords, x_coords):
    color = arr[y, x]
    
    # Half width at this Y
    min_x = min_x_per_y[y]
    max_x = max_x_per_y[y]
    w_y = max(10.0, (max_x - min_x) / 2.0)
    c_y = (min_x + max_x) / 2.0
    
    # Normalized u coordinate from -1 (left edge) to +1 (right edge)
    u = np.clip((x - c_y) / w_y, -1.0, 1.0)
    
    # Base depth from ellipsoid surface
    # R_z is approximately 1.15 * w_y
    rad_z = w_y * 1.10
    z_base = rad_z * math.sqrt(max(0.0, 1.0 - u * u))
    
    # Facial feature depth perturbations
    z_feat = 0.0
    u_abs = abs(u)
    
    # 1. Nose: Y in [145, 195], center u < 0.28
    if 145 <= y <= 195 and u_abs < 0.28:
        nose_y = math.sin((y - 145) / 50.0 * math.pi)
        nose_u = math.cos(u_abs / 0.28 * math.pi * 0.5) ** 2
        z_feat += 22.0 * nose_u * (nose_y ** 0.8)
        
    # 2. Eye sockets: Y in [115, 145], u in [0.22, 0.62]
    elif 115 <= y <= 145 and 0.20 < u_abs < 0.60:
        eye_y = math.sin((y - 115) / 30.0 * math.pi)
        eye_u = math.sin((u_abs - 0.20) / 0.40 * math.pi)
        z_feat -= 12.0 * eye_u * eye_y
        
    # 3. Brow ridge: Y in [105, 120], u < 0.60
    elif 105 <= y <= 120 and u_abs < 0.60:
        brow_y = math.sin((y - 105) / 15.0 * math.pi)
        brow_u = math.cos(u_abs / 0.60 * math.pi * 0.5)
        z_feat += 6.0 * brow_u * brow_y
        
    # 4. Lips: Y in [205, 235], u < 0.35
    elif 205 <= y <= 235 and u_abs < 0.35:
        mouth_u = math.cos(u_abs / 0.35 * math.pi * 0.5)
        if 208 <= y <= 218: # Upper lip
            z_feat += 8.0 * mouth_u * math.sin((y - 208) / 10.0 * math.pi)
        elif 222 <= y <= 232: # Lower lip
            z_feat += 9.0 * mouth_u * math.sin((y - 222) / 10.0 * math.pi)
            
    # 5. Chin: Y in [240, 265], u < 0.32
    elif 240 <= y <= 265 and u_abs < 0.32:
        chin_y = math.sin((y - 240) / 25.0 * math.pi)
        chin_u = math.cos(u_abs / 0.32 * math.pi * 0.5)
        z_feat += 11.0 * chin_u * chin_y
        
    # 6. Neck: Y > 275 recedes back
    elif y > 275:
        z_feat -= (y - 275) * 0.15
        
    z = z_base + z_feat
    
    # Center X and Y around (0, 0)
    X = float(x - cx_head)
    Y = float(y - cy_head)
    Z = float(z)
    
    points.append([X, Y, Z])
    colors.append([int(color[0]), int(color[1]), int(color[2]), int(color[3])])
    
    # Back of head points (so rotation to sides is completely solid and dense)
    # Generate back points for cranium and sides
    if z_base > 4.0:
        z_back = -z_base * 1.08
        points.append([X, Y, float(z_back)])
        # Back points have deeper teal shading
        r_back = int(color[0] * 0.25)
        g_back = int(color[1] * 0.45)
        b_back = int(color[2] * 0.55)
        colors.append([r_back, g_back, b_back, 180])

pts_3d = np.array(points, dtype=np.float32)
cols_3d = np.array(colors, dtype=np.uint8)

print(f"Total 3D volumetric particles: {len(pts_3d)}")
print(f"X bounds: [{pts_3d[:,0].min():.1f}, {pts_3d[:,0].max():.1f}]")
print(f"Y bounds: [{pts_3d[:,1].min():.1f}, {pts_3d[:,1].max():.1f}]")
print(f"Z bounds: [{pts_3d[:,2].min():.1f}, {pts_3d[:,2].max():.1f}]")

np.save("models/ref_3d_points.npy", pts_3d)
np.save("models/ref_3d_colors.npy", cols_3d)
print("Saved models/ref_3d_points.npy successfully!")

