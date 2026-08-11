"""FINAL part_18 repair.

The source3MF object 18 is 14 disconnected components, several of which are
EXACTLY coincident duplicate copies (5x arm, 4x long-arm, 2x cube). Unioning
coincident copies creates degenerate sliver folds. Fix: deduplicate to one
copy of each distinct component, then boolean-union them into one clean solid.
"""
import zipfile
import os
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
import manifold3d
from collections import defaultdict

src_3mf = r"C:\Users\elsay\Downloads\3D Model.3mf"
out_stl = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts\print_ready\part_18.stl"

# ---------- extract from3MF ----------
with zipfile.ZipFile(src_3mf, 'r') as z:
    with z.open('3D/3dmodel.model') as f:
        content = f.read()
root = ET.fromstring(content)
ns = {'3mf': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
obj = [o for o in root.findall('.//3mf:object', ns) if o.get('id') == '18'][0]
verts = np.array([[float(v.get('x')), float(v.get('y')), float(v.get('z'))]
                  for v in obj.find('3mf:mesh/3mf:vertices', ns).findall('3mf:vertex', ns)], dtype=np.float64)
tris = np.array([[int(t.get('v1')), int(t.get('v2')), int(t.get('v3'))]
                 for t in obj.find('3mf:mesh/3mf:triangles', ns).findall('3mf:triangle', ns)], dtype=np.int64)

# ---------- connected components ----------
parent = list(range(len(verts)))
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        parent[ra] = rb
for t in tris:
    union(t[0], t[1]); union(t[1], t[2])
comps = defaultdict(list)
for i in range(len(verts)):
    comps[find(i)].append(i)

# ---------- dedup components by geometry signature ----------
def signature(vlist):
    # canonical: sorted rounded vertex coords, then sorted rounded face coords
    cv = np.round(verts[vlist], 4)
    return cv.tobytes()

seen = {}
manifolds = []
n_dup = 0
for vlist in comps.values():
    sig = signature(vlist)
    if sig in seen:
        n_dup += 1
        continue
    seen[sig] = True
    imap = {old: i for i, old in enumerate(vlist)}
    ct = np.array([[imap[a], imap[b], imap[c]] for a, b, c in tris
                   if a in imap and b in imap and c in imap], dtype=np.uint32)
    cv = np.ascontiguousarray(verts[vlist], dtype=np.float32)
    m = manifold3d.Manifold(manifold3d.Mesh(vert_properties=cv, tri_verts=ct))
    if m.status() == manifold3d.Error.NoError:
        manifolds.append(m)

print("components: %d total, %d duplicate copies dropped, %d distinct unioned" % (
    len(comps), n_dup, len(manifolds)))

# ---------- boolean union ----------
result = manifolds[0]
for m in manifolds[1:]:
    result = result + m
print("union: status=%s genus=%d volume=%.1f mm^3  verts=%d tris=%d" % (
    result.status(), result.genus(), result.volume(), result.num_vert(), result.num_tri()))

mo = result.to_mesh()
v = np.array(mo.vert_properties, dtype=np.float64)
t = np.array(mo.tri_verts, dtype=np.int64)

clean = trimesh.Trimesh(vertices=v, faces=t, process=False)
clean.export(out_stl)
print("Wrote:", out_stl, "%.1f KB" % (os.path.getsize(out_stl) / 1024))
