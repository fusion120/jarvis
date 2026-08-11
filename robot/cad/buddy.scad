// ============================================================
//  JARVIS BUDDY — parametric frame (OpenSCAD)
// ------------------------------------------------------------
//  Three printable parts: base plate, neck bracket, head/face.
//  Render one at a time (set `part` below) and export STL.
//  All dims in mm. Tune the servo block to YOUR servo.
//
//  SETUP:  Free & tiny — install from openscad.org, open this
//          file, set `part`, press F6 (render) then F7 (export).
// ============================================================

part = "all";   // "base" | "neck" | "head" | "all"

$fn = 48;

// ---- servo (SG90 / MG90S class) ----------------------------
servo_l           = 22.8;   // body length (along the flange axis)
servo_w           = 12.3;   // body width
servo_hole_span   = 32.0;   // distance between the two flange screw holes
servo_hole_d      = 2.0;    // M2 screw
horn_hole_d       = 4.4;    // pan-horn hub hole

// ============================================================  BASE
base_x = 90; base_y = 60; base_t = 5;   // footprint / thickness
corner_r = 6;                            // corner rounding
m3_d = 3.2;                             // M3 clearance
edge  = 7;                              // corner-hole inset
pocket_d = 2.5;                         // servo pocket depth (top face)

module rrect(x, y, r) {
    offset(r = r) square([x - 2*r, y - 2*r], center = true);
}

module base() {
    difference() {
        linear_extrude(base_t) rrect(base_x, base_y, corner_r);
        // 4 corner M3 mounting holes
        for (ix = [-1, 1], iy = [-1, 1])
            translate([ix*(base_x/2 - edge), iy*(base_y/2 - edge), -0.5])
                cylinder(d = m3_d, h = base_t + 1);
        // shallow pocket so the pan servo body sits flush, shaft up
        translate([0, 0, base_t - pocket_d - 0.01])
            linear_extrude(pocket_d + 0.02) rrect(servo_l + 1.6, servo_w + 1.6, 2);
        // pan servo flange screws (2× M2, length-wise along X)
        for (sx = [-1, 1])
            translate([sx * servo_hole_span/2, 0, -0.5])
                cylinder(d = servo_hole_d, h = base_t + 1);
    }
}

// ============================================================  NECK
neck_plate_x = 46; neck_plate_y = 34; neck_plate_t = 4;
ear_len = 26; ear_h = 28; ear_t = 4;
ear_gap   = servo_l + 1.6;          // inner face spacing (clear the body)
tilt_axis = servo_w/2 + 1.2;        // tilt shaft height above the plate
hub_r     = 4.5; hub_h = 8;         // pan-horn press-fit hub (below plate)

module neck() {
    difference() {
        union() {
            // bottom plate (sits on the pan horn)
            translate([0, 0, 0]) cube([neck_plate_x, neck_plate_y, neck_plate_t], center = true);
            // two vertical ears on ±X that grab the tilt servo's flanges
            for (sx = [-1, 1])
                translate([sx * ear_gap/2, 0, neck_plate_t + ear_h/2])
                    cube([ear_t, ear_len, ear_h], center = true);
            // pan-horn hub under the plate
            translate([0, 0, -hub_h/2 - neck_plate_t/2]) cylinder(d = 2*hub_r, h = hub_h);
        }
        // tilt servo flange screws through the ears
        for (sx = [-1, 1])
            translate([sx * ear_gap/2, 0, neck_plate_t + tilt_axis])
                rotate([90, 0, 0]) cylinder(d = servo_hole_d, h = ear_len + 1, center = true);
        // pan-horn hub: center hole + cross slot (2-arm cross horn)
        translate([0, 0, -hub_h - neck_plate_t]) {
            cylinder(d = horn_hole_d, h = hub_h + neck_plate_t + 1);
            rotate([0, 0, 45]) cube([6, 1.4, hub_h + neck_plate_t + 1], center = true);
        }
    }
}

// ============================================================  HEAD
head_x = 70; head_y = 50; head_t = 3;
oled_w = 27; oled_h = 27;
oled_y = -2;                          // window slightly above center
horn_screw_y = 15;                    // tilt-horn pivot above the face (hangs down)
horn_screw_span = 8.4;                // cross-horn arm hole spacing

module head() {
    difference() {
        cube([head_x, head_y, head_t], center = true);
        // OLED window (glue the screen behind it)
        translate([0, oled_y, 0]) cube([oled_w, oled_h, head_t + 0.6], center = true);
        // tilt-horn M2 screws through the back face
        for (ix = [-1, 1])
            translate([ix * horn_screw_span/2, horn_screw_y, 0])
                cylinder(d = 2.0, h = head_t + 1, center = true);
    }
}

// ============================================================  RENDER
if (part == "base" || part == "all")       base();
if (part == "neck" || part == "all")       translate([0, 0, 0]) neck();
if (part == "head" || part == "all")       translate([110, 0, 0]) head();
