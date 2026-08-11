"""Render JUST the dropped (single-face) triangles from part_18,
with the clean body in gray underneath. Shows whether the dropped
triangles form the tower arm or are truly garbage."""
import os
import trimesh
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

base = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts"
orig = trimesh.load(os.path.join(base, "part_18.stl"), process=True)
clean = trimesh.load(os.path.join(base, "print_ready", "part_18.stl"), process=True)

# get dropped faces: faces in original but not in clean
# since clean is a subset of big shells, find faces belonging to small shells
shells = orig.split(only_watertight=False)
big_faces = set()
small_faces = set()
for s in shells:
    idx = frozenset(map(tuple, s.faces.tolist()))
    if len(s.faces) >= 8:
        big_faces.update(idx)
    else:
        small_faces.update(idx)

# map triangle vertex coords
vert = orig.vertices
drop_verts = [vert[list(t)] for t in small_faces]

fig = plt.figure(figsize=(12, 6))
for col, (elev, azim) in enumerate([(20, 45), (8, 180)]):
    ax = fig.add_subplot(1, 2, col + 1, projection="3d")
    # clean body in gray
    c = orig.centroid
    v = (clean.vertices - c)
    pc_body = Poly3DCollection(v[clean.faces], alpha=0.25, linewidths=0.1,
                               edgecolors="gray", facecolors=(0.85, 0.85, 0.85))
    ax.add_collection3d(pc_body)
    # dropped triangles in RED
    if drop_verts:
        v_drop = np.array(drop_verts) - c
        pc_drop = Poly3DCollection(v_drop, alpha=0.9, linewidths=0.3,
                                   edgecolors=(0.8, 0.15, 0.15),
                                   facecolors=(0.95, 0.25, 0.2))
        ax.add_collection3d(pc_drop)
    ax.view_init(elev=elev, azim=azim)
    ax.set_box_aspect((1, 1, 1))
    lim = max(orig.extents) * 0.62
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(-lim, lim)
    ax.set_title("view %d" % (col + 1))
    ax.axis("off")

fig.suptitle("RED = dropped 11,210 faces | GRAY = cleaned body", fontsize=13)
fig.tight_layout()
out = os.path.join(base, "render_dropped.png")
fig.savefig(out, dpi=110)
plt.close(fig)
print("wrote", out)
