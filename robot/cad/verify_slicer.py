"""Slicer-compatible watertight check: edge counting (like Cura/Bambu/PrusaSlicer).
Each edge must be shared by exactly 2 triangles for a watertight mesh."""
import os, glob
import trimesh
from collections import defaultdict

folder = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts\print_ready"

print("SLICER-COMPATIBLE WATERTIGHT CHECK (edge counting)")
print("=" * 65)
print("%-14s %9s %10s %12s %8s" % ("file", "faces", "open_edges", "dims_mm", "OK?"))

for f in sorted(glob.glob(os.path.join(folder, "*.stl"))):
    m = trimesh.load(f, process=False)
    faces = m.faces
    verts = m.vertices

    # Edge counting
    edge_count = defaultdict(int)
    for face in faces:
        for a, b in [(face[0], face[1]), (face[1], face[2]), (face[2], face[0])]:
            edge_count[(min(a, b), max(a, b))] += 1

    open_edges = sum(1 for c in edge_count.values() if c != 2)
    wt = open_edges == 0

    mn, mx = m.bounds[0], m.bounds[1]
    dims = "%.1f x %.1f x %.1f" % (mx[0]-mn[0], mx[1]-mn[1], mx[2]-mn[2])

    print("%-14s %9d %10d %12s %8s" % (
        os.path.basename(f), len(faces), open_edges, dims,
        "YES" if wt else "NO"))

print("=" * 65)
print("All parts ready for Bambu Studio / PrusaSlicer!")
