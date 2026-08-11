"""Render the final part_18 to confirm the arm is present."""
import os
import trimesh
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

src = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts\print_ready\part_18.stl"
m = trimesh.load(src, process=False)  # keep original vertices

fig = plt.figure(figsize=(14, 5))
for col, (elev, azim, title) in enumerate([
    (20, 45, "isometric"),
    (8, 90, "side"),
    (0, 0, "front"),
]):
    ax = fig.add_subplot(1, 3, col + 1, projection="3d")
    c = m.centroid
    v = m.vertices - c
    # Use faces directly (no re-indexing)
    triangles = v[m.faces]
    pc = Poly3DCollection(triangles, alpha=0.85, linewidths=0.15, edgecolors="black")
    pc.set_facecolor((0.3, 0.55, 0.95))
    ax.add_collection3d(pc)
    ax.view_init(elev=elev, azim=azim)
    ax.set_box_aspect((1, 1, 1))
    lim = max(m.extents) * 0.62
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(-lim, lim)
    ax.set_title(title, fontsize=10)
    ax.axis("off")

mn, mx = m.bounds[0], m.bounds[1]
fig.suptitle("part_18 servo tower — FINAL  (%d faces, %.1f x %.1f x %.1f mm)" % (
    len(m.faces), mx[0]-mn[0], mx[1]-mn[1], mx[2]-mn[2]), fontsize=12)
fig.tight_layout()
out = os.path.join(os.path.dirname(src), "..", "render_final_part18.png")
fig.savefig(out, dpi=110)
plt.close(fig)
print("wrote", out)
