import math
import time
import numpy as np
from PIL import Image

ref_path = "C:/Users/LapStore/.gemini/antigravity/brain/844ac597-d85a-478b-890f-14cbed3033cd/.user_uploaded/media_1794406136732_df8f1070.jpg"
ref_img = Image.open(ref_path).convert("RGBA")
ref_arr = np.array(ref_img).astype(np.float32)
H, W = ref_arr.shape[:2]

# Head bounds in reference image
# Center X = 151, Center Y = 145
# Half width = 98, Half height = 125
cx_ref = 151.0
cy_ref = 145.0
hw_ref = 98.0
hh_ref = 125.0

# Build 3D mesh grid of scanlines
num_y = 190       # 190 vertical scanlines for ultra dense look
num_th = 240      # 240 points per scanline ring

# Y from -1.0 (cranium top) to +1.0 (neck bottom)
v_norm = np.linspace(-1.0, 1.0, num_y)
# Angular theta around the head from -pi*0.62 to +pi*0.62
th_vals = np.linspace(-math.pi * 0.62, math.pi * 0.62, num_th)

grid_v, grid_th = np.meshgrid(v_norm, th_vals, indexing="ij")

# Anatomical radii based on normalized height v in [-1, 1]
# v = -1 (cranium top): narrows to 0
# v = -0.5 to 0.1 (forehead, eyes, nose): full width ~ 100 px
# v = 0.5 (chin): width ~ 75 px
# v = 0.8 to 1.0 (neck): width ~ 64 px
rad_x = np.zeros_like(grid_v)
rad_z = np.zeros_like(grid_v)

for i in range(num_y):
    v = v_norm[i]
    if v < -0.5: # Cranium dome
        t = (v - (-1.0)) / 0.5
        rx = 98.0 * math.sqrt(max(0.01, t * (2.0 - t)))
        rz = 105.0 * math.sqrt(max(0.01, t * (2.0 - t)))
    elif v < 0.2: # Brow, eyes, upper cheeks
        t = (v - (-0.5)) / 0.7
        rx = 98.0 + t * 4.0
        rz = 105.0
    elif v < 0.6: # Cheeks to jaw taper
        t = (v - 0.2) / 0.4
        rx = 102.0 - t * 24.0
        rz = 105.0 - t * 15.0
    elif v < 0.8: # Chin
        t = (v - 0.6) / 0.2
        rx = 78.0 - t * 14.0
        rz = 90.0 - t * 18.0
    else: # Slender neck
        t = (v - 0.8) / 0.2
        rx = 64.0 + t * 8.0
        rz = 72.0 + t * 6.0
    rad_x[i, :] = rx
    rad_z[i, :] = rz

# 3D Coordinates
Y_3d = grid_v * hh_ref
X_3d = rad_x * np.sin(grid_th)
Z_3d = rad_z * np.cos(grid_th)

# Feature depth perturbations in true 3D
# Nose: v in [-0.10, 0.28], th near 0
nose_v = np.clip(1.0 - np.abs(grid_v - 0.08) / 0.20, 0.0, 1.0)
nose_th = np.clip(1.0 - np.abs(grid_th) / 0.22, 0.0, 1.0)
z_nose = 22.0 * (nose_v ** 1.2) * (nose_th ** 2.0)

# Eye sockets: v in [-0.25, -0.05], th around +/- 0.32
eye_v = np.clip(1.0 - np.abs(grid_v - (-0.15)) / 0.12, 0.0, 1.0)
eye_th = np.clip(1.0 - np.abs(np.abs(grid_th) - 0.32) / 0.16, 0.0, 1.0)
z_eyes = -12.0 * eye_v * eye_th

# Brow ridge: v in [-0.32, -0.20]
brow_v = np.clip(1.0 - np.abs(grid_v - (-0.25)) / 0.08, 0.0, 1.0)
brow_th = np.clip(1.0 - np.abs(grid_th) / 0.45, 0.0, 1.0)
z_brow = 6.0 * brow_v * brow_th

# Lips: v in [0.35, 0.55]
lips_v = np.clip(1.0 - np.abs(grid_v - 0.45) / 0.10, 0.0, 1.0)
lips_th = np.clip(1.0 - np.abs(grid_th) / 0.25, 0.0, 1.0)
z_lips = 8.0 * lips_v * lips_th

# Chin: v in [0.60, 0.78]
chin_v = np.clip(1.0 - np.abs(grid_v - 0.68) / 0.10, 0.0, 1.0)
chin_th = np.clip(1.0 - np.abs(grid_th) / 0.26, 0.0, 1.0)
z_chin = 10.0 * chin_v * chin_th

Z_total = Z_3d + z_nose + z_eyes + z_brow + z_lips + z_chin

# UV coordinates permanently bound to the 3D surface points
# u_norm from -1 to 1 based on sin(grid_th)
u_norm = np.sin(grid_th)
ref_x = np.clip(cx_ref + u_norm * hw_ref, 0, W - 1).astype(np.int32)
ref_y = np.clip(cy_ref + grid_v * hh_ref, 0, H - 1).astype(np.int32)

# Sample reference texture
surface_colors = ref_arr[ref_y, ref_x].copy()

# Boost cyan/teal specular slightly for rich holographic brilliance
# and feather bottom neck smoothly into #070a14
neck_fade = np.clip(1.0 - (grid_v - 0.75) / 0.25, 0.0, 1.0)
surface_colors[:, :, 3] *= (neck_fade ** 1.8)

# Feather side edges so silhouette is completely soft and organic
th_edge_fade = np.clip((math.pi * 0.62 - np.abs(grid_th)) / 0.16, 0.0, 1.0)
surface_colors[:, :, 3] *= th_edge_fade

# Boost colors by 15% for vivid holographic presence
surface_colors[:, :, 1] = np.clip(surface_colors[:, :, 1] * 1.15, 0, 255)
surface_colors[:, :, 2] = np.clip(surface_colors[:, :, 2] * 1.25, 0, 255)

# Flatten points & colors
pts_3d = np.stack([X_3d.ravel(), Y_3d.ravel(), Z_total.ravel()], axis=-1).astype(np.float32)
cols_3d = surface_colors.reshape((-1, 4)).astype(np.float32)

# Filter out low alpha
valid = cols_3d[:, 3] > 10.0
pts_final = pts_3d[valid]
cols_final = cols_3d[valid]

print(f"Final UV-Bound 3D Model: {len(pts_final)} points.")
np.save("models/uv_surface_3d_points.npy", pts_final)
np.save("models/uv_surface_3d_colors.npy", cols_final)
print("Saved models/uv_surface_3d_points.npy successfully!")

