"""Salvage part_18 (servo tower): strip floating single-triangle islands,
keep only shells big enough to be real geometry, check watertightness."""
import trimesh
from collections import defaultdict

src = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts\part_18.stl"
m = trimesh.load(src, process=True)
print("loaded:", len(m.faces), "faces,", len(m.split()), "shells")

def open_edges(mesh):
    ec = defaultdict(int)
    for a, b, c in mesh.faces:
        for u, v in ((a, b), (b, c), (c, a)):
            if u < v:
                ec[(u, v)] += 1
            else:
                ec[(v, u)] += 1
    return sum(1 for n in ec.values() if n != 2)

# try progressively more aggressive minimum-shell-size filters
for min_faces in (2, 4, 8, 20, 100, 200):
    kept = [s for s in m.split(only_watertight=False) if len(s.faces) >= min_faces]
    merged = trimesh.util.concatenate(kept) if kept else None
    if merged is None:
        print("min_faces>=%d -> nothing kept" % min_faces)
        continue
    print("min_faces>=%-4d shells=%-4d faces=%d  watertight=%s  open_edges=%d" % (
        min_faces, len(kept), len(merged.faces), merged.is_watertight,
        0 if merged.is_watertight else open_edges(merged)))
