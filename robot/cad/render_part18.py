"""Side-by-side render of original vs cleaned part_18 so we can SEE whether
the tower top survived the noise-removal. Writes PNGs to qbit_parts/."""
import os
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

base = r"C:\Users\elsay\OneDrive\Desktop\jarvis\robot\cad\qbit_parts"
orig = trimesh.load(os.path.join(base, "part_18.stl"), process=True)
clean = trimesh.load(os.path.join(base, "print_ready", "part_18.stl"), process=True)

def draw(ax, m, title, elev, azim):
    ax.set_title(title)
    ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel("Z")
    ax.view_init(elev=elev, azim=azim)
    # center it
    c = m.centroid
    v = m.vertices - c
    pc = Poly3DCollection(v[m.faces], alpha=0.85, linewidths=0.2, edgecolors="black")
    pc.set_facecolor((0.3, 0.55, 0.95))
    ax.add_collection3d(pc)
    ax.set_box_aspect((1, 1, 1))
    lim = max(m.extents) * 0.62
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(-lim, lim)
    ax.axis("off")

for elev, azim, tag in ((20, 45, "iso"), (8, 90, "side"), (45, 0, "front")):
    fig = plt.figure(figsize=(11, 5.5))
    a1 = fig.add_subplot(1, 2, 1, projection="3d")
    draw(a1, orig, "ORIGINAL  (%d faces, 65.6mm tall)" % len(orig.faces), elev, azim)
    a2 = fig.add_subplot(1, 2, 2, projection="3d")
    draw(a2, clean, "CLEANED  (%d faces, 40.3mm tall)" % len(clean.faces), elev, azim)
    fig.suptitle("part_18 servo tower — %s" % tag, fontsize=12)
    fig.tight_layout()
    out = os.path.join(base, "render_%s.png" % tag)
    fig.savefig(out, dpi=110)
    plt.close(fig)
    print("wrote", out)
