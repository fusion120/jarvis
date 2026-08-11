"""
JARVIS BUDDY — build the frame parts in SolidWorks via its Automation API.
====================================================================
Creates three part files from the spec in robot/docs/BUILD_SPEC.md:
    base.SLDPRT  90 x 60 x 5  (4x M3 corners, 2x M2 servo flange)
    neck.SLDPRT  46 x 34 x 4  (2 vertical ears, tilt servo holes, pan horn hub)
    head.SLDPRT  70 x 50 x 3  (OLED window 27x27, 2x M2 tilt-horn screws)

REQUIREMENTS
  - SolidWorks installed and OPEN + logged in (the licensing/login dialog
    blocks automation until you've clicked through it).
  - Python with pywin32:  pip install pywin32
  - The SolidWorks API needs the part template "Part.prtdot" (auto-found).

USAGE
    python build_buddy_sldworks.py [output_dir]
    (output_dir defaults to .\\solidworks_out)

Design + wire notes: see robot/docs/BUILD_SPEC.md and PARTS_LIST.md.
"""
import os
import sys
import time
import glob

try:
    import win32com.client
except ImportError:
    sys.exit("pywin32 missing. Install it:  pip install pywin32")

DIMS = {
    "base": {
        "x": 90.0, "y": 60.0, "t": 5.0,
        "corner_hole": (3.2, 7.0),        # (diameter, inset from each edge)
        "servo_holes": (2.0, 16.0),       # (diameter, +/-offset along X)
    },
    "neck": {
        "plate": (46.0, 34.0, 4.0),
        "ear":   {"half_gap": 12.2, "t": 4.0, "len": 26.0, "h": 24.0},
        "tilt_axis_z": 11.4,              # screw height above the front plane
        "hub":   {"r": 4.5, "h": 8.0, "hole": 2.2},
    },
    "head": {
        "x": 70.0, "y": 50.0, "t": 3.0,
        "oled": (27.0, 27.0, -2.0),       # (w, h, y-offset of window center)
        "horn_holes": (2.0, 8.4, 15.0),   # (diameter, +/-span, y)
    },
}


def log(msg):
    print(msg, flush=True)


def find_template():
    roots = [
        os.environ.get("ProgramData", r"C:\ProgramData"),
        r"C:\Program Files\SOLIDWORKS Corp",
        r"C:\Program Files\Common Files\SOLIDWORKS Shared",
    ]
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            # skip very deep/slow subtrees
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
        log("Connected to the RUNNING SolidWorks instance.")
    except Exception:
        log("No running SolidWorks — launching a new instance...")
        sw = win32com.client.Dispatch("SldWorks.Application")
        time.sleep(3)
    sw.Visible = True
    return sw


def select_plane(model, name):
    # The 5-arg IModelDoc::SelectByID avoids the Callout/SelectOption args of
    # SelectByID2, which pywin32 late binding can't marshal (type mismatch).
    return model.SelectByID(name, "PLANE", 0, 0, 0)


def sketch_rect(skm, x1, y1, x2, y2):
    skm.CreateCornerRectangle(x1, y1, 0, x2, y2, 0)


def sketch_circle(skm, cx, cy, r):
    skm.CreateCircle(cx, cy, 0, cx + r, cy, 0)


def start_sketch(model, plane):
    if not select_plane(model, plane):
        raise RuntimeError(f"could not select {plane}")
    skm = model.SketchManager
    skm.InsertSketch(True)          # void method — returns None even on success
    return skm


def end_sketch(model):
    model.SketchManager.InsertSketch(True)   # toggle off
    model.ClearSelection2(True)


def extrude(model, depth):
    # FeatureExtrusion2 is a void wrapper here (returns None on success).
    model.FeatureManager.FeatureExtrusion2(True, False, False, 0, 0, float(depth), 0,
                                           False, False, False, False, 0, 0, False,
                                           True, False, False, True, True, True, 0, 0, 0)


def cut_through(model, both=False):
    # SolidWorks 2025 FeatureCut signature (from the typelib):
    #   (Sd, Flip, Dir, T1, T2, D1, D2, Dchk1, Dchk2, Ddir1, Ddir2,
    #    Dang1, Dang2, OffsetReverse1, OffsetReverse2, TranslateSurface1,
    #    TranslateSurface2, NormalCut, UseFeatScope, UseAutoSelect)
    # T1: swEndCondThroughAll = 1, swEndCondThroughAllBoth = 2
    t1 = 2 if both else 1
    model.FeatureManager.FeatureCut(True, False, False, t1, 0, 0, 0,
                                    False, False, False, False, 0, 0,
                                    False, False, False, False, True, True, True)


def new_part(sw, template):
    if not template:
        raise RuntimeError("Part.prtdot template not found")
    model = sw.NewDocument(template, 0, 0, 0)
    if not model:
        raise RuntimeError("NewDocument failed (licensing dialog open?)")
    time.sleep(1.0)
    return model


def close_all(sw):
    """Close every open document WITHOUT saving, so stale probes never trigger
    a save prompt that would stall automation."""
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


