"""Check the freshly-exported Fusion meshes for part_18."""
import os, glob
import trimesh

base = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts"

for f in sorted(glob.glob(os.path.join(base, "fusion_part18_child*.stl"))):
    m = trimesh.load(f, process=True)
    mn, mx = m.bounds[0], m.bounds[1]
    dims = "%.1f x %.1f x %.1f" % (mx[0]-mn[0], mx[1]-mn[1], mx[2]-mn[2])
    shells = m.split(only_watertight=False)
    print("%s: faces=%d watertight=%s shells=%d dims=%s" % (
        os.path.basename(f), len(m.faces), m.is_watertight, len(shells), dims))
    for i, s in enumerate(shells):
        sb = s.bounds
        sd = "%.1f x %.1f x %.1f" % (sb[1][0]-sb[0][0], sb[1][1]-sb[0][1], sb[1][2]-sb[0][2])
        print("  shell %d: faces=%d watertight=%s dims=%s" % (i, len(s.faces), s.is_watertight, sd))

# Also try merging both children
print("\nMerged:")
files = sorted(glob.glob(os.path.join(base, "fusion_part18_child*.stl")))
meshes = [trimesh.load(f, process=True) for f in files]
merged = trimesh.util.concatenate(meshes)
shells = merged.split(only_watertight=False)
mn, mx = merged.bounds[0], merged.bounds[1]
dims = "%.1f x %.1f x %.1f" % (mx[0]-mn[0], mx[1]-mn[1], mx[2]-mn[2])
print("  faces=%d watertight=%s shells=%d dims=%s" % (len(merged.faces), merged.is_watertight, len(shells), dims))
