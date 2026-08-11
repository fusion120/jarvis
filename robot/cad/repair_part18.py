"""Try to repair part_18 by merging coincident vertices at various tolerances,
then check if the arm triangles reconnect into proper topology."""
import trimesh
import numpy as np

src = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts\part_18.stl"
m = trimesh.load(src, process=False)  # don't merge vertices yet

print("Original: %d faces, %d vertices" % (len(m.faces), len(m.vertices)))
print("  bounds:", m.bounds.tolist())

# Try different merge tolerances (in mm, since original STL is in mm)
for tol in [0.001, 0.01, 0.05, 0.1, 0.5, 1.0]:
    copy = m.copy()
    # Merge vertices within tolerance
    trimesh.repair.fill_holes(copy)
    # Use trimesh's simplify to merge close vertices
    # Actually, let's use a manual approach
    verts = copy.vertices.copy()
    faces = copy.faces.copy()

    # Find pairs of vertices within tolerance
    from scipy.spatial import cKDTree
    tree = cKDTree(verts)
    pairs = tree.query_pairs(tol)

    if not pairs:
        print("\ntol=%.3f: no pairs found" % tol)
        continue

    print("\ntol=%.3f: %d vertex pairs to merge" % (tol, len(pairs)))

    # Union-find to group vertices
    parent = list(range(len(verts)))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for a, b in pairs:
        union(a, b)

    # Build mapping: each vertex -> its group representative
    groups = {}
    new_idx = {}
    counter = 0
    for i in range(len(verts)):
        root = find(i)
        if root not in groups:
            groups[root] = []
            new_idx[root] = counter
            counter += 1
        groups[root].append(i)

    # New vertices: average of each group
    new_verts = np.zeros((len(groups), 3))
    for root, members in groups.items():
        new_verts[new_idx[root]] = verts[members].mean(axis=0)

    # Remap faces
    new_faces = faces.copy()
    for i in range(len(verts)):
        new_faces[faces == i] = new_idx[find(i)]

    # Check for degenerate faces (all 3 vertices same)
    valid = np.array([len(set(f)) >= 3 for f in new_faces])
    degenerate = (~valid).sum()

    repaired = trimesh.Trimesh(vertices=new_verts, faces=new_faces[valid], process=True)
    shells = repaired.split(only_watertight=False)
    big = [s for s in shells if len(s.faces) >= 8]
    small_count = len(shells) - len(big)
    print("  after merge: %d faces (%d degenerate removed), %d shells (%d big, %d small)" % (
        len(repaired.faces), degenerate, len(shells), len(big), small_count))

    if big:
        mb = trimesh.util.concatenate(big)
        mn, mx = mb.bounds[0], mb.bounds[1]
        print("  big shells: watertight=%s dims=%.1f x %.1f x %.1f mm" % (
            mb.is_watertight, mx[0]-mn[0], mx[1]-mn[1], mx[2]-mn[2]))
