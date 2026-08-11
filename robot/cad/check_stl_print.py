"""Definitive 3D-print readiness check for the QBIT STLs (trimesh).

Loads each STL the way a slicer would (merge duplicate vertices), reports
watertightness + open-edge count, and --repair writes hole-filled copies
to ./print_ready/ for dropping straight into Bambu Studio.
"""
import os, sys, glob
from collections import defaultdict
import trimesh

folder = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts"
out = os.path.join(folder, "print_ready")
repair = "--repair" in sys.argv
if repair:
    os.makedirs(out, exist_ok=True)

def open_edges(m):
    ec = defaultdict(int)
    for a, b, c in m.faces:
        for u, v in ((a, b), (b, c), (c, a)):
            if u < v:
                ec[(u, v)] += 1
            else:
                ec[(v, u)] += 1
    return sum(1 for n in ec.values() if n != 2)

print("%-14s %8s %10s %9s %9s %12s" % ("file", "faces", "watertight", "open_edg", "added", "dims_mm"))
for f in sorted(glob.glob(os.path.join(folder, "*.stl"))):
    m = trimesh.load(f, force="mesh", process=True)   # merge dup verts like a slicer
    n0 = len(m.faces)
    wt = m.is_watertight
    oe = open_edges(m) if not wt else 0

    added = 0
    if repair and not wt:
        fixed = m.copy()
        try:
            trimesh.repair.fill_holes(fixed)
        except Exception as e:
            print("  !! repair failed on %s: %s" % (os.path.basename(f), e))
            continue
        if fixed.is_watertight:
            added = len(fixed.faces) - n0
            fixed.export(os.path.join(out, os.path.basename(f)))
            m = fixed
            wt = True
            oe = 0

    mn = m.bounds[0]
    mx = m.bounds[1]
    dims = "%.1f x %.1f x %.1f" % (mx[0]-mn[0], mx[1]-mn[1], mx[2]-mn[2])
    status = "OK" if wt and added < max(300, n0 // 4) else "CHECK"
    print("%-14s %8d %10s %9d %9d %12s  %s" % (
        os.path.basename(f), n0, "YES" if wt else "NO", oe, added, dims, status))
    if repair and wt and added == 0 and not os.path.exists(os.path.join(out, os.path.basename(f))):
        # already watertight — still copy into print_ready so the folder is complete
        m.export(os.path.join(out, os.path.basename(f)))
