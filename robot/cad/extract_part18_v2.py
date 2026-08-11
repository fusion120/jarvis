"""Extract Object 18 (servo tower) from 3D Model.3mf using trimesh's Trimesh constructor
with shared vertices — avoids STL's per-face vertex duplication."""
import zipfile
import xml.etree.ElementTree as ET
import os
import numpy as np
import trimesh

src = r"C:\Users\elsay\Downloads\3D Model.3mf"
out_dir = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts\print_ready"

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

mesh = target_obj.find('3mf:mesh', ns)
vertices_el = mesh.find('3mf:vertices', ns)
triangles_el = mesh.find('3mf:triangles', ns)

# Parse into numpy arrays
verts = []
for v in vertices_el.findall('3mf:vertex', ns):
    verts.append([float(v.get('x')), float(v.get('y')), float(v.get('z'))])
verts = np.array(verts, dtype=np.float64)

faces = []
for t in triangles_el.findall('3mf:triangle', ns):
    faces.append([int(t.get('v1')), int(t.get('v2')), int(t.get('v3'))])
faces = np.array(faces, dtype=np.int64)

print("Raw3MF data: %d vertices, %d faces" % (len(verts), len(faces)))

# Build trimesh directly from indexed data (no vertex duplication!)
m = trimesh.Trimesh(vertices=verts, faces=faces, process=True)

mn, mx = m.bounds[0], m.bounds[1]
shells = m.split(only_watertight=False)

print("trimesh result:")
print("  vertices:", len(m.vertices))
print("  faces:", len(m.faces))
print("  watertight:", m.is_watertight)
print("  dimensions: %.1f x %.1f x %.1f mm" % (mx[0]-mn[0], mx[1]-mn[1], mx[2]-mn[2]))
print("  shells:", len(shells))

if len(shells) <= 20:
    for i, s in enumerate(shells):
        sb = s.bounds
        print("  shell %d: faces=%d watertight=%s" % (i, len(s.faces), s.is_watertight))

if m.is_watertight:
    out_path = os.path.join(out_dir, "part_18.stl")
    m.export(out_path)
    print("\n*** WATERTIGHT — saved to", out_path, "***")
    print("    file size:", os.path.getsize(out_path), "bytes")
else:
    print("\nNot watertight — trying fill_holes...")
    trimesh.repair.fill_holes(m)
    print("  after fill_holes:", m.is_watertight)
    if m.is_watertight:
        out_path = os.path.join(out_dir, "part_18.stl")
        m.export(out_path)
        print("  saved to", out_path)
    else:
        # Try with process=False to avoid vertex merging
        m2 = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
        print("\n  process=False: watertight=%s" % m2.is_watertight)
        # Count open edges manually
        from collections import defaultdict
        edge_count = defaultdict(int)
        for f in faces:
            for a, b in [(f[0], f[1]), (f[1], f[2]), (f[2], f[0])]:
                edge_count[(min(a,b), max(a,b))] += 1
        open_e = sum(1 for c in edge_count.values() if c != 2)
        print("  manual edge check: open_edges=%d / %d" % (open_e, len(edge_count)))
        if open_e == 0:
            # Manually merge duplicates for export
            print("  Mesh IS watertight by edge count. Exporting...")
            out_path = os.path.join(out_dir, "part_18.stl")
            m2.export(out_path)
            print("  saved to", out_path)
            # Verify
            v = trimesh.load(out_path, process=True)
            print("  reloaded: watertight=%s faces=%d" % (v.is_watertight, len(v.faces)))
