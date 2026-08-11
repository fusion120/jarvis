# Jarvis Buddy — Build Spec (v1)

A desk companion for Jarvis: a **pan-tilt head** with an **OLED face** driven by your
**Arduino Uno**, connected to your PC over USB, relayed to your backend by the desktop agent.

- **Brain** — your existing Flask backend on Render (unchanged)
- **Relay** — the desktop agent (`agent/jarvis_agent.py`), which gains a robot module
- **Body** — Arduino Uno + 2 servos + OLED + buzzer, over USB serial

```
backend (Render)  <──poll──  desktop agent (PC)  <──USB serial──>  Arduino (body)
                                   │  jarvis_agent.py                 │
                                   └─ robot_bridge.py ────────────────┘
```

---

## 1. Mechanical design

A classic 2-axis pan-tilt rig: a **pan servo** spins the upper assembly left/right, a
**tilt servo** pitches the face up/down. Three printed parts (or Lego Technic substitute).

### Part A — Base plate
| Dim | Value |
|---|---|
| Footprint | 90 × 60 mm |
| Thickness | 5 mm |
| Corner holes | 4× Ø3.2 mm (M3), 6 mm from each edge |
| Pan servo pocket | recess so the SG90 body sits flush, shaft up |
| Pan servo screws | 2× M2 × 8 mm through the servo flange ears |

### Part B — Neck bracket
| Dim | Value |
|---|---|
| Overall height | 30 mm |
| Horn hub | splined hole to press onto the pan servo horn (standard 2-arm cross horn) |
| Ear spacing | 24 mm inside — matches SG90 body length (23 mm) + 0.5 mm clearance each side |
| Tilt servo screws | 2× M2 × 8 mm through the ears into the servo flange |

### Part C — Head / face plate
| Dim | Value |
|---|---|
| Footprint | 70 × 50 mm |
| Thickness | 3 mm |
| OLED window | 27 × 27 mm cutout centered 20 mm up from the bottom (0.96" screen) |
| Tilt horn hub | splined hub on the back face for the tilt servo horn |
| Speaker/mic holes | Ø3 mm grille, lower corners (for the V2 DFPlayer/mic) |

> The OpenSCAD model (`cad/buddy.scad`) and SolidWorks script (`cad/build_buddy_sldworks.py`)
> use SG90 standard dimensions. If your servo's flange holes differ, adjust the two
> `servo_hole_spacing` params — everything is parametric.

**Lego alternative:** the neck bracket can be built from Technic beams + pins; the head
plate becomes a Technic panel. Servos bolt to beams with M2 through-hole. Print nothing
except (optionally) the face plate for the OLED window.

---

## 2. Electronics & wiring

### Bill of wiring
| From | To | Wire |
|---|---|---|
| Pan servo signal | **D9** | yellow/orange |
| Pan servo power | **5V rail** (external supply) | red |
| Pan servo ground | **GND rail** (shared) | brown/black |
| Tilt servo signal | **D10** | yellow/orange |
| Tilt servo power | **5V rail** (external supply) | red |
| Tilt servo ground | **GND rail** (shared) | brown/black |
| OLED SDA | **A4** | blue |
| OLED SCL | **A5** | yellow |
| OLED VCC / GND | 5V / GND | red / black |
| Buzzer + | **D3** (through 100 Ω) | red |
| Buzzer − | GND | black |
| (V2) MAX9814 mic OUT | **A0** | white |
| Uno USB-B | your PC | data cable |

### Power (important)
- **Logic** (Uno, OLED, buzzer): the USB cable from your PC — enough for the OLED + buzzer.
- **Servos**: power them from a **separate 5 V / 2 A supply** (any phone charger wired to a
  breadboard 5V rail) — *not* from the Uno's 5 V pin. Two SG90s can brown-out the Uno and
  reset it mid-move if they draw from USB.
- **Ground**: the external supply's GND MUST be tied to the Uno's GND (shared rail).
- Common ground is the #1 wiring mistake — if servos twitch and the OLED flickers, check it.

### Serial
- Uno → PC: USB (the IDE port). 115200 baud, 8-N-1.
- Find the port (e.g. `COM7`) in the Arduino IDE or Device Manager; you'll tell the agent.

---

## 3. Serial protocol (Uno ⇄ agent)

ASCII, newline-terminated, 115200 baud. Full spec in `docs/PROTOCOL.md`.

| Command | Example | What the buddy does |
|---|---|---|
| `PING` | `PING` | replies `PONG` |
| `POS <pan> <tilt>` | `POS 90 45` | snaps head to angles (0–180) |
| `MOVE <pan> <tilt> <ms>` | `MOVE 45 60 400` | smooth move over ms (default 400) |
| `EYE <expr>` | `EYE happy` | OLED expression: `idle` `happy` `sad` `curious` `blink` `sleep` `x` |
| `BLINK` | `BLINK` | one eye blink |
| `BLIP <freq> <ms>` | `BLIP 880 80` | buzzer tone |
| `STATUS` | `STATUS` | replies angles + uptime (for the Desktop page) |
| `RST` | `RST` | re-home both servos to center |

Every command acks with `OK …` or `ERR …`. The agent waits for the ack before the next step.

---

## 4. Firmware → build order (do this once parts arrive)

1. **Print** base, neck, head from the CAD (`cad/`), or build the bracket from Lego.
2. **Wire** per the table above. Power servos from the external rail, shared ground.
3. **Flash** `firmware/jarvis_buddy/jarvis_buddy.ino` to the Uno (needs Arduino IDE +
   Adafruit SSD1306 + Adafruit GFX + Servo libraries — see the file's header comment).
4. **Test standalone** — Serial Monitor → type `MOVE 90 90 500`, `EYE happy`, `BLINK`.
5. **Connect** — tell the desktop agent the COM port; it auto-reconnects if the Uno unplugs.
6. **Talk to it** — in the dashboard chat: *"make jarvis look happy"*, *"tell jarvis to
   look left"*, *"make jarvis say hi"*. The backend plans it → agent → Arduino → buddy moves.
