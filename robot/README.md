# Jarvis Buddy — a body for Jarvis

A desk companion that plugs into your existing Jarvis stack. It's a **pan-tilt
Arduino head with an OLED face** that lives on your desk, nods at you, reacts to
chat, and shares the same brain your dashboard uses.

```
┌─ backend (Render) ─┐        ┌─ desktop agent (this PC) ─┐        ┌─ buddy ─┐
│ Flask + Groq brain  │  poll  │ jarvis_agent.py             │  USB   │ Arduino  │
│ robot tasks planned │◀──────▶│  + robot_bridge.py          │◀──────▶│ 2 servos │
└─────────────────────┘        │  (serial driver, COM3-20)   │ serial │ OLED face│
                               └─────────────────────────────┘        │ buzzer   │
                                                                      └──────────┘
```

The **brain** (Groq on Render) plans a robot action, the **desktop agent** picks it
up from the same queue it already polls, and `robot_bridge.py` turns each step into
a serial command the Arduino executes. Same pipeline as browser/desktop tasks —
zero new infrastructure.

---

## What it does

Ask in the dashboard chat and the buddy reacts:

| You say | Buddy does |
|---|---|
| *"make jarvis look happy"* | head moves + OLED shows `^ ^` eyes |
| *"jarvis, look left"* | head pans toward you |
| *"tell jarvis to blink"* | one eye blink |
| *"make jarvis sad"* | `u u` eyes |
| *"wake up jarvis"* | head center + chime |

Every reply's `🤖 Buddy:` line shows how many actions were queued.

## Folder map

- `docs/BUILD_SPEC.md` — mechanical design + wiring + build order
- `docs/PARTS_LIST.md` — what to buy (MVP ≈ $15–20)
- `docs/PROTOCOL.md` — the serial protocol the firmware speaks
- `firmware/jarvis_buddy/` — Arduino sketch (flash this)
- `agent/robot_bridge.py` — desktop-agent serial driver (already wired in)
- `cad/buddy.scad` — OpenSCAD parametric model → STL
- `cad/build_buddy_sldworks.py` — **builds all three parts in SolidWorks** via COM

## Build order

1. **Order parts** (`docs/PARTS_LIST.md` — you have the Uno already).
2. **Print the frame** — OpenSCAD STLs, or run `build_buddy_sldworks.py` with
   SolidWorks open to generate `base/neck/head .SLDPRT` (verified working).
3. **Wire it** — `docs/BUILD_SPEC.md` pin table (2 servos, OLED, buzzer).
4. **Flash the firmware** — open `jarvis_buddy.ino` in the Arduino IDE (needs
   Adafruit SSD1306 + Adafruit GFX), upload to the Uno.
5. **Test standalone** — Serial Monitor → `MOVE 90 45 400`, `EYE happy`, `BLINK`.
6. **Connect** — tell the desktop agent the COM port (or let it auto-detect):
   add `"robot_port": "COM7"` to `agent/agent_config.json` (optional).
7. **Talk to it** — backend is already live with `[[ROBOT]]` support; chat works
   end-to-end once the agent + Arduino are running.

## Backend

`app11.py` gained robot support riding the desktop pipeline — `ROBOT_ACTIONS`
doc + `plan_robot()`, all `robot_*` steps classified `safe`, `[[ROBOT]]` tag +
intent fallback in `chat()`. No new env vars. Re-deploy the backend as usual.

## Future

- **Speech** — V2 swaps the buzzer for a DFPlayer (real TTS MP3s).
- **Hearing** — a MAX9814 mic lets the buddy react to your voice.
- **WiFi** — swap the Uno for an ESP32 and it polls the backend directly, no PC.
