"""Render each QBIT part individually for identification."""
import trimesh
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

part_dir = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts\print_ready"
out_dir = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad"

parts = ['part_3', 'part_5', 'part_8', 'part_10', 'part_12', 'part_14', 'part_17', 'part_18']

for pname in parts:
    stl = os.path.join(part_dir, pname + '.stl')
    m = trimesh.load(stl, process=True)
    bbox = m.bounding_box.extents
    vol = m.volume if m.is_watertight else 0
    print(f"{pname}: {len(m.faces)} faces, {len(m.vertices)} verts, "
          f"bbox={bbox[0]:.1f}x{bbox[1]:.1f}x{bbox[2]:.1f}mm, vol={vol:.0f}mm3")

    fig = plt.figure(figsize=(15, 5))
    for i, (angle, elev) in enumerate([(200, 20), (270, 5), (0, 30)]):
        ax = fig.add_subplot(1, 3, i + 1, projection='3d')
        ax.set_title(['isometric', 'front (x-y)', 'side (y-z)'][i])
        ax.view_init(elev=elev, azim=angle)
        ax.scatter(m.vertices[:, 0], m.vertices[:, 1], m.vertices[:, 2],
                   s=0.3, c='steelblue')
        ax.set_xlabel('x'); ax.set_ylabel('y'); ax.set_zlabel('z')
        ax.set_box_aspect(bbox.copy())
    plt.suptitle(f'{pname}  ({len(m.faces)} faces, {bbox[0]:.1f}x{bbox[1]:.1f}x{bbox[2]:.1f}mm)', fontsize=13)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, f'render_{pname}.png'), dpi=100)
    plt.close()
    print(f"  saved render_{pname}.png")
