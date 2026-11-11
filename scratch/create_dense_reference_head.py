import math
import time
import numpy as np
from PIL import Image, ImageDraw

def create_dense_reference_head(num_slices=140, pts_per_slice=180):
    """
    Creates a dense 3D holographic point cloud matching the exact silhouette,
    facial anatomy, and scanline density of the reference image.
    """
    points = []
    colors = []
    
    # Y from cranium top to neck/collarbone: -115 to +130
    y_min, y_max = -115.0, 130.0
    y_levels = np.linspace(y_min, y_max, num_slices)
    
    for s_idx, y in enumerate(y_levels):
        # 1. Anatomical radius R_x and R_z based on reference image proportions
        # Reference image: cranium width ~135, height ~245
        if y < -70: # Cranium dome (smooth hemisphere)
            t = (y - (-115)) / 45.0
            rad_x = 54.0 * math.sqrt(max(0.01, t * (2.0 - t)))
            rad_z_front = 55.0 * math.sqrt(max(0.01, t * (2.0 - t)))
            rad_z_back = 62.0 * math.sqrt(max(0.01, t * (2.0 - t)))
            z_c = -5.0 * (1.0 - t)
            feature = "dome"
        elif y < -35: # Forehead
            t = (y - (-70)) / 35.0
            rad_x = 54.0 - t * 2.0
            rad_z_front = 55.0 + t * 2.0
            rad_z_back = 63.0
            z_c = 0.0
            feature = "forehead"
        elif y < -10: # Brow ridge & Eye sockets
            t = (y - (-35)) / 25.0
            rad_x = 52.0 - t * 2.0
            rad_z_front = 54.0
            rad_z_back = 60.0
            z_c = 2.0
            feature = "eyes"
        elif y < 22: # Nose & Cheekbones
            t = (y - (-10)) / 32.0
            rad_x = 50.0 - t * 5.0
            rad_z_front = 52.0 - t * 4.0
            rad_z_back = 58.0 - t * 8.0
            z_c = 5.0
            feature = "nose"
        elif y < 55: # Mouth & Upper Jaw
            t = (y - 22) / 33.0
            rad_x = 44.0 - t * 9.0
            rad_z_front = 47.0 - t * 7.0
            rad_z_back = 48.0 - t * 8.0
            z_c = 6.0
            feature = "mouth"
        elif y < 85: # Chin & Lower Jaw
            t = (y - 55) / 30.0
            rad_x = 35.0 * (1.0 - t * 0.48)
            rad_z_front = 40.0 * (1.0 - t * 0.42)
            rad_z_back = 38.0 * (1.0 - t * 0.50)
            z_c = 5.0 * (1.0 - t)
            feature = "chin"
        elif y < 112: # Slender neck
            t = (y - 85) / 27.0
            rad_x = 18.0 + t * 3.0
            rad_z_front = 20.0 + t * 4.0
            rad_z_back = 22.0 + t * 4.0
            z_c = -12.0
            feature = "neck"
        else: # Trapezius / Collarbone flare
            t = (y - 112) / 18.0
            rad_x = 21.0 + t * 35.0
            rad_z_front = 24.0 + t * 25.0
            rad_z_back = 26.0 + t * 22.0
            z_c = -10.0
            feature = "collar"
            
        # 2. Points along this horizontal scanline ring
        # Sample points around the front and sides (angle from -pi*0.65 to +pi*0.65)
        # and back of head for 3D rotation
        angles = np.linspace(-math.pi * 0.95, math.pi * 0.95, pts_per_slice)
        
        for p_idx, th in enumerate(angles):
            sin_th = math.sin(th)
            cos_th = math.cos(th)
            
            rad_z = rad_z_front if cos_th >= 0 else rad_z_back
            
            x = rad_x * sin_th
            z = z_c + rad_z * cos_th
            
            # Surface normal approximation for lighting
            nx = sin_th
            ny = (y / 150.0) * 0.3
            nz = cos_th
            
            # Anatomical face features
            if cos_th > 0:
                angle_ratio = abs(sin_th) # 0 is center, 1 is profile
                
                # Nose
                if feature == "nose" and angle_ratio < 0.26:
                    bell = math.cos(angle_ratio / 0.26 * math.pi * 0.5) ** 2
                    nose_t = (y - (-10)) / 32.0
                    nose_shape = math.sin(nose_t * math.pi)
                    z += 20.0 * bell * (nose_shape ** 0.85)
                    # Normal tilted forward
                    nz += 0.3 * bell
                    
                # Eye sockets (depression)
                elif feature == "eyes" and 0.18 < angle_ratio < 0.62:
                    eye_t = (angle_ratio - 0.18) / 0.44
                    recess = math.sin(eye_t * math.pi)
                    z -= 11.0 * recess
                    # Normal tilted inward (shadowed)
                    nz -= 0.4 * recess
                    
                # Brow ridge
                elif feature == "eyes" and y < -22 and angle_ratio < 0.62:
                    brow = math.cos(angle_ratio / 0.62 * math.pi * 0.5)
                    z += 6.5 * brow
                    ny -= 0.2 * brow
                    
                # Mouth & Lips
                elif feature == "mouth" and angle_ratio < 0.34:
                    mouth_t = math.cos(angle_ratio / 0.34 * math.pi * 0.5)
                    if 26 <= y <= 36: # Upper lip
                        z += 7.5 * mouth_t * math.sin((y - 26) / 10.0 * math.pi)
                    elif 38 <= y <= 48: # Lower lip
                        z += 8.5 * mouth_t * math.sin((y - 38) / 10.0 * math.pi)
                    elif 35 < y < 39: # Mouth aperture
                        z -= 2.0 * mouth_t
                        
                # Chin
                elif feature == "chin" and y < 75 and angle_ratio < 0.32:
                    chin_t = math.cos(angle_ratio / 0.32 * math.pi * 0.5)
                    z += 10.0 * chin_t * math.sin((y - 55) / 20.0 * math.pi)
                    
            # Normalize normal vector
            n_len = math.sqrt(nx*nx + ny*ny + nz*nz)
            nx, ny, nz = nx/n_len, ny/n_len, nz/n_len
            
            # --- HOLOGRAPHIC LIGHTING (EXACTLY MATCHING REFERENCE IMAGE) ---
            # 1. Top light vector L_top = (0, -0.9, 0.4)
            # Produces the brilliant glow on the crown of the head in reference image
            dot_top = max(0.0, -ny * 0.9 + nz * 0.4)
            top_light = (dot_top ** 3.0) * 1.3
            
            # 2. Ambient front glow
            ambient = 0.28 + 0.35 * max(0.0, nz)
            
            # 3. Fresnel rim light: silhouette edges glow
            # View vector V = (0, 0, 1) -> N dot V = nz
            fresnel = ((1.0 - abs(nz)) ** 2.2) * 0.45
            
            # 4. Total intensity
            intensity = ambient + top_light + fresnel
            
            # Eye socket shadowing (deep dark eyes like reference image)
            if feature == "eyes" and cos_th > 0 and 0.18 < abs(sin_th) < 0.62:
                intensity *= 0.35
                
            # Bottom chest fade
            if y > 112:
                intensity *= max(0.0, 1.0 - (y - 112) / 18.0)
                
            # Random micro-glitter twinkle factor (matches the diamond sparkles in reference)
            glitter_noise = np.random.uniform(0.85, 1.25)
            # 2% of points are bright star sparkles
            if np.random.random() < 0.02 and cos_th > 0:
                glitter_noise = 2.0
                
            intensity = min(1.0, max(0.05, intensity * glitter_noise))
            
            # Convert intensity to Reference Image Color Palette:
            # - High intensity / crown: brilliant cyan-white (220, 248, 255)
            # - Medium intensity: vibrant cyan (56, 189, 248) to (6, 182, 212)
            # - Low intensity: deep mysterious teal (8, 145, 178) to (14, 116, 144)
            # - Shadow / back: dark oceanic navy (10, 35, 55)
            if intensity > 0.85:
                r = int(180 + (intensity - 0.85) / 0.15 * 75)
                g = int(235 + (intensity - 0.85) / 0.15 * 20)
                b = 255
                a = 255
            elif intensity > 0.50:
                t_c = (intensity - 0.50) / 0.35
                r = int(30 + t_c * 150)
                g = int(180 + t_c * 55)
                b = int(220 + t_c * 35)
                a = int(220 + t_c * 35)
            elif intensity > 0.20:
                t_c = (intensity - 0.20) / 0.30
                r = int(10 + t_c * 20)
                g = int(100 + t_c * 80)
                b = int(140 + t_c * 80)
                a = int(160 + t_c * 60)
            else:
                t_c = intensity / 0.20
                r = int(5 + t_c * 5)
                g = int(35 + t_c * 65)
                b = int(60 + t_c * 80)
                a = int(60 + t_c * 100)
                
            points.append([x, y, z])
            colors.append([r, g, b, a])
            
    return np.array(points, dtype=np.float32), np.array(colors, dtype=np.uint8)

t0 = time.time()
np.random.seed(42)
pts, cols = create_dense_reference_head(num_slices=130, pts_per_slice=200)
print(f"Generated {len(pts)} points in {time.time()-t0:.3f}s")
np.save("models/dense_head_points.npy", pts)
np.save("models/dense_head_colors.npy", cols)
print("Saved models/dense_head_points.npy and dense_head_colors.npy!")

