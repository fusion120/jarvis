"""Finalize the QBIT STLs for printing.

- Drops floating micro-shells (single/tiny triangles that are remix noise)
  that make the mesh non-watertight.
- Writes the cleaned, watertight meshes to ./print_ready/ so Mohamed can
  drop them straight into Bambu Studio.
"""
import os, glob
import trimesh
from collections import defaultdict

folder = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts"
out = os.path.join(folder, "print_ready")
os.makedirs(out, exist_ok=True)

def open_edges(mesh):
    ec = defaultdict(int)
    for a, b, c in mesh.faces:
        for u, v in ((a, b), (b, c), (c, a)):
            if u < v:
                ec[(u, v)] += 1
            else:
                ec[(v, u)] += 1
    return sum(1 for n in ec.values() if n != 2)

MIN_SHELL_FACES = 8   # anything smaller than this is remix noise

print("%-14s %8s %9s %8s %10s %10s" % ("file", "faces", "clean", "shells", "dropped", "out"))
for f in sorted(glob.glob(os.path.join(folder, "*.stl"))):
    m = trimesh.load(f, force="mesh", process=True)
    shells = m.split(only_watertight=False)
    big = [s for s in shells if len(s.faces) >= MIN_SHELL_FACES]
    dropped = sum(len(s.faces) for s in shells if len(s.faces) < MIN_SHELL_FACES)

    if len(big) != len(shells):
        merged = trimesh.util.concatenate(big) if big else m
        if merged.is_watertight:
            m = merged
    wt = m.is_watertight
    oe = 0 if wt else open_edges(m)

    if not wt:
        print("%-14s %8d %9s %8s %10d %10s" % (
            os.path.basename(f), len(m.faces), "NO  (%d open)" % oe, "-", "-", "SKIPPED"))
        continue

    name = os.path.join(out, os.path.basename(f))
    m.export(name)
    print("%-14s %8d %9s %8d %10d %10s" % (
        os.path.basename(f), len(m.faces), "YES", len(big), dropped,
        os.path.relpath(name, folder)))
