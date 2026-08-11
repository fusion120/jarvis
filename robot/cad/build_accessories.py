"""
JARVIS EV — accessory parts (speaker bracket + monitor camera clip)
====================================================================
Builds two parts in SolidWorks via COM automation:
  speaker_bracket.SLDPRT — clips to QBIT body back, holds 28mm speaker
  camera_clip.SLDPRT     — hooks over monitor top, holds webcam

Run with SolidWorks open + logged in.
"""
import os, sys, time, glob

try:
    import win32com.client
except ImportError:
    sys.exit("pip install pywin32")


def log(msg):
    print(msg, flush=True)


def find_template():
    root = os.environ.get("ProgramData", r"C:\ProgramData")
    for dirpath, dirnames, filenames in os.walk(root):
        if dirpath.count(os.sep) - root.count(os.sep) > 4:
            dirnames[:] = []
            continue
        for f in filenames:
            if f.lower() == "part.prtdot":
                return os.path.join(dirpath, f)
        dirnames[:] = [d for d in dirnames if d.lower() != "data"]
    return None


def connect():
    try:
        sw = win32com.client.GetActiveObject("SldWorks.Application")
        log("connected to running SolidWorks")
    except Exception:
        sw = win32com.client.Dispatch("SldWorks.Application")
        time.sleep(3)
        log("launched new SolidWorks instance")
    sw.Visible = True
    return sw


def select_plane(model, name):
    return model.SelectByID(name, "PLANE", 0, 0, 0)


def start_sketch(model, plane):
    if not select_plane(model, plane):
        raise RuntimeError(f"could not select {plane}")
    skm = model.SketchManager
    skm.InsertSketch(True)
    return skm


def end_sketch(model):
    model.SketchManager.InsertSketch(True)


def extrude(model, depth):
    model.FeatureManager.FeatureExtrusion2(
        True, False, False, 0, 0, float(depth), 0,
        False, False, False, False, 0, 0, False,
        True, False, False, True, True, True, 0, 0, 0)


def cut_through(model, both=False):
    t1 = 2 if both else 1
    model.FeatureManager.FeatureCut(
        True, False, False, t1, 0, 0, 0,
        False, False, False, False, 0, 0,
        False, False, False, False, True, True, True)


def cut_depth(model, depth):
    model.FeatureManager.FeatureCut(
        True, False, False, 0, 0, float(depth), 0,
        False, False, False, False, 0, 0,
        False, False, False, False, True, True, True)


def new_part(sw, template):
    model = sw.NewDocument(template, 0, 0, 0)
    if not model:
        raise RuntimeError("NewDocument failed")
    time.sleep(0.5)
    return model


def close_all(sw):
    try:
        for d in sw.GetDocuments():
            t = getattr(d, "GetTitle", None)
            title = t() if callable(t) else t
            if title:
                try:
                    sw.CloseDoc(str(title))
                except Exception:
                    pass
    except Exception:
        pass


# ── SPEAKER BRACKET ─────────────────────────────────────────
# Clips to the back of the QBIT body. Holds a 28mm speaker.
# Plate 45x55x3, speaker hole 28mm centered, 2 clip tabs, 2 M2 screws.

def build_speaker_bracket(sw, template):
    log("  building speaker_bracket.SLDPRT")
    model = new_part(sw, template)
    out = os.path.join(OUT, "speaker_bracket.SLDPRT")

    # plate 45 x 55 x 3
    skm = start_sketch(model, "Front Plane")
    skm.CreateCornerRectangle(-22.5, -27.5, 0, 22.5, 27.5, 0)
    end_sketch(model)
    extrude(model, 3)

    # speaker hole 28mm centered
    skm = start_sketch(model, "Front Plane")
    skm.CreateCircle(0, 0, 0, 14, 0, 0)
    end_sketch(model)
    cut_through(model)

    # 2 clip tabs on left/right edges (5mm wide x 3mm deep x 10mm tall)
    # tabs rise from the front face (+Z direction)
    skm = start_sketch(model, "Front Plane")
    skm.CreateCornerRectangle(-22.5, -5, 0, -17.5, 5, 0)   # left tab
    skm.CreateCornerRectangle(17.5, -5, 0, 22.5, 5, 0)      # right tab
    end_sketch(model)
    extrude(model, 10)   # 10mm tall clips

    # 2 M2 screw holes through plate (near bottom corners)
    skm = start_sketch(model, "Front Plane")
    skm.CreateCircle(-14, -20, 0, -13, -20, 0)   # left screw
    skm.CreateCircle(14, -20, 0, 15, -20, 0)      # right screw
    end_sketch(model)
    cut_through(model)

    model.SaveAs3(out, 0, 2)
    log(f"  saved {out}")


# ── MONITOR CAMERA CLIP ─────────────────────────────────────
# L-shaped hook + shelf. Hooks over monitor top (10-15mm thick).
# Vertical: 30w x 30h x 3mm with 12mm x 16mm slot.
# Horizontal shelf: 30w x 20d x 3mm for the webcam.

def build_camera_clip(sw, template):
    log("  building camera_clip.SLDPRT")
    model = new_part(sw, template)
    out = os.path.join(OUT, "camera_clip.SLDPRT")

    # L-shape: vertical wall + horizontal shelf = one extrusion of the L profile
    # Profile in XZ plane: vertical 30h x 3mm thick, shelf 20d x 3mm thick at bottom
    # Sketch on Front Plane (XY), extrude 3mm in Z
    skm = start_sketch(model, "Front Plane")
    # L profile: vertical bar + horizontal bar
    skm.CreateCornerRectangle(-15, 0, 0, 15, 30, 0)          # vertical wall 30w x 30h
    skm.CreateCornerRectangle(-15, -3, 0, 15, 0, 0)          # shelf 30w x 3d (below the wall)
    end_sketch(model)
    extrude(model, 3)

    # monitor slot: cut through the vertical wall (12mm wide x 16mm deep from top)
    # centered horizontally, starting 14mm from bottom (so the hook lip is 16mm)
    skm = start_sketch(model, "Front Plane")
    skm.CreateCornerRectangle(-6, 14, 0, 6, 30.1, 0)    # slot: 12mm wide, through top
    end_sketch(model)
    cut_through(model)

    # webcam hole in the shelf (circular, 15mm diameter, centered on shelf)
    skm = start_sketch(model, "Front Plane")
    skm.CreateCircle(0, -1.5, 0, 7.5, -1.5, 0)
    end_sketch(model)
    cut_through(model)

    model.SaveAs3(out, 0, 2)
    log(f"  saved {out}")


# ── MAIN ─────────────────────────────────────────────────────
if __name__ == "__main__":
    OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "solidworks_out")
    os.makedirs(OUT, exist_ok=True)

    template = find_template()
    if not template:
        sys.exit("Part.prtdot not found")
    log(f"template: {template}")

    sw = connect()
    close_all(sw)

    for name, fn in [("speaker_bracket", build_speaker_bracket),
                     ("camera_clip", build_camera_clip)]:
        log(f"\n{name}:")
        try:
            fn(sw, template)
        except Exception as e:
            log(f"  FAILED: {e}")

    log("\ndone")
