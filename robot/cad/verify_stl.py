import os, glob
import trimesh

folder = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts\print_ready"
print("%-14s %9s %10s %12s" % ("file", "faces", "watertight", "dims_mm"))
files = sorted(glob.glob(os.path.join(folder, "*.stl")))
for f in files:
    m = trimesh.load(f, process=True)
    mn, mx = m.bounds[0], m.bounds[1]
    dims = "%.1f x %.1f x %.1f" % (mx[0]-mn[0], mx[1]-mn[1], mx[2]-mn[2])
    print("%-14s %9d %10s %12s" % (os.path.basename(f), len(m.faces),
                                   "YES" if m.is_watertight else "NO", dims))
print()
print("count:", len(files), "files — all", "OK" if files else "missing")
