"""Slicer-compatible check: merge coincident vertices (like Cura/Bambu does)
then count edges. Each edge must appear exactly 2x for watertight."""
import os, glob
import numpy as np
import trimesh
from collections import defaultdict

folder = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts\print_ready"

print("SLICER-COMPATIBLE WATERTIGHT CHECK (vertex merge + edge count)")
print("=" * 70)
print("%-14s %9s %8s %10s %12s %8s" % (
    "file", "faces", "shells", "open_edges", "dims_mm", "OK?"))

for f in sorted(glob.glob(os.path.join(folder, "*.stl"))):
    m = trimesh.load(f, process=True)

    # trimesh with process=True merges vertices — now count edges by index
    edge_count = defaultdict(int)
    for face in m.faces:
        for a, b in [(face[0], face[1]), (face[1], face[2]), (face[2], face[0])]:
            edge_count[(min(a, b), max(a, b))] += 1

    open_edges = sum(1 for c in edge_count.values() if c != 2)
    wt = open_edges == 0
    shells = len(m.split(only_watertight=False))

    mn, mx = m.bounds[0], m.bounds[1]
    dims = "%.1f x %.1f x %.1f" % (mx[0]-mn[0], mx[1]-mn[1], mx[2]-mn[2])

    print("%-14s %9d %8d %10d %12s %8s" % (
        os.path.basename(f), len(m.faces), shells, open_edges, dims,
        "YES" if wt else "NO"))

print("=" * 70)
