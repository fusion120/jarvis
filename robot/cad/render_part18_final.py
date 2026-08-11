"""Render the repaired part_18 to confirm arm + camera hole are intact."""
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

stl = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts\print_ready\part_18.stl"
m = trimesh.load(stl, process=True)
print("faces=%d verts=%d volume=%.1f mm^3 (est watertight)" % (
    len(m.faces), len(m.vertices), m.is_watertight and m.volume or 0))

fig = plt.figure(figsize=(15, 5))
for i, (angle, elev) in enumerate([(200, 20), (270, 5), (0, 30)]):
    ax = fig.add_subplot(1, 3, i + 1, projection='3d')
    ax.set_title(['isometric', 'front (x-y)', 'side (y-z)'][i])
    ax.view_init(elev=elev, azim=angle)
    ax.scatter(m.vertices[:, 0], m.vertices[:, 1], m.vertices[:, 2],
               s=0.3, c='steelblue')
    ax.set_xlabel('x'); ax.set_ylabel('y'); ax.set_zlabel('z')
    ax.set_box_aspect([41, 38, 66])
plt.tight_layout()
plt.savefig(r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\render_part18_final.png", dpi=110)
print("saved render_part18_final.png")
