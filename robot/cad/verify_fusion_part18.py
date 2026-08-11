"""Verify the Fusion-exported part_18 tower."""
import os
import trimesh

src = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts\fusion_part_18_tower.stl"
m = trimesh.load(src, process=True)

mn, mx = m.bounds[0], m.bounds[1]
dims = "%.1f x %.1f x %.1f" % (mx[0]-mn[0], mx[1]-mn[1], mx[2]-mn[2])
shells = m.split(only_watertight=False)

print("Fusion-exported part_18:")
print("  faces: %d" % len(m.faces))
print("  vertices: %d" % len(m.vertices))
print("  watertight: %s" % m.is_watertight)
print("  dimensions: %s mm" % dims)
print("  shells: %d" % len(shells))

for i, s in enumerate(shells):
    sb = s.bounds
    sd = "%.1f x %.1f x %.1f" % (sb[1][0]-sb[0][0], sb[1][1]-sb[0][1], sb[1][2]-sb[0][2])
    print("  shell %d: faces=%d watertight=%s dims=%s" % (i, len(s.faces), s.is_watertight, sd))

# Compare with original
orig = trimesh.load(r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts\part_18.stl", process=True)
print("\nOriginal part_18:")
print("  faces: %d, watertight: %s" % (len(orig.faces), orig.is_watertight))
omn, omx = orig.bounds[0], orig.bounds[1]
print("  dimensions: %.1f x %.1f x %.1f mm" % (omx[0]-omn[0], omx[1]-omn[1], omx[2]-omn[2]))

if m.is_watertight:
    print("\n*** FUSION EXPORT IS WATERTIGHT — READY TO PRINT ***")
    out = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts\print_ready\part_18.stl"
    m.export(out)
    print("  saved to", out)
else:
    print("\n*** NOT WATERTIGHT — needs repair ***")
    # Try repair
    fixed = trimesh.repair.fill_holes(m)
    print("  after fill_holes: watertight=%s" % m.is_watertight)
