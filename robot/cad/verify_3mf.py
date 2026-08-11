"""Verify the QBIT_body.3mf — check all parts for watertightness."""
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict

src = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts\QBIT_body.3mf"

with zipfile.ZipFile(src, 'r') as z:
    with z.open('3D/3dmodel.model') as f:
        content = f.read()

root = ET.fromstring(content)
ns = {'3mf': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}

print("QBIT_body.3mf verification")
print("=" * 65)

for obj in root.findall('.//3mf:object', ns):
    name = obj.get('name', 'unnamed')
    mesh = obj.find('3mf:mesh', ns)
    if mesh is None:
        continue

    verts_el = mesh.find('3mf:vertices', ns)
    tris_el = mesh.find('3mf:triangles', ns)

    verts = []
    for v in verts_el.findall('3mf:vertex', ns):
        verts.append([float(v.get('x')), float(v.get('y')), float(v.get('z'))])

    faces = []
    for t in tris_el.findall('3mf:triangle', ns):
        faces.append((int(t.get('v1')), int(t.get('v2')), int(t.get('v3'))))

    # Edge count on raw indices (3MF has shared vertices)
    edge_count = defaultdict(int)
    for v1, v2, v3 in faces:
        for a, b in [(v1, v2), (v2, v3), (v3, v1)]:
            edge_count[(min(a, b), max(a, b))] += 1

    open_edges = sum(1 for c in edge_count.values() if c != 2)

    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    zs = [v[2] for v in verts]
    dims = "%.1f x %.1f x %.1f" % (max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))

    print("%-12s %6d faces  %5d verts  open=%-4d  %s  %s" % (
        name, len(faces), len(verts), open_edges, dims,
        "WATERTIGHT" if open_edges == 0 else "BROKEN"))

print("=" * 65)
