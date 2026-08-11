"""Extract Object 18 (servo tower) from 3D Model.3mf with proper shared vertices,
producing a clean, watertight STL. The 3MF stores vertex indices (shared), unlike
STL which duplicates vertices per-face — this is why the Fusion import broke it."""
import zipfile
import xml.etree.ElementTree as ET
import struct
import os
import math

src = r"C:\Users\elsay\Downloads\3D Model.3mf"
out_dir = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts\print_ready"
os.makedirs(out_dir, exist_ok=True)

with zipfile.ZipFile(src, 'r') as z:
    with z.open('3D/3dmodel.model') as f:
        content = f.read()

root = ET.fromstring(content)
ns = {'3mf': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}

# Find object 18
target_obj = None
for obj in root.findall('.//3mf:object', ns):
    if obj.get('id') == '18':
        target_obj = obj
        break

if target_obj is None:
    print("Object 18 not found!"); exit(1)

mesh = target_obj.find('3mf:mesh', ns)
vertices = mesh.find('3mf:vertices', ns)
triangles = mesh.find('3mf:triangles', ns)

# Parse vertices
verts = []
for v in vertices.findall('3mf:vertex', ns):
    x = float(v.get('x'))
    y = float(v.get('y'))
    z = float(v.get('z'))
    verts.append((x, y, z))

print("Vertices:", len(verts))

# Parse triangles
tris = []
for t in triangles.findall('3mf:triangle', ns):
    v1 = int(t.get('v1'))
    v2 = int(t.get('v2'))
    v3 = int(t.get('v3'))
    tris.append((v1, v2, v3))

print("Triangles:", len(tris))

# Check connectivity: how many unique vertex indices?
used_verts = set()
for v1, v2, v3 in tris:
    used_verts.update([v1, v2, v3])
print("Unique vertex indices used:", len(used_verts))

# Check if watertight: count open edges
from collections import defaultdict
edge_count = defaultdict(int)
for v1, v2, v3 in tris:
    for a, b in [(v1, v2), (v2, v3), (v3, v1)]:
        key = (min(a, b), max(a, b))
        edge_count[key] += 1

open_edges = sum(1 for c in edge_count.values() if c != 2)
total_edges = len(edge_count)
print("Total unique edges:", total_edges)
print("Open edges:", open_edges)
print("Watertight:", open_edges == 0)

# Bounding box
xs = [v[0] for v in verts]
ys = [v[1] for v in verts]
zs = [v[2] for v in verts]
print("Bounding box: %.1f x %.1f x %.1f mm" % (
    max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs)))

# Compute proper normals using cross product
def compute_normal(v0, v1, v2):
    ax, ay, az = v1[0]-v0[0], v1[1]-v0[1], v1[2]-v0[2]
    bx, by, bz = v2[0]-v0[0], v2[1]-v0[1], v2[2]-v0[2]
    nx = ay*bz - az*by
    ny = az*bx - ax*bz
    nz = ax*by - ay*bx
    ln = math.sqrt(nx*nx + ny*ny + nz*nz)
    if ln > 0:
        return (nx/ln, ny/ln, nz/ln)
    return (0, 0, 0)

# Write binary STL (vertices in mm — 3MF stores in mm)
out_path = os.path.join(out_dir, "part_18.stl")
with open(out_path, 'wb') as f:
    f.write(struct.pack('<80sI', b'', len(tris)))
    for v1, v2, v3 in tris:
        p0 = verts[v1]
        p1 = verts[v2]
        p2 = verts[v3]
        n = compute_normal(p0, p1, p2)
        f.write(struct.pack('<fff', *n))
        f.write(struct.pack('<fff', *p0))
        f.write(struct.pack('<fff', *p1))
        f.write(struct.pack('<fff', *p2))
        f.write(struct.pack('<H', 0))

print("\nWrote:", out_path)
print("File size:", os.path.getsize(out_path), "bytes")

# Verify with trimesh
import trimesh
m = trimesh.load(out_path, process=True)
mn, mx = m.bounds[0], m.bounds[1]
print("\nVerification:")
print("  faces:", len(m.faces))
print("  vertices:", len(m.vertices))
print("  watertight:", m.is_watertight)
print("  dimensions: %.1f x %.1f x %.1f mm" % (mx[0]-mn[0], mx[1]-mn[1], mx[2]-mn[2]))
print("  shells:", len(m.split(only_watertight=False)))
