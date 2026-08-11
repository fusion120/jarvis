"""
JARVIS BUDDY BRIDGE  v1.0
=========================
Lets the desktop agent drive the Arduino buddy over USB serial. Auto-detects
the port by PING-ing candidates, reconnects if the USB unplugs, and maps the
backend's `robot_*` steps onto the serial protocol (robot/docs/PROTOCOL.md).

Usage:
    import robot_bridge
    robot_bridge.configure(port="COM7")          # optional; auto-detect otherwise
    ok, reply = robot_bridge.bridge.send("MOVE 90 45 400")
    res = robot_bridge.act_robot_eyes({"expression": "happy"})

Wiring + protocol: see robot/docs/BUILD_SPEC.md and robot/docs/PROTOCOL.md.
"""
import os
import sys
import time
import threading

try:
    import serial
    HAVE_SERIAL = True
except Exception:                       # pyserial not installed yet
    HAVE_SERIAL = False

BASE     = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE, "agent.log")
PORT_HINTS = [f"COM{i}" for i in range(3, 21)]     # COM3..COM20
BAUD     = 115200
ACK_PREFIXES = ("OK", "PONG", "READY")


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


class RobotBridge:
    """Owns the serial connection and maps protocol commands onto it."""

    def __init__(self, port=None):
        self.port = port
        self.ser = None
        self.lock = threading.Lock()
        self.last_state = "no serial library" if not HAVE_SERIAL else "not connected"

    # ── low level ─────────────────────────────────────────────────────
    def _open(self):
        """Find and open the Arduino port (PING probe). Returns bool."""
        if self.ser and self.ser.is_open:
            return True
        if not HAVE_SERIAL:
            self.last_state = "pyserial missing (pip install pyserial)"
            return False
        candidates = ([self.port] if self.port else []) + PORT_HINTS
        for p in candidates:
            try:
                s = serial.Serial(p, BAUD, timeout=0.5)
                time.sleep(0.3)                 # let the DTR reset settle
                s.reset_input_buffer()
                s.write(b"PING\n")
                s.flush()
                r = s.readline().decode("utf-8", "replace").strip()
                if r in ("PONG",) or r.startswith(("PONG", "READY")):
                    self.ser = s
                    self.port = p
                    self.last_state = f"connected on {p}"
                    log(f"Buddy online on {p}")
                    return True
                s.close()
            except Exception:
                continue
        self.last_state = "no Arduino found on COM3-COM20"
        return False

    def _close(self):
        try:
            if self.ser:
                self.ser.close()
        except Exception:
            pass
        self.ser = None

    def send(self, cmd, timeout=3.0):
        """Send one protocol line, wait for its ack. Returns (ok, reply)."""
        with self.lock:
            for attempt in range(3):
                if not self._open():
                    time.sleep(1.0)
                    continue
                try:
                    self.ser.reset_input_buffer()
                    self.ser.write((cmd + "\n").encode())
                    self.ser.flush()
                    deadline = time.time() + timeout
                    while time.time() < deadline:
                        line = self.ser.readline().decode("utf-8", "replace").strip()
                        if not line:
                            time.sleep(0.05)
                            continue
                        if line.startswith(("OK", "PONG")):
                            self.last_state = f"connected on {self.port}"
                            return True, line
                        if line.startswith("ERR"):
                            return False, line
                        # READY / STATUS chatter — keep reading for the ack
                    self._close()               # stale connection
                except Exception:
                    self._close()
                    time.sleep(1.0)
            return False, f"no-ack ({self.last_state})"

    def status(self):
        ok_, rep = self.send("STATUS", timeout=2.0)
        return rep if ok_ else f"offline ({self.last_state})"


# module-level instance shared with jarvis_agent.py
bridge = RobotBridge()


def configure(port=None):
    """Set a specific COM port (e.g. "COM7") or let it auto-detect."""
    bridge.port = port
    return bridge


def status():
    return bridge.status()


# ── backend step handlers (action name -> fn(step) -> {ok, done}) ──────
def act_robot_head(step):
    pan = int(step.get("pan") or 90)
    tilt = int(step.get("tilt") or 90)
    ms = int(step.get("ms") or 400)
    ok_, rep = bridge.send(f"MOVE {pan} {tilt} {ms}")
    return {"ok": ok_, "done": f"head -> pan {pan} tilt {tilt}: {rep}" if ok_
            else f"head move failed: {rep}"}


def act_robot_eyes(step):
    expr = (step.get("expression") or step.get("expr") or "idle").strip().lower()
    ok_, rep = bridge.send(f"EYE {expr}")
    return {"ok": ok_, "done": f"face -> {expr}: {rep}" if ok_
            else f"face failed: {rep}"}


def act_robot_blink(step):
    ok_, rep = bridge.send("BLINK")
    return {"ok": ok_, "done": "blink: " + rep if ok_ else "blink failed: " + rep}


def act_robot_blip(step):
    f = int(step.get("freq") or 880)
    d = int(step.get("ms") or 80)
    ok_, rep = bridge.send(f"BLIP {f} {d}")
    return {"ok": ok_, "done": f"beep {f}hz: {rep}" if ok_ else "beep failed: " + rep}


def act_robot_say(step):
    """MVP reaction to speech: face goes curious, two chime notes.
    V2 (DFPlayer) will play real TTS MP3s here."""
    text = (step.get("text") or "").strip()[:60]
    bridge.send("EYE curious")
    bridge.send("BLIP 1318 60")
    time.sleep(0.09)
    bridge.send("BLIP 1568 60")
    bridge.send("EYE idle")
    return {"ok": True, "done": f"reacted to \"{text}\"" if text else "reacted"}


def act_robot_status(step):
    return {"ok": True, "done": bridge.status()}


def robot_actions():
    """Actions to merge into the desktop agent's ACTIONS table."""
    return {
        "robot_head": act_robot_head,
        "robot_eyes": act_robot_eyes,
        "robot_blink": act_robot_blink,
        "robot_blip": act_robot_blip,
        "robot_say": act_robot_say,
        "robot_status": act_robot_status,
    }