def build_base(sw, model, out):
    log("  base: plate + holes")
    skm = start_sketch(model, "Front Plane")
    x, y, t = DIMS["base"]["x"], DIMS["base"]["y"], DIMS["base"]["t"]
    sketch_rect(skm, -x / 2, -y / 2, x / 2, y / 2)
    end_sketch(model)
    extrude(model, t)
    # corner M3 holes + 2 servo flange M2 holes
    skm = start_sketch(model, "Front Plane")
    d, ins = DIMS["base"]["corner_hole"]
    for ix in (-1, 1):
        for iy in (-1, 1):
            sketch_circle(skm, ix * (x / 2 - ins), iy * (y / 2 - ins), d / 2)
    sd, soff = DIMS["base"]["servo_holes"]
    sketch_circle(skm, soff, 0, sd / 2)
    sketch_circle(skm, -soff, 0, sd / 2)
    end_sketch(model)
    cut_through(model)
    model.SaveAs3(out, 0, 2)


def build_neck(sw, model, out):
    log("  neck: plate + ears + holes + hub")
    px, py, pt = DIMS["neck"]["plate"]
    e = DIMS["neck"]["ear"]
    skm = start_sketch(model, "Front Plane")
    sketch_rect(skm, -px / 2, -py / 2, px / 2, py / 2)
    end_sketch(model)
    extrude(model, pt)
    # ears on ±X (overlapping the plate footprint -> rises above it)
    skm = start_sketch(model, "Front Plane")
    for sx in (-1, 1):
        cx = sx * e["half_gap"]
        sketch_rect(skm, cx - e["t"] / 2, -e["len"] / 2, cx + e["t"] / 2, e["len"] / 2)
    end_sketch(model)
    extrude(model, e["h"])
    # tilt servo screws: through both ears, along X (Right Plane sketch)
    skm = start_sketch(model, "Right Plane")
    sketch_circle(skm, 0, DIMS["neck"]["tilt_axis_z"], 1.0)
    end_sketch(model)
    cut_through(model, both=True)
    # pan horn hub below the plate (boss, then its center hole)
    h = DIMS["neck"]["hub"]
    skm = start_sketch(model, "Front Plane")
    sketch_circle(skm, 0, 0, h["r"])
    end_sketch(model)
    model.FeatureManager.FeatureExtrusion2(True, True, False, 0, 0, h["h"], 0,
                                           False, False, False, False, 0, 0, False,
                                           True, False, False, True, True, True, 0, 0, 0)
    skm = start_sketch(model, "Front Plane")
    sketch_circle(skm, 0, 0, h["hole"] / 2)
    end_sketch(model)
    cut_through(model)
    model.SaveAs3(out, 0, 2)


def build_head(sw, model, out):
    log("  head: face + OLED window + horn screws")
    x, y, t = DIMS["head"]["x"], DIMS["head"]["y"], DIMS["head"]["t"]
    skm = start_sketch(model, "Front Plane")
    sketch_rect(skm, -x / 2, -y / 2, x / 2, y / 2)
    end_sketch(model)
    extrude(model, t)
    # OLED window + 2 horn screw holes
    skm = start_sketch(model, "Front Plane")
    w, hh, oy = DIMS["head"]["oled"]
    sketch_rect(skm, -w / 2, oy - hh / 2, w / 2, oy + hh / 2)
    hd, hspan, hy = DIMS["head"]["horn_holes"]
    for ix in (-1, 1):
        sketch_circle(skm, ix * hspan / 2, hy, hd / 2)
    end_sketch(model)
    cut_through(model)
    model.SaveAs3(out, 0, 2)


def report(model, name, out_dir):
    """Feature/body counts from the still-open part (no reopening needed)."""
    try:
        fc = model.GetFeatureCount()
    except Exception:
        fc = "?"
    try:
        bc = model.GetBodyCount()
    except Exception:
        bc = "?"
    path = os.path.join(out_dir, name + ".SLDPRT")
    sz = os.path.getsize(path) if os.path.exists(path) else 0
    log(f"  verified {name}: {sz:,} bytes, features={fc}, bodies={bc}")


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "solidworks_out")
    os.makedirs(out_dir, exist_ok=True)
    template = find_template()
    if not template:
        log("!! Could not find Part.prtdot — set the template path manually.")
    else:
        log(f"Template: {template}")

    sw = connect()
    close_all(sw)
    for name, fn in (("base", build_base), ("neck", build_neck), ("head", build_head)):
        log(f"Building {name}.SLDPRT ...")
        try:
            model = new_part(sw, template)
            path = os.path.join(out_dir, name + ".SLDPRT")
            fn(sw, model, path)
            log(f"  saved {path}")
            report(model, name, out_dir)
        except Exception as e:
            log(f"  !! {name} failed: {e}")
        try:
            sw.CloseDoc("Part1")
        except Exception:
            pass
    log("Done. Files in: " + out_dir)


if __name__ == "__main__":
    main()
