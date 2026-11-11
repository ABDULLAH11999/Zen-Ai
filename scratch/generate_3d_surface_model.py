import math
import time
import numpy as np
from PIL import Image

# Load reference image
ref_path = "C:/Users/LapStore/.gemini/antigravity/brain/844ac597-d85a-478b-890f-14cbed3033cd/.user_uploaded/media_1794406136732_df8f1070.jpg"
ref_img = Image.open(ref_path).convert("RGBA")
ref_arr = np.array(ref_img).astype(np.float32)
H, W = ref_arr.shape[:2]

# Measure background and feather edges cleanly into #070a14
bg = ref_arr[0:20, 0:20, :3].mean(axis=(0, 1))
diff = np.linalg.norm(ref_arr[:, :, :3] - bg, axis=-1)

cx_ref = 151.0
cy_ref = 160.0

# Build 3D mesh grid of scanlines
num_y = 180       # 180 vertical scanlines for dense resolution
num_th = 220      # 220 points per scanline ring

# Measured head half-widths from reference image
y_min, y_max = -135.0, 140.0
y_vals = np.linspace(y_min, y_max, num_y)

# Angular range around the front and sides: -pi*0.62 to +pi*0.62
th_vals = np.linspace(-math.pi * 0.62, math.pi * 0.62, num_th)

grid_y, grid_th = np.meshgrid(y_vals, th_vals, indexing="ij")

# Calculate anatomical radii R_x and R_z based on measured reference silhouette
# Width at eyes (y ~ -10 to 20): half-width ~ 100
# Cranium dome (y < -50): narrows smoothly
# Chin (y ~ 70 to 95): half-width ~ 75
# Neck (y ~ 100 to 135): half-width ~ 65
t_norm = (grid_y - y_min) / (y_max - y_min)

rad_x = np.zeros_like(grid_y)
rad_z = np.zeros_like(grid_y)

for i in range(num_y):
    y = y_vals[i]
    if y < -65: # Cranium dome
        t = (y - y_min) / (-65 - y_min)
        rx = 98.0 * math.sqrt(max(0.01, t * (2.0 - t)))
        rz = 105.0 * math.sqrt(max(0.01, t * (2.0 - t)))
    elif y < 20: # Forehead, brow, eyes, upper cheeks (full width)
        t = (y - (-65)) / 85.0
        rx = 98.0 + t * 4.0
        rz = 105.0
    elif y < 75: # Cheeks to jaw taper
        t = (y - 20) / 55.0
        rx = 102.0 - t * 24.0
        rz = 105.0 - t * 15.0
    elif y < 105: # Chin to upper neck
        t = (y - 75) / 30.0
        rx = 78.0 - t * 14.0
        rz = 90.0 - t * 20.0
    else: # Slender neck to shoulders
        t = (y - 105) / 35.0
        rx = 64.0 + t * 12.0
        rz = 70.0 + t * 10.0
    rad_x[i, :] = rx
    rad_z[i, :] = rz

# 3D Coordinates
X_base = rad_x * np.sin(grid_th)
Z_base = rad_z * np.cos(grid_th)
Y_base = grid_y.copy()

# Facial anatomical feature displacement
# 1. Nose protrusion (y in [-15, 35], centered around th=0)
nose_mask_y = np.clip(1.0 - np.abs(grid_y - 10.0) / 25.0, 0.0, 1.0)
nose_mask_th = np.clip(1.0 - np.abs(grid_th) / 0.22, 0.0, 1.0)
z_nose = 22.0 * (nose_mask_y ** 1.2) * (nose_mask_th ** 2.0)

# 2. Eye socket recesses (y in [-35, -5], th around +/- 0.32)
eye_mask_y = np.clip(1.0 - np.abs(grid_y - (-20.0)) / 15.0, 0.0, 1.0)
eye_mask_th = np.clip(1.0 - np.abs(np.abs(grid_th) - 0.30) / 0.16, 0.0, 1.0)
z_eyes = -12.0 * eye_mask_y * eye_mask_th

# 3. Brow ridge (y in [-40, -25])
brow_mask_y = np.clip(1.0 - np.abs(grid_y - (-32.0)) / 10.0, 0.0, 1.0)
brow_mask_th = np.clip(1.0 - np.abs(grid_th) / 0.45, 0.0, 1.0)
z_brow = 6.0 * brow_mask_y * brow_mask_th

# 4. Lips (y in [45, 70])
lips_mask_y = np.clip(1.0 - np.abs(grid_y - 58.0) / 14.0, 0.0, 1.0)
lips_mask_th = np.clip(1.0 - np.abs(grid_th) / 0.25, 0.0, 1.0)
z_lips = 8.0 * lips_mask_y * lips_mask_th

# 5. Chin (y in [75, 95])
chin_mask_y = np.clip(1.0 - np.abs(grid_y - 85.0) / 12.0, 0.0, 1.0)
chin_mask_th = np.clip(1.0 - np.abs(grid_th) / 0.26, 0.0, 1.0)
z_chin = 10.0 * chin_mask_y * chin_mask_th

# 6. Neck recedes (y > 100)
neck_t = np.clip((grid_y - 100.0) / 40.0, 0.0, 1.0)
z_neck = -neck_t * 15.0

Z_total = Z_base + z_nose + z_eyes + z_brow + z_lips + z_chin + z_neck

# Map unrotated surface points directly to reference image UV coordinates
# X in [-100, 100] maps to ref image X in [151 - 100, 151 + 100]
u_tex = np.clip(cx_ref + X_base, 0, W - 1).astype(np.int32)
v_tex = np.clip(cy_ref + Y_base, 0, H - 1).astype(np.int32)

# Sample reference image colors
sample_colors = ref_arr[v_tex, u_tex].copy()

# Feather the bottom neck and outer boundary into #070a14
# Bottom neck fade (Y > 95)
neck_fade = np.clip(1.0 - (grid_y - 95.0) / 45.0, 0.0, 1.0)
sample_colors[:, :, 3] *= (neck_fade ** 1.8)

# Boundary theta fade
th_fade = np.clip((math.pi * 0.62 - np.abs(grid_th)) / 0.15, 0.0, 1.0)
sample_colors[:, :, 3] *= th_fade

# Flatten arrays
pts_flat = np.stack([X_base.ravel(), Y_base.ravel(), Z_total.ravel()], axis=-1).astype(np.float32)
cols_flat = sample_colors.reshape((-1, 4)).astype(np.float32)

# Filter out zero alpha points
valid_alpha = cols_flat[:, 3] > 8.0
pts_model = pts_flat[valid_alpha]
cols_model = cols_flat[valid_alpha]

print(f"Generated 3D Surface Model: {len(pts_model)} points.")
np.save("models/surface_3d_points.npy", pts_model)
np.save("models/surface_3d_colors.npy", cols_model)
print("Saved models/surface_3d_points.npy and surface_3d_colors.npy!")

