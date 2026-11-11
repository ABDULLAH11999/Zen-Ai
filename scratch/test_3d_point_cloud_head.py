import math
import time
import numpy as np
from PIL import Image, ImageDraw

def create_humanoid_head_point_cloud():
    points = []
    intensities = []
    
    # 110 scanlines from cranium top to shoulders
    num_slices = 110
    y_min, y_max = -125.0, 135.0
    
    for s in range(num_slices):
        t = s / (num_slices - 1)
        y = y_min + t * (y_max - y_min)
        
        # Determine anatomical radius & centers
        if y < -75: # Top cranium dome
            tc = (y - (-125)) / 50.0
            rad_x = 56.0 * math.sqrt(max(0.01, tc * (2.0 - tc)))
            rad_z_front = 56.0 * math.sqrt(max(0.01, tc * (2.0 - tc)))
            rad_z_back = 65.0 * math.sqrt(max(0.01, tc * (2.0 - tc)))
            zc = -10.0 * (1.0 - tc)
            feature = "dome"
        elif y < -35: # Forehead & upper temples
            tf = (y - (-75)) / 40.0
            rad_x = 56.0 - tf * 2.0
            rad_z_front = 56.0 + tf * 2.0
            rad_z_back = 66.0
            zc = -2.0
            feature = "forehead"
        elif y < -10: # Brow ridge & Eye sockets
            te = (y - (-35)) / 25.0
            rad_x = 53.0
            rad_z_front = 55.0
            rad_z_back = 64.0
            zc = 0.0
            feature = "eyes"
        elif y < 25: # Nose, Cheekbones
            tn = (y - (-10)) / 35.0
            rad_x = 52.0 - tn * 6.0
            rad_z_front = 52.0 - tn * 4.0
            rad_z_back = 60.0 - tn * 10.0
            zc = 4.0
            feature = "nose"
        elif y < 55: # Mouth, Lips, Upper Jaw
            tm = (y - 25) / 30.0
            rad_x = 44.0 - tm * 8.0
            rad_z_front = 46.0 - tm * 5.0
            rad_z_back = 48.0 - tm * 8.0
            zc = 6.0
            feature = "mouth"
        elif y < 85: # Chin, Lower Jaw
            tj = (y - 55) / 30.0
            rad_x = 35.0 * (1.0 - tj * 0.45)
            rad_z_front = 39.0 * (1.0 - tj * 0.40)
            rad_z_back = 38.0 * (1.0 - tj * 0.45)
            zc = 4.0 * (1.0 - tj)
            feature = "chin"
        elif y < 115: # Neck
            tnk = (y - 85) / 30.0
            rad_x = 21.0 + tnk * 4.0
            rad_z_front = 22.0 + tnk * 5.0
            rad_z_back = 24.0 + tnk * 5.0
            zc = -14.0
            feature = "neck"
        else: # Collarbone & upper chest flare
            tcol = (y - 115) / 20.0
            rad_x = 25.0 + tcol * 32.0
            rad_z_front = 27.0 + tcol * 22.0
            rad_z_back = 29.0 + tcol * 20.0
            zc = -12.0
            feature = "collar"

        # Number of particle points along this scanline ring
        num_pts = 100
        for p in range(num_pts):
            th = (p / num_pts) * 2.0 * math.pi
            sin_th = math.sin(th)
            cos_th = math.cos(th)
            
            # Select front or back Z radius
            rad_z = rad_z_front if cos_th >= 0 else rad_z_back
            
            x = rad_x * sin_th
            z = zc + rad_z * cos_th
            
            # Surface perturbations for anatomical realism
            # cos_th > 0 is front face
            if cos_th > 0:
                angle_ratio = abs(sin_th) # 0 is center of face, 1 is side
                
                # Nose bridge & tip
                if feature == "nose" and angle_ratio < 0.28:
                    # sharp triangular nose projection
                    bell = math.cos(angle_ratio / 0.28 * math.pi * 0.5) ** 2
                    nose_profile = math.sin((y - (-10)) / 35.0 * math.pi)
                    z += 22.0 * bell * (nose_profile ** 0.8)
                    
                # Eye sockets (depression on left and right)
                elif feature == "eyes" and 0.20 < angle_ratio < 0.65:
                    eye_t = (angle_ratio - 0.20) / 0.45
                    recess = math.sin(eye_t * math.pi)
                    z -= 11.0 * recess
                    
                # Brow ridge protrusion
                elif feature == "eyes" and y < -22 and angle_ratio < 0.65:
                    brow_t = math.cos(angle_ratio / 0.65 * math.pi * 0.5)
                    z += 7.0 * brow_t
                    
                # Lips and Philtrum
                elif feature == "mouth" and angle_ratio < 0.36:
                    mouth_profile = math.cos(angle_ratio / 0.36 * math.pi * 0.5)
                    # Upper lip protrusion (y ~ 33)
                    if 28 <= y <= 38:
                        z += 9.0 * mouth_profile * math.sin((y - 28) / 10.0 * math.pi)
                    # Lower lip protrusion (y ~ 44)
                    elif 40 <= y <= 50:
                        z += 10.0 * mouth_profile * math.sin((y - 40) / 10.0 * math.pi)
                    # Mouth indentation line (y ~ 39)
                    elif 37 < y < 41:
                        z -= 2.0 * mouth_profile

                # Chin protrusion
                elif feature == "chin" and y < 75 and angle_ratio < 0.35:
                    chin_bell = math.cos(angle_ratio / 0.35 * math.pi * 0.5)
                    z += 12.0 * chin_bell * math.sin((y - 55) / 20.0 * math.pi)
            
            # Base brightness / intensity based on height and frontal normal
            # Front particles are brighter, edges/back fade gracefully
            base_intensity = 0.55 + 0.45 * max(0.0, cos_th)
            # Fade bottom chest
            if y > 115:
                base_intensity *= max(0.0, 1.0 - (y - 115) / 20.0)
            # Highlight forehead / crown
            if -80 < y < -40 and cos_th > 0.4:
                base_intensity *= 1.25
                
            points.append([x, y, z])
            intensities.append(min(1.0, max(0.1, base_intensity)))

    return np.array(points, dtype=np.float32), np.array(intensities, dtype=np.float32)

t0 = time.time()
points, intensities = create_humanoid_head_point_cloud()
print(f"Generated 3D point cloud: {len(points)} points in {time.time()-t0:.4f}s")
print(f"X bounds: [{points[:,0].min():.1f}, {points[:,0].max():.1f}]")
print(f"Y bounds: [{points[:,1].min():.1f}, {points[:,1].max():.1f}]")
print(f"Z bounds: [{points[:,2].min():.1f}, {points[:,2].max():.1f}]")

