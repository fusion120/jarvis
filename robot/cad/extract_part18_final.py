"""Extract Object 18 from 3D Model.3mf, properly deduplicate vertices,
and export a clean watertight STL."""
import zipfile
import xml.etree.ElementTree as ET
import os
import numpy as np
import trimesh
from collections import defaultdict

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

# Parse
raw_verts = []
for v in vertices_el.findall('3mf:vertex', ns):
    raw_verts.append([float(v.get('x')), float(v.get('y')), float(v.get('z'))])
raw_verts = np.array(raw_verts, dtype=np.float64)

faces = []
for t in triangles_el.findall('3mf:triangle', ns):
    faces.append([int(t.get('v1')), int(t.get('v2')), int(t.get('v3'))])
faces = np.array(faces, dtype=np.int64)

print("Raw: %d vertices, %d faces" % (len(raw_verts), len(faces)))

# Properly deduplicate: round to 6 decimal places, then unique
rounded = np.round(raw_verts, decimals=6)
unique_verts, inverse = np.unique(rounded, axis=0, return_inverse=True)
print("After dedup: %d unique vertices" % len(unique_verts))

# Remap face indices
new_faces = inverse[faces]
print("Remapped faces shape:", new_faces.shape)

# Build trimesh
m = trimesh.Trimesh(vertices=unique_verts, faces=new_faces, process=True)

mn, mx = m.bounds[0], m.bounds[1]
shells = m.split(only_watertight=False)
print("Result: %d vertices, %d faces, watertight=%s, shells=%d" % (
    len(m.vertices), len(m.faces), m.is_watertight, len(shells)))
print("Dimensions: %.1f x %.1f x %.1f mm" % (mx[0]-mn[0], mx[1]-mn[1], mx[2]-mn[2]))

if len(shells) <= 20:
    for i, s in enumerate(shells):
        sb = s.bounds
        sd = "%.1f x %.1f x %.1f" % (sb[1][0]-sb[0][0], sb[1][1]-sb[0][1], sb[1][2]-sb[0][2])
        print("  shell %d: faces=%d watertight=%s dims=%s" % (i, len(s.faces), s.is_watertight, sd))

if m.is_watertight:
    out_path = os.path.join(out_dir, "part_18.stl")
    m.export(out_path)
    print("\n*** WATERTIGHT — saved to", out_path, "***")
    print("    file size:", os.path.getsize(out_path), "bytes")
else:
    print("\nNot watertight after dedup. Trying fill_holes...")
    trimesh.repair.fill_holes(m)
    print("  after fill_holes:", m.is_watertight)
    if m.is_watertight:
        out_path = os.path.join(out_dir, "part_18.stl")
        m.export(out_path)
        print("  saved to", out_path)
    else:
        # Count open edges manually to verify
        edge_count = defaultdict(int)
        for f in new_faces:
            for a, b in [(f[0], f[1]), (f[1], f[2]), (f[2], f[0])]:
                edge_count[(min(a,b), max(a,b))] += 1
        open_e = sum(1 for c in edge_count.values() if c != 2)
        print("  manual edge count: open=%d / total=%d" % (open_e, len(edge_count)))
        if open_e == 0:
            print("  Edge-count confirms watertight. Saving despite trimesh report...")
            out_path = os.path.join(out_dir, "part_18.stl")
            m.export(out_path)
            print("  saved to", out_path)
