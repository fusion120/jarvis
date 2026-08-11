"""Export part_18 without trimesh vertex processing.
The edge-count check on raw3MF indices showed 0 open edges.
Bambu Studio / PrusaSlicer use edge-counting too, so this should work."""
import zipfile
import xml.etree.ElementTree as ET
import os
import numpy as np
import trimesh
import struct
import math

src = r"C:\Users\elsay\Downloads\3D Model.3mf"
out_dir = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts\print_ready"

with zipfile.ZipFile(src, 'r') as z:
    with z.open('3D/3dmodel.model') as f:
        content = f.read()

root = ET.fromstring(content)
ns = {'3mf': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}

target_obj = None
for obj in root.findall('.//3mf:object', ns):
    if obj.get('id') == '18':
        target_obj = obj
        break

mesh_el = target_obj.find('3mf:mesh', ns)
vertices_el = mesh_el.find('3mf:vertices', ns)
triangles_el = mesh_el.find('3mf:triangles', ns)

raw_verts = []
for v in vertices_el.findall('3mf:vertex', ns):
    raw_verts.append([float(v.get('x')), float(v.get('y')), float(v.get('z'))])

faces = []
for t in triangles_el.findall('3mf:triangle', ns):
    faces.append([int(t.get('v1')), int(t.get('v2')), int(t.get('v3'))])

print("%d vertices, %d faces" % (len(raw_verts), len(faces)))

# Write binary STL with original vertices (no dedup, no processing)
# This preserves the exact mesh topology from the 3MF
out_path = os.path.join(out_dir, "part_18.stl")

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

with open(out_path, 'wb') as f:
    f.write(struct.pack('<80sI', b'', len(faces)))
    for v1, v2, v3 in faces:
        p0 = raw_verts[v1]
        p1 = raw_verts[v2]
        p2 = raw_verts[v3]
        n = compute_normal(p0, p1, p2)
        f.write(struct.pack('<fff', *n))
        f.write(struct.pack('<fff', *p0))
        f.write(struct.pack('<fff', *p1))
        f.write(struct.pack('<fff', *p2))
        f.write(struct.pack('<H', 0))

print("Wrote:", out_path)
print("Size:", os.path.getsize(out_path), "bytes")

# Verify by edge counting (like a slicer would)
from collections import defaultdict
edge_count = defaultdict(int)
for v1, v2, v3 in faces:
    for a, b in [(v1, v2), (v2, v3), (v3, v1)]:
        edge_count[(min(a, b), max(a, b))] += 1

open_edges = sum(1 for c in edge_count.values() if c != 2)
print("Edge verification: %d open / %d total" % (open_edges, len(edge_count)))
print("Watertight (slicer-compatible):", open_edges == 0)

# Also try trimesh with process=False
m = trimesh.Trimesh(vertices=np.array(raw_verts), faces=np.array(faces), process=False)
print("\ntrimesh process=False: watertight=%s" % m.is_watertight)
