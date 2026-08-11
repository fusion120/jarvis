"""Extract meshes from 3D Model.3mf using the3mf library (reads triangulated_data properly)."""
import zipfile
import os
import xml.etree.ElementTree as ET

src = r"C:\Users\elsay\Downloads\3D Model.3mf"

print("Reading:", src)
print("Size:", os.path.getsize(src), "bytes")

with zipfile.ZipFile(src, 'r') as z:
    print("Files in archive:")
    for name in z.namelist():
        print(f"  {name} ({z.getinfo(name).file_size} bytes)")

    # Read the model
    with z.open('3D/3dmodel.model') as f:
        content = f.read()

# Parse XML
root = ET.fromstring(content)
ns = {'3mf': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}

# Find all objects
objects = root.findall('.//3mf:object', ns)
print(f"\nFound {len(objects)} objects")

for obj in objects:
    obj_id = obj.get('id')
    obj_name = obj.get('name', 'unnamed')
    mesh = obj.find('3mf:mesh', ns)
    if mesh is None:
        print(f"  Object {obj_id} ({obj_name}): no mesh")
        continue

    vertices = mesh.find('3mf:vertices', ns)
    triangles = mesh.find('3mf:triangles', ns)

    vert_count = len(vertices.findall('3mf:vertex', ns)) if vertices is not None else 0
    tri_count = len(triangles.findall('3mf:triangle', ns)) if triangles is not None else 0

    print(f"  Object {obj_id} ({obj_name}): {vert_count} vertices, {tri_count} triangles")

    # Get triangle vertex indices to check for connectivity
    if triangles is not None:
        tri_verts = set()
        for tri in triangles.findall('3mf:triangle', ns):
            v1 = int(tri.get('v1'))
            v2 = int(tri.get('v2'))
            v3 = int(tri.get('v3'))
            tri_verts.update([v1, v2, v3])
        print(f"    unique vertex indices used: {len(tri_verts)} / {vert_count}")
        if len(tri_verts) < vert_count:
            print(f"    WARNING: {vert_count - len(tri_verts)} vertices are UNUSED (orphaned)")
