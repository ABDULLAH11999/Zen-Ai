import math
import time
import numpy as np
from PIL import Image, ImageDraw

# 1. Parse OBJ file (vertices and triangle faces)
def load_obj(path):
    verts = []
    faces = []
    with open(path, "r") as f:
        for line in f:
            if line.startswith("v "):
                p = line.strip().split()
                # OBJ Y is up, Z is depth
                verts.append([float(p[1]), float(p[2]), float(p[3])])
            elif line.startswith("f "):
                p = line.strip().split()
                # Extract vertex indices (1-based to 0-based)
                v_idx = [int(x.split("/")[0]) - 1 for x in p[1:]]
                # Triangulate polygon if > 3 vertices
                for i in range(1, len(v_idx) - 1):
                    faces.append([v_idx[0], v_idx[i], v_idx[i + 1]])
    return np.array(verts, dtype=np.float32), np.array(faces, dtype=np.int32)

print("Loading head_mesh.obj...")
verts, faces = load_obj("models/head_mesh.obj")
print(f"Loaded {len(verts)} vertices, {len(faces)} triangles.")

# Normalize vertices to standard size (e.g. scale to height ~220 px)
# Y in OBJ goes from -1 to +1 (chin to cranium top)
# In computer graphics canvas, top is negative Y, chin is positive Y
# So we invert Y: y_canvas = -y_obj
verts_scaled = verts.copy()
# Invert Y so cranium top is negative, chin is positive
verts_scaled[:, 1] = -verts_scaled[:, 1]
# Scale to 110 units radius
scale = 110.0
verts_scaled *= scale

# Center mesh
mean_center = verts_scaled.mean(axis=0)
verts_scaled[:, 0] -= mean_center[0]
verts_scaled[:, 1] -= mean_center[1]

# 2. Slice the 3D mesh with horizontal planes to get scanline rings
def slice_mesh_to_scanlines(verts, faces, num_slices=85):
    y_min, y_max = verts[:, 1].min(), verts[:, 1].max()
    # Add slight margin
    y_levels = np.linspace(y_min + 2, y_max - 2, num_slices)
    
    scanline_pts = [] # list of (x, y, z, intensity)
    
    # Pre-extract face vertices
    f_v0 = verts[faces[:, 0]]
    f_v1 = verts[faces[:, 1]]
    f_v2 = verts[faces[:, 2]]
    
    for y_plane in y_levels:
        # Find intersecting triangle edges
        # Edge 0-1, 1-2, 2-0
        edges = [(f_v0, f_v1), (f_v1, f_v2), (f_v2, f_v0)]
        seg_pts = []
        for e_a, e_b in edges:
            y_a = e_a[:, 1]
            y_b = e_b[:, 1]
            # Check which edges cross y_plane
            cross = (y_a <= y_plane) & (y_b > y_plane) | (y_b <= y_plane) & (y_a > y_plane)
            if np.any(cross):
                a_cross = e_a[cross]
                b_cross = e_b[cross]
                t = (y_plane - a_cross[:, 1]) / (b_cross[:, 1] - a_cross[:, 1])
                t = t[:, np.newaxis]
                inter_pts = a_cross + t * (b_cross - a_cross)
                seg_pts.append(inter_pts)
                
        if seg_pts:
            all_inter = np.vstack(seg_pts)
            # Remove duplicate points
            # Sample points along the contour
            # Sort points by angle around center in X-Z plane
            angles = np.arctan2(all_inter[:, 2], all_inter[:, 0])
            sorted_order = np.argsort(angles)
            ring = all_inter[sorted_order]
            
            # Interpolate to dense equidistant points along the ring (e.g. 70 points per ring)
            num_ring_pts = 75
            t_orig = np.linspace(0, 1, len(ring))
            t_dense = np.linspace(0, 1, num_ring_pts)
            
            x_dense = np.interp(t_dense, t_orig, ring[:, 0])
            z_dense = np.interp(t_dense, t_orig, ring[:, 2])
            y_dense = np.full_like(x_dense, y_plane)
            
            for px, py, pz in zip(x_dense, y_dense, z_dense):
                # Intensity based on Z (front face is brighter)
                # Front face has positive Z
                inten = 0.50 + 0.50 * max(0.0, pz / 60.0)
                scanline_pts.append([px, py, pz, inten])
                
    return np.array(scanline_pts, dtype=np.float32)

t0 = time.time()
points = slice_mesh_to_scanlines(verts_scaled, faces, num_slices=90)
print(f"Generated {len(points)} 3D scanline points in {time.time()-t0:.4f}s")
print(f"X bounds: [{points[:,0].min():.1f}, {points[:,0].max():.1f}]")
print(f"Y bounds: [{points[:,1].min():.1f}, {points[:,1].max():.1f}]")
print(f"Z bounds: [{points[:,2].min():.1f}, {points[:,2].max():.1f}]")

# Save points to a fast numpy binary cache
np.save("models/head_scanlines.npy", points)
print("Saved models/head_scanlines.npy successfully!")

