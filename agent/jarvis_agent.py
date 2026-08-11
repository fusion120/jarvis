"""
JARVIS DESKTOP AGENT  v1.0
==========================
A small local program that gives Jarvis (the cloud backend) real control of
this Windows PC. It polls the backend for approved tasks, executes them, and
reports back — the same pattern as the Chrome extension, but for the OS.

SAFETY
------
The backend decides what is safe / needs approval / is blocked. The agent only
executes tasks the backend hands to it (which are already approved or safe).
As defense-in-depth, this agent still refuses to delete system paths and stops
on the first failed step.

SETUP (first run)
-----------------
Double-click run_agent.bat (or `python jarvis_agent.py`). You'll be asked for:
  - Backend URL     e.g. https://jarvis-3hff.onrender.com
  - API Secret      the same API_SECRET your dashboard uses
It saves those to agent_config.json (gitignored). Env vars JARVIS_BACKEND /
JARVIS_SECRET / JARVIS_WORKSPACE override the file.
"""
import os, sys, json, time, re, threading, subprocess, shutil, ctypes, platform, datetime, webbrowser
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import robot_bridge   # Jarvis Buddy — USB serial driver for the Arduino (robot/)

BASE          = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE   = os.path.join(BASE, "agent_config.json")
LOG_FILE      = os.path.join(BASE, "agent.log")
WORKSPACE_DEFAULT = os.path.join(os.path.expanduser("~"), "jarvis-workspace")
FILE_SERVER_PORT = 8765

workspace = WORKSPACE_DEFAULT

SYSTEM_DIRS = ("C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)", "C:\\ProgramData")

# ── LOGGING ─────────────────────────────────────────────────────────────
LOG_RING = __import__("collections").deque(maxlen=120)   # last N lines for the companion UI
def log(msg):
    line = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line)
    LOG_RING.append(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

# ── CONFIG ──────────────────────────────────────────────────────────────
def load_config():
    cfg = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
    backend = os.environ.get("JARVIS_BACKEND") or cfg.get("backend") or ""
    secret  = os.environ.get("JARVIS_SECRET") or cfg.get("secret") or ""
    ws      = os.environ.get("JARVIS_WORKSPACE") or cfg.get("workspace") or WORKSPACE_DEFAULT
    if not backend or not secret:
        print("=== JARVIS DESKTOP AGENT — FIRST RUN SETUP ===")
        print("(These are saved to agent_config.json — never committed to git.)")
        if not backend:
            backend = input("Backend URL (e.g. https://jarvis-3hff.onrender.com): ").strip().rstrip("/")
        if not secret:
            secret = input("API Secret (your Render API_SECRET): ").strip()
    if not backend or not secret:
        sys.exit("Backend URL and API Secret are required, Sir. Set JARVIS_BACKEND / "
                 "JARVIS_SECRET env vars or answer the prompts.")
    cfg = {"backend": backend, "secret": secret, "workspace": ws}
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass
    return cfg

# ── SMALL HELPERS ───────────────────────────────────────────────────────
def ok(done):       return {"ok": True,  "done": done}
def err(msg):       return {"ok": False, "error": str(msg)[:500]}
def _abs(p):        return os.path.abspath(os.path.expanduser(p or workspace))
def _in_workspace(p):
    ap = _abs(p).lower(); ws = os.path.abspath(workspace).lower()
    return ap == ws or ap.startswith(ws + os.sep)
def _is_system(p):
    ap = _abs(p).lower()
    return any(ap == d.lower() or ap.startswith(d.lower() + os.sep) for d in SYSTEM_DIRS)

def run_shell(command, timeout=120, cwd=None):
    """Run a command through the shell. Returns an ok/err result."""
    try:
        p = subprocess.run(command, shell=True, capture_output=True, text=True,
                           timeout=timeout, cwd=cwd or workspace)
        out = (p.stdout or "").strip()
        if (p.stderr or "").strip():
            out = out + ("\n" + p.stderr.strip()) if out else p.stderr.strip()
        out = out.strip()[:6000]
        note = f"  (exit {p.returncode})" if p.returncode != 0 else ""
        return ok((out or "Done.") + note)
    except subprocess.TimeoutExpired:
        return err(f"Command timed out after {timeout}s")
    except Exception as e:
        return err(str(e)[:400])

def run_ps(script, timeout=60):
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                           capture_output=True, text=True, timeout=timeout)
        out = (p.stdout or "").strip()
        if (p.stderr or "").strip():
            out = out + ("\n" + p.stderr.strip()) if out else p.stderr.strip()
        return ok((out or "Done.")[:6000])
    except subprocess.TimeoutExpired:
        return err(f"PowerShell timed out after {timeout}s")
    except Exception as e:
        return err(str(e)[:400])

# ── ACTIONS ─────────────────────────────────────────────────────────────
def act_open_app(step):
    app = (step.get("app") or "").strip()
    if not app:
        return err("No app name, Sir.")
    try:
        found = shutil.which(app) or shutil.which(app + ".exe")
        if found:
            subprocess.Popen([found])
        else:
            os.startfile(app)            # registered app, file, folder, or URL
        return ok(f"Launched {app}.")
    except Exception:
        try:
            subprocess.run(f'start "" "{app}"', shell=True, timeout=20)
            return ok(f"Launched {app}.")
        except Exception as e:
            return err(f"Couldn't open '{app}': {e}")

def act_list_files(step):
    path = _abs(step.get("path"))
    if not os.path.isdir(path):
        return err(f"Not a folder: {path}")
    try:
        lines = []
        for name in sorted(os.listdir(path)):
            p = os.path.join(path, name)
            try:
                isdir = os.path.isdir(p)
                size = os.path.getsize(p) if os.path.isfile(p) else 0
            except Exception:
                isdir, size = False, 0
            lines.append(("[DIR]  " if isdir else "       ") + name + ("" if isdir else f"  ({size:,} B)"))
        body = "\n".join(lines[:80])
        return ok(f"{path} ({len(lines)} entries):\n" + (body or "(empty)"))
    except Exception as e:
        return err(str(e)[:400])

def act_read_file(step):
    path = _abs(step.get("path"))
    if not os.path.isfile(path):
        return err(f"Not a file: {path}")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read(200000)
        return ok(text[:180000] if text else "(empty file)")
    except Exception as e:
        return err(str(e)[:400])

def act_find_file(step):
    name = (step.get("name") or "").lower()
    path = _abs(step.get("path"))
    hits = []
    try:
        for root, dirs, files in os.walk(path):
            for fn in files:
                if name in fn.lower():
                    hits.append(os.path.join(root, fn))
                    if len(hits) >= 30:
                        break
            if len(hits) >= 30:
                break
    except Exception as e:
        return err(str(e)[:300])
    return ok(f"{len(hits)} match(es) for '{name}' under {path}:\n" + "\n".join(hits) if hits
              else f"No files matching '{name}' under {path}.")

def act_sys_info(step):
    info = {"os": platform.platform(), "machine": platform.machine(),
            "cpu_count": os.cpu_count(), "python": sys.version.split()[0]}
    try:
        du = shutil.disk_usage(workspace or os.path.expanduser("~"))
        info["disk_total_gb"] = round(du.total / 1e9, 1)
        info["disk_free_gb"] = round(du.free / 1e9, 1)
    except Exception:
        pass
    try:
        class MS(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = MS(); m.dwLength = ctypes.sizeof(MS)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        info["ram_total_gb"] = round(m.ullTotalPhys / 1e9, 1)
        info["ram_free_gb"] = round(m.ullAvailPhys / 1e9, 1)
    except Exception:
        pass
    return ok(json.dumps(info, indent=2))

def act_net_info(step):
    host = (step.get("host") or "").strip()
    if host:
        return run_shell(f"ipconfig /all & ping -n 2 {host}")
    return run_shell("ipconfig /all")

def act_network_scan(step):
    return run_shell("arp -a")

def act_screenshot(step):
    try:
        from PIL import ImageGrab
        shots = os.path.join(workspace, "_screenshots")
        os.makedirs(shots, exist_ok=True)
        name = "screen_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
        path = os.path.join(shots, name)
        ImageGrab.grab().save(path)
        url = f"http://localhost:{FILE_SERVER_PORT}/screens/{name}"
        return ok(f"Saved {path} ({os.path.getsize(path):,} B). View on this PC: {url}")
    except Exception as e:
        return err(f"Screenshot failed: {e}")

def act_list_windows(step):
    return run_ps("Get-Process | Where-Object { $_.MainWindowTitle } | "
                  "Select-Object ProcessName, MainWindowTitle | Format-Table -AutoSize | Out-String -Width 200")

def act_list_printers(step):
    return run_ps("Get-Printer | Select-Object Name, PortName, DriverName | Format-Table -AutoSize | Out-String -Width 200")

def act_list_usb(step):
    return run_ps("Get-PnpDevice -Class USB -PresentOnly | Select-Object FriendlyName, Status | Format-Table -AutoSize | Out-String -Width 200")

def act_list_displays(step):
    return run_ps("Get-CimInstance Win32_VideoController | Select-Object Name, "
                  "CurrentHorizontalResolution, CurrentVerticalResolution, Status | "
                  "Format-Table -AutoSize | Out-String -Width 200")

def act_get_clipboard(step):
    return run_ps("Get-Clipboard")

def act_set_clipboard(step):
    text = (step.get("text") or "")[:5000]
    return run_ps("Set-Clipboard -Value '" + text.replace("'", "''") + "'")

def act_write_file(step):
    path = _abs(step.get("path"))
    content = step.get("content") or ""
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return ok(f"Wrote {len(content):,} bytes to {path}")
    except Exception as e:
        return err(str(e)[:400])

def act_edit_file(step):
    path = _abs(step.get("path"))
    old, new = step.get("old") or "", step.get("new") or ""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        if old and old not in text:
            return err("Couldn't find the text to replace in that file.")
        text = text.replace(old, new, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return ok(f"Edited {path}.")
    except Exception as e:
        return err(str(e)[:400])

def act_delete_file(step):
    path = _abs(step.get("path"))
    if _is_system(path):
        return err("Refusing to delete a system path, Sir.")
    try:
        os.remove(path)
        return ok(f"Deleted {path}.")
    except Exception as e:
        return err(str(e)[:400])

def act_delete_folder(step):
    path = _abs(step.get("path"))
    if _is_system(path):
        return err("Refusing to delete a system path, Sir.")
    try:
        shutil.rmtree(path)
        return ok(f"Deleted folder {path}.")
    except Exception as e:
        return err(str(e)[:400])

def act_run_command(step):
    cmd = (step.get("command") or "").strip()
    if not cmd:
        return err("No command, Sir.")
    cwd = step.get("cwd") or None          # optional explicit dir (e.g. a firmware folder)
    return run_shell(cmd, timeout=int(step.get("timeout") or 120), cwd=cwd)

def act_execute_code(step):
    lang = (step.get("language") or "python").lower()
    code = step.get("code") or ""
    if not code:
        return err("No code to run, Sir.")
    try:
        os.makedirs(workspace, exist_ok=True)
        ext = ".js" if ("js" in lang or "node" in lang) else ".py"
        interp = "node" if ("js" in lang or "node" in lang) else "python"
        path = os.path.join(workspace, f"_run_{int(time.time())}{ext}")
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        return run_shell(f'"{interp}" "{path}"', timeout=120)
    except Exception as e:
        return err(str(e)[:400])

def act_install(step):
    name = (step.get("name") or "").strip()
    if not name:
        return err("No software name, Sir.")
    return run_shell(f'winget install --name "{name}" --accept-package-agreements '
                     f'--accept-source-agreements --silent', timeout=300)

def act_shutdown(step):
    return run_shell('shutdown /s /t 30 /c "Jarvis: shut down requested. Cancel with shutdown /a within 30s."', timeout=15)

def act_restart(step):
    return run_shell('shutdown /r /t 30 /c "Jarvis: restart requested. Cancel with shutdown /a within 30s."', timeout=15)

def act_send_keys(step):
    keys = (step.get("keys") or "").strip()
    if not keys:
        return err("No keys, Sir.")
    script = ("Add-Type -AssemblyName System.Windows.Forms; "
              "[System.Windows.Forms.SendKeys]::SendWait('" + keys.replace("'", "''") + "')")
    return run_ps(script)

def act_print(step):
    path = _abs(step.get("path"))
    if not os.path.isfile(path):
        return err(f"Not a file: {path}")
    return run_ps("Get-Content '" + path.replace("'", "''") + "' | Out-Printer", timeout=60)

def act_wait(step):
    time.sleep(max(0, int(step.get("ms") or 500)) / 1000.0)
    return ok("Waited.")

# ── MEDIA / DISPLAY (volume, brightness, media keys — zero extra deps) ─
# Media/volume keys are OS virtual-key codes sent with SendInput-style
# keybd_event; they work system-wide no matter which app is focused.
_VK = {"vol_up": 0xAF, "vol_down": 0xAE, "mute": 0xAD,
       "play_pause": 0xB3, "next": 0xB0, "prev": 0xB1, "stop": 0xB2}

def _press_vk(vk):
    """Press + release one virtual-key code."""
    u = ctypes.windll.user32
    u.keybd_event(vk, 0, 0, 0)                 # down
    u.keybd_event(vk, 0, 2, 0)                 # up (KEYEVENTF_KEYUP)
    time.sleep(0.05)

def _set_volume_level(level):
    """Precise volume via pycaw if available; else step the OS volume keys."""
    try:
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        dev = AudioUtilities.GetSpeakers()
        itf = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        from ctypes import cast, POINTER
        vol = cast(itf, POINTER(IAudioEndpointVolume))
        vol.SetMasterVolumeLevelScalar(max(0.0, min(1.0, int(level) / 100.0)), None)
        return True, f"volume set to {level}%"
    except Exception:
        # Fallback: nudge with volume keys (coarse but dependency-free).
        steps = max(1, min(40, abs(int(level) - 50) // 5))
        key = "vol_up" if int(level) >= 50 else "vol_down"
        for _ in range(steps):
            _press_vk(_VK[key])
        return True, f"nudged volume {'up' if int(level) >= 50 else 'down'} {steps} step(s)"

def act_volume(step):
    if "level" in step:
        try:
            done, msg = _set_volume_level(int(step.get("level")))
            return ok(msg) if done else err(msg)
        except Exception as e:
            return err(str(e)[:300])
    if step.get("dir") == "up":
        _press_vk(_VK["vol_up"]); return ok("Volume up.")
    if step.get("dir") == "down":
        _press_vk(_VK["vol_down"]); return ok("Volume down.")
    return err("Volume needs a level (0-100) or a direction.")

def act_mute(step):
    _press_vk(_VK["mute"]); return ok("Toggled mute.")

def act_media(step):
    cmd = (step.get("command") or "play_pause").lower()
    if cmd not in _VK:
        return err(f"Unknown media command: {cmd}")
    _press_vk(_VK[cmd]); return ok(f"Sent {cmd}.")

def act_brightness(step):
    level = (step.get("level") or "").strip()
    if not level:
        cur = run_ps("(Get-WmiObject -Namespace root\\wmi -Class WmiMonitorBrightness).CurrentBrightness")
        return cur if cur.get("ok") else ok("Brightness: unknown (no WMI monitor)")
    try:
        lvl = max(0, min(100, int(level)))
    except Exception:
        return err("Brightness level must be 0-100.")
    return run_ps(f"(Get-WmiObject -Namespace root\\wmi -Class WmiMonitorBrightnessMethods)."
                  f"WmiSetBrightness(1,{lvl})", timeout=30)

# ── ANDROID PHONE (adb / scrcpy — optional, graceful if missing) ──────
def _adb():
    p = shutil.which("adb")
    if p:
        return p
    # scrcpy ships a bundled adb.exe — use it if present.
    sp = shutil.which("scrcpy")
    if sp:
        cand = os.path.join(os.path.dirname(sp), "adb.exe")
        if os.path.isfile(cand):
            return cand
    return None

def _adb_shell(args, timeout=30):
    adb = _adb()
    if not adb:
        return None, "Android tools not found — install platform-tools (or scrcpy) and add adb to PATH."
    try:
        p = subprocess.run([adb] + args, capture_output=True, text=True, timeout=timeout)
        out = ((p.stdout or "") + ("\n" + p.stderr if p.stderr else "")).strip()
        return (out or "Done.") + (f"  (exit {p.returncode})" if p.returncode else ""), None
    except subprocess.TimeoutExpired:
        return None, f"adb timed out after {timeout}s"
    except Exception as e:
        return None, str(e)[:300]

def act_phone_list(step):
    out, e = _adb_shell(["devices"])
    if e: return err(e)
    return ok(out)

def act_phone_screenshot(step):
    adb = _adb()
    if not adb:
        return err("Android tools not found — install platform-tools (or scrcpy) and add adb to PATH.")
    try:
        p = subprocess.run([adb, "exec-out", "screencap", "-p"],
                           capture_output=True, timeout=30)
        if p.returncode != 0 or not p.stdout:
            return err(("adb screencap failed: " + p.stderr.decode(errors="replace"))[:300])
        shots = os.path.join(workspace, "_screenshots"); os.makedirs(shots, exist_ok=True)
        name = "phone_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
        path = os.path.join(shots, name)
        with open(path, "wb") as f:
            f.write(p.stdout)
        url = f"http://localhost:{FILE_SERVER_PORT}/screens/{name}"
        return ok(f"Phone screenshot saved ({os.path.getsize(path):,} B). View: {url}")
    except Exception as e:
        return err(str(e)[:300])

def act_phone_open(step):
    pkg = (step.get("package") or "").strip()
    if not pkg:
        return err("No Android package name given, Sir.")
    out, e = _adb_shell(["shell", "monkey", "-p", pkg, "1"])
    if e: return err(e)
    return ok(out)

def act_phone_shell(step):
    cmd = (step.get("command") or "").strip()
    if not cmd:
        return err("No adb shell command, Sir.")
    out, e = _adb_shell(["shell", cmd])
    if e: return err(e)
    return ok(out)

def act_phone_mirror(step):
    sp = shutil.which("scrcpy")
    if not sp:
        return err("scrcpy not installed — `winget install scrcpy` or download from scrcpy.dev.")
    try:
        subprocess.Popen([sp], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS)
        return ok("Launched scrcpy mirror of your phone.")
    except Exception as e:
        return err(str(e)[:300])

# ── IPHONE (tidevice — optional. On Windows: detection + screenshots +
# app launch. Full tap/type would need WebDriverAgent, which is fragile.) ─
def _tidevice():
    return shutil.which("tidevice")

def act_iphone_info(step):
    if not _tidevice():
        return err("tidevice not installed — `pip install tidevice` (needs an iPhone on USB + trust prompt).")
    return run_shell("tidevice info", timeout=30)

def act_iphone_screenshot(step):
    if not _tidevice():
        return err("tidevice not installed — `pip install tidevice` (needs an iPhone on USB + trust prompt).")
    shots = os.path.join(workspace, "_screenshots"); os.makedirs(shots, exist_ok=True)
    name = "iphone_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
    path = os.path.join(shots, name)
    r = run_shell(f"tidevice screenshot \"{path}\"", timeout=60)
    if not r.get("ok"):
        return r
    if not os.path.isfile(path):
        return err("tidevice ran but no screenshot file appeared.")
    url = f"http://localhost:{FILE_SERVER_PORT}/screens/{name}"
    return ok(f"iPhone screenshot saved ({os.path.getsize(path):,} B). View: {url}")

# ── VISION: webcam frame → backend Groq vision analysis ───────────────
# Set by main() once config is loaded (backend URL + API secret).
_VISION_BACKEND = ""
_VISION_SECRET = ""

def act_capture_webcam(step):
    """Grab one frame from the PC webcam, base64-JPEG it, and POST it to the
    backend /api/vision/upload. Returns what Jarvis saw (analysis from Groq)."""
    if not _VISION_BACKEND:
        return err("Vision not configured — agent not running its main loop yet, Sir.")
    import base64
    try:
        import cv2
    except ImportError:
        return err("Webcam needs OpenCV, Sir. Run: pip install opencv-python-headless")
    cap = None
    try:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)   # DSHOW = Windows directshow, reliable
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        ok_, frame = cap.read()
        if not ok_ or frame is None:
            return err("Couldn't read a frame from the webcam, Sir.")
        ok_, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ok_:
            return err("Failed to encode webcam frame, Sir.")
        image_b64 = base64.b64encode(buf.tobytes()).decode()
    finally:
        if cap is not None:
            cap.release()
    try:
        r = requests.post(
            f"{_VISION_BACKEND}/api/vision/upload",
            headers={"Content-Type": "application/json",
                     "X-Jarvis-Token": _VISION_SECRET},
            json={"image": image_b64}, timeout=75)
        if r.status_code == 200:
            data = r.json()
            analysis = data.get("analysis", "")
            # save the frame locally so Mohamed can see what Jarvis saw
            try:
                shots = os.path.join(workspace, "_vision")
                os.makedirs(shots, exist_ok=True)
                name = "cam_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".jpg"
                path = os.path.join(shots, name)
                with open(path, "wb") as f:
                    f.write(base64.b64decode(image_b64))
                return ok(f"Jarvis looked at you: {analysis}  (frame saved: {path})")
            except Exception:
                return ok(f"Jarvis looked at you: {analysis}")
        return err(f"Backend vision returned {r.status_code}: {str(r.text)[:200]}")
    except requests.RequestException as e:
        return err(f"Vision upload failed: {e}")

def act_mimo_say(step):
    """MIMO speaks on the PC: Windows built-in TTS + a small popup. Runs the
    speech in a background thread so the poll loop isn't blocked. The OLED
    mouth animates separately via the backend's robot `talk` command."""
    text = (step.get("text") or "").strip()
    if not text:
        return err("No text to speak, Sir.")
    safe = text.replace("'", "''")
    ps = (f"Add-Type -AssemblyName System.Speech; "
          f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          f"$s.Speak('{safe}')")
    threading.Thread(target=_mimo_speak_async, args=(ps, text), daemon=True).start()
    return ok(f"MIMO says: {text}")

def _mimo_speak_async(ps, text):
    try:
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                       timeout=60)
    except Exception as e:
        log(f"MIMO TTS failed: {e}")
    try:
        from winotify import Notification
        Notification(app_id="MIMO", title="MIMO", msg=text[:120]).show()
    except ImportError:
        try:
            import tkinter as tk
            import tkinter.messagebox as mb
            root = tk.Tk(); root.withdraw()
            mb.showinfo("MIMO", text[:160])
            root.destroy()
        except Exception:
            pass

def _capture_screen_b64():
    """One screen capture as base64 JPEG (downscaled to keep Groq payloads small)."""
    import io, base64
    from PIL import ImageGrab
    img = ImageGrab.grab()
    img.thumbnail((1280, 800))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=75)
    return base64.b64encode(buf.getvalue()).decode()

def _gaze_bucket(landmarks, frame_w, frame_h):
    """Map FaceMesh landmarks to a gaze region using the nose-vs-eyes offset.
    Region-level only (not pixel eye-tracking): strong yaw → away, strong
    pitch-down → paper, mild pitch-down → mimo, level face → screen."""
    def pt(i):
        return (landmarks[i].x * frame_w, landmarks[i].y * frame_h)
    nose  = pt(1)          # nose tip
    l_eye = pt(33)         # left eye outer corner
    r_eye = pt(263)        # right eye outer corner
    chin  = pt(152)        # chin
    eye_cx  = (l_eye[0] + r_eye[0]) / 2
    eye_cy  = (l_eye[1] + r_eye[1]) / 2
    eye_w   = max(1.0, abs(r_eye[0] - l_eye[0]))
    face_h  = max(1.0, abs(chin[1] - l_eye[1]))
    yaw   = (nose[0] - eye_cx) / eye_w      # + = head turned right
    pitch = (nose[1] - eye_cy) / face_h     # + = head down
    if abs(yaw) > 0.6:
        return "away"       # head turned to the side → not looking at anything here
    if pitch > 0.45:
        return "paper"      # strongly looking down at the desk
    if pitch > 0.18:
        return "mimo"       # looking down toward the robot on the desk
    return "screen"         # level face → the monitor

def _post_vision(image_b64, screenshot_b64, gaze):
    try:
        r = requests.post(
            f"{_VISION_BACKEND}/api/vision/upload",
            headers={"Content-Type": "application/json", "X-Jarvis-Token": _VISION_SECRET},
            json={"image": image_b64, "screenshot": screenshot_b64 or "", "gaze": gaze},
            timeout=75)
        return r.status_code == 200
    except requests.RequestException:
        return False

def mimo_vision_loop():
    """MIMO's continuous eyes: webcam + MediaPipe head-pose → gaze bucket,
    motion/change-gated POSTs so Groq vision is called sparingly (heartbeat
    every 30s when a face is in view; screenshot attached when gaze=screen).
    A webcam failure never kills the task-poll loop — this is its own thread."""
    if not _VISION_BACKEND or not _VISION_SECRET:
        log("MIMO vision: not configured — skipping.")
        return
    import base64
    try:
        import cv2
        import mediapipe as mp
    except ImportError as e:
        log(f"MIMO vision: missing dep ({e}) — run: pip install mediapipe")
        return
    face_mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=False, max_num_faces=2, refine_landmarks=False,
        min_detection_confidence=0.5, min_tracking_confidence=0.5)
    cap = None
    last_gaze, last_post = None, 0.0
    last_faces, last_dist = 0, "mid"
    while True:
        try:
            if cap is None or not cap.isOpened():
                if cap is not None:
                    cap.release()
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                if not cap.isOpened():
                    log("MIMO vision: webcam unavailable — retrying in 60s.")
                    time.sleep(60)
                    continue
            ok_, frame = cap.read()
            if not ok_ or frame is None:
                time.sleep(2)
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = face_mesh.process(rgb)
            gaze, faces, dist = "none", 0, "mid"
            if res.multi_face_landmarks:
                faces = len(res.multi_face_landmarks)
                lms = res.multi_face_landmarks[0].landmark   # primary (largest) face
                gaze = _gaze_bucket(lms, 640, 480)
                eye_w = abs(lms[263].x - lms[33].x)          # normalized eye width → distance
                dist = "near" if eye_w > 0.24 else ("far" if eye_w < 0.10 else "mid")
            now = time.time()
            changed = (gaze, faces, dist) != (last_gaze, last_faces, last_dist)
            last_gaze, last_faces, last_dist = gaze, faces, dist
            hb = (gaze != "none" and (now - last_post) >= 30.0)
            if not (changed or hb):
                time.sleep(2)
                continue
            ok2, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ok2:
                time.sleep(2)
                continue
            image_b64 = base64.b64encode(buf.tobytes()).decode()
            screenshot_b64 = ""
            if gaze == "screen":
                try:
                    screenshot_b64 = _capture_screen_b64()
                except Exception as e:
                    log(f"MIMO vision: screenshot failed ({e})")
            if _post_vision(image_b64, screenshot_b64, {"bucket": gaze, "faces": faces, "dist": dist, "ts": now}):
                last_post = now
                log(f"MIMO sees: gaze={gaze} faces={faces} dist={dist}" + (" + screen" if screenshot_b64 else ""))
            else:
                log("MIMO vision: upload failed — is the backend up?")
            time.sleep(2)
        except Exception as e:
            log(f"MIMO vision err: {e}")
            time.sleep(5)

# ── MIMO USB WATCH ────────────────────────────────────────────────────
def _list_usb_devices():
    """Present USB / serial devices (friendly names) that look like dev boards.
    Hubs, composite, Bluetooth, printers and plain mass-storage are filtered out
    so only interesting hardware (Arduino / ESP32 / Pico / Pi) gets reported."""
    ps = ("Get-PnpDevice -PresentOnly | Where-Object { $_.Class -in @('USB','Ports','Modem','Net') } | "
          "Select-Object -ExpandProperty FriendlyName")
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                           capture_output=True, text=True, timeout=30)
        out = set()
        for line in (p.stdout or "").splitlines():
            line = line.strip()
            if not line:
                continue
            low = line.lower()
            if any(x in low for x in ("root hub", "composite device", "usb hub", "xbox",
                                      "bluetooth", "mass storage", "print")):
                continue
            if any(x in low for x in ("arduino", "esp", "pico", "ch340", "cp210", "ftdi",
                                      "ft232", "wch", "st-link", "jtag", "raspberry",
                                      "serial", "usb to serial", "rndis", "gadget", "com port")):
                out.add(line)
        return out
    except Exception:
        return set()

def mimo_usb_loop():
    """Watch for new USB/serial devices and tell the backend so MIMO can offer
    to program them ('need a hand with that?'). Own thread; never blocks polling."""
    seen = set()
    while True:
        time.sleep(20)
        try:
            now = _list_usb_devices()
        except Exception:
            continue
        new = now - seen
        seen = now
        if new and _VISION_BACKEND and _VISION_SECRET:
            try:
                requests.post(f"{_VISION_BACKEND}/api/robot/usb_event",
                              headers={"Content-Type": "application/json",
                                       "X-Jarvis-Token": _VISION_SECRET},
                              json={"devices": sorted(new)}, timeout=15)
                log(f"MIMO usb: new device(s) -> {', '.join(sorted(new))}")
            except requests.RequestException as e:
                log(f"MIMO usb event failed: {e}")

ACTIONS = {
    "open_app": act_open_app, "list_files": act_list_files, "read_file": act_read_file,
    "find_file": act_find_file, "get_system_info": act_sys_info,
    "get_network_info": act_net_info, "network_scan": act_network_scan,
    "screenshot": act_screenshot, "list_windows": act_list_windows,
    "list_printers": act_list_printers, "list_usb": act_list_usb,
    "list_displays": act_list_displays, "get_clipboard": act_get_clipboard,
    "set_clipboard": act_set_clipboard, "write_file": act_write_file,
    "edit_file": act_edit_file, "delete_file": act_delete_file,
    "delete_folder": act_delete_folder, "run_command": act_run_command,
    "execute_code": act_execute_code, "install_software": act_install,
    "shutdown": act_shutdown, "restart": act_restart,
    "send_keys": act_send_keys, "print_document": act_print, "wait": act_wait,
    "capture_webcam": act_capture_webcam, "mimo_say": act_mimo_say,
    # Media / display / phone / LAN (companion app device control)
    "volume": act_volume, "mute": act_mute, "media": act_media,
    "brightness": act_brightness,
    "phone_list": act_phone_list, "phone_screenshot": act_phone_screenshot,
    "phone_open": act_phone_open, "phone_shell": act_phone_shell,
    "phone_mirror": act_phone_mirror,
    "iphone_info": act_iphone_info, "iphone_screenshot": act_iphone_screenshot,
}

# Jarvis Buddy (robot/) — merge the Arduino bridge actions.
try:
    ACTIONS.update(robot_bridge.robot_actions())
except Exception as e:
    log(f"robot bridge off ({e})")

def run_task(task):
    """Execute a task's steps, stopping on the first failure. Returns the step log."""
    log_steps = []
    for step in task.get("steps", []):
        fn = ACTIONS.get(step.get("action"))
        if not fn:
            log_steps.append({"action": step.get("action"), "ok": False,
                              "done": "", "error": "Unknown action"})
            break
        try:
            res = fn(step)
        except Exception as e:
            res = err(f"{type(e).__name__}: {e}")
        log_steps.append({"action": step.get("action"), "ok": res.get("ok"),
                          "done": res.get("done", ""), "error": res.get("error", "")})
        if not res.get("ok"):
            break
    return log_steps

# ── COMPANION SERVER STATE (set by main()) ─────────────────────────────
_BACKEND = ""
_SECRET  = ""
_WORKSPACE = ""
_LAST_POLL_OK = False
_LAST_POLL_TS = 0.0
_DEVICE_CACHE = {"ts": 0.0, "data": None}
_ACT_WHITELIST = {"volume", "mute", "media", "brightness", "phone_list",
                  "phone_screenshot", "phone_mirror", "iphone_info",
                  "iphone_screenshot", "screenshot", "network_scan", "mimo_say"}

def _device_probe():
    """Cached (10s) snapshot of connected devices for the companion window."""
    now = time.time()
    if _DEVICE_CACHE["data"] and now - _DEVICE_CACHE["ts"] < 10:
        return _DEVICE_CACHE["data"]
    out = {"phone": None, "iphone": None, "mimo": None, "lan": None}
    # Android
    try:
        adb = _adb()
        if adb:
            p = subprocess.run([adb, "devices"], capture_output=True, text=True, timeout=8)
            lines = [l.split("\t") for l in (p.stdout or "").strip().splitlines()[1:]
                     if l.strip() and "device" in l]
            out["phone"] = [l[0] for l in lines if len(l) >= 2 and l[1].startswith("device")]
    except Exception:
        pass
    # iPhone (tidevice)
    try:
        if _tidevice():
            p = subprocess.run([_tidevice(), "list"], capture_output=True, text=True, timeout=10)
            txt = (p.stdout or "") + (p.stderr or "")
            if txt.strip() and "no" not in txt.lower()[:40]:
                out["iphone"] = txt.strip().splitlines()[0][:120]
    except Exception:
        pass
    # MIMO robot
    try:
        fn = ACTIONS.get("robot_status")
        if fn:
            r = fn({})
            out["mimo"] = "ok" if r.get("ok") else "off"
    except Exception:
        out["mimo"] = "off"
    # LAN devices (arp table, unique IPs)
    try:
        p = subprocess.run("arp -a", shell=True, capture_output=True, text=True, timeout=10)
        ips = set(re.findall(r"\d+\.\d+\.\d+\.\d+", p.stdout or "")) - {"255.255.255.255"}
        out["lan"] = len(ips)
    except Exception:
        pass
    _DEVICE_CACHE.update({"ts": now, "data": out})
    return out

def _proxy_backend(path, method="GET", data=None):
    """Forward a call to the backend using the agent's stored secret. The
    companion page calls localhost, never sees the API secret. Only /api/* paths."""
    if not path.startswith("/api/"):
        return {"error": "proxy only forwards /api/*"}, 400
    try:
        headers = {"Content-Type": "application/json",
                   "X-Jarvis-Token": _SECRET,
                   "X-Jarvis-Workspace": _WORKSPACE}
        url = _BACKEND + path
        if method == "POST":
            r = requests.post(url, json=data or {}, headers=headers, timeout=25)
        else:
            r = requests.get(url, headers=headers, timeout=25)
        try:
            return r.json(), r.status_code
        except Exception:
            return {"raw": r.text[:2000]}, r.status_code
    except requests.RequestException as e:
        return {"error": f"backend unreachable: {e}"}, 502

# ── LOCAL FILE SERVER (Coding page file browser + companion window) ────
# Bound to 127.0.0.1 only. Serves the workspace file browser (read-only,
# restricted to the workspace), screenshots, the companion.html window, and
# local JSON endpoints (/api/status, /api/devices, /api/act, /api/backend).
class FileHandler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        if u.path == "/api/ws":
            self._send(200, json.dumps({"workspace": os.path.abspath(workspace)}).encode())
            return
        if u.path == "/api/files":
            p = qs.get("path", [workspace])[0]
            ap = _abs(p)
            if not _in_workspace(ap):
                self._send(403, b'{"error":"outside workspace"}'); return
            try:
                entries = [{"name": n, "dir": os.path.isdir(os.path.join(ap, n)),
                            "size": os.path.getsize(os.path.join(ap, n)) if os.path.isfile(os.path.join(ap, n)) else 0}
                           for n in sorted(os.listdir(ap))]
                self._send(200, json.dumps({"root": ap, "entries": entries}).encode())
            except Exception as e:
                self._send(400, json.dumps({"error": str(e)[:200]}).encode())
            return
        if u.path == "/api/file":
            p = qs.get("path", [""])[0]
            ap = _abs(p)
            if not _in_workspace(ap):
                self._send(403, b'{"error":"outside workspace"}'); return
            try:
                with open(ap, "rb") as f:
                    data = f.read(500000)
                self._send(200, data, ctype="text/plain; charset=utf-8")
            except Exception as e:
                self._send(400, json.dumps({"error": str(e)[:200]}).encode())
            return
        if u.path.startswith("/screens/"):
            name = u.path.rsplit("/", 1)[-1]
            try:
                with open(os.path.join(workspace, "_screenshots", name), "rb") as f:
                    self._send(200, f.read(), ctype="image/png")
            except Exception:
                self._send(404, b"not found")
            return
        # ── Companion window ──
        if u.path == "/" or u.path == "/companion":
            path = os.path.join(BASE, "companion.html")
            if not os.path.isfile(path):
                self._send(404, b'{"error":"companion.html not built yet"}'); return
            try:
                with open(path, "r", encoding="utf-8") as f:
                    html = f.read()
                self._send(200, html.encode("utf-8"), ctype="text/html; charset=utf-8")
            except Exception as e:
                self._send(400, json.dumps({"error": str(e)[:200]}).encode())
            return
        if u.path == "/api/status":
            self._send(200, json.dumps({
                "backend": _BACKEND, "workspace": os.path.abspath(workspace),
                "last_poll_ok": _LAST_POLL_OK, "last_poll_ts": _LAST_POLL_TS,
                "log_tail": list(LOG_RING)[-40:],
            }).encode())
            return
        if u.path == "/api/devices":
            try:
                self._send(200, json.dumps(_device_probe()).encode())
            except Exception as e:
                self._send(500, json.dumps({"error": str(e)[:200]}).encode())
            return
        self._send(404, b'{"error":"not found"}')

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
        except Exception:
            body = {}
        u = urlparse(self.path)
        # Immediate safe device actions (volume, media, phone screenshots...)
        if u.path == "/api/act":
            act = (body or {}).get("action", "")
            if act not in _ACT_WHITELIST and not act.startswith("robot_"):
                self._send(403, json.dumps({"error": f"action '{act}' not allowed locally"}).encode())
                return
            fn = ACTIONS.get(act)
            if not fn:
                self._send(404, json.dumps({"error": "unknown action"}).encode()); return
            try:
                res = fn(body)
            except Exception as e:
                res = {"ok": False, "error": f"{type(e).__name__}: {e}"}
            self._send(200, json.dumps(res).encode())
            return
        # Proxy to the backend using the stored secret (companion page never
        # holds the API secret itself).
        if u.path == "/api/backend":
            path = (body or {}).get("path") or ""
            method = ((body or {}).get("method") or "GET").upper()
            payload = (body or {}).get("data")
            res, code = _proxy_backend(path, method, payload)
            self._send(code, json.dumps(res).encode())
            return
        self._send(404, b'{"error":"not found"}')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def log_message(self, *a):
        pass

# ── TRAY ICON (optional: pystray + Pillow) ─────────────────────────────
_QUIT = threading.Event()
_PAUSED = False
_PAUSE_LOCK = threading.Lock()

def _open_companion(icon=None, item=None):
    def _wv():
        try:
            import webview  # optional nicety — a small real window
            webview.create_window("Jarvis Companion",
                                  f"http://localhost:{FILE_SERVER_PORT}/companion",
                                  width=880, height=720, background_color="#0a0d13")
            webview.start()
            return
        except Exception:
            pass
        webbrowser.open(f"http://localhost:{FILE_SERVER_PORT}/companion")
    threading.Thread(target=_wv, daemon=True).start()

def _approve_all(icon=None, item=None):
    def _work():
        try:
            headers = {"Content-Type": "application/json", "X-Jarvis-Token": _SECRET}
            r = requests.get(_BACKEND + "/api/desktop/approvals", headers=headers, timeout=20)
            pending = (r.json() or {}).get("pending", [])
            if not pending:
                log("Tray: no pending approvals.")
                return
            for t in pending:
                requests.post(_BACKEND + "/api/desktop/approval", headers=headers,
                              json={"task_id": t["id"], "action": "approve"}, timeout=20)
            log(f"Tray: approved {len(pending)} pending task(s).")
        except Exception as e:
            log(f"tray approve-all error: {e}")
    threading.Thread(target=_work, daemon=True).start()

def _toggle_pause(icon=None, item=None):
    global _PAUSED
    with _PAUSE_LOCK:
        _PAUSED = not _PAUSED
    log("Agent " + ("PAUSED" if _PAUSED else "resumed") + " (tray).")

def _tray_title(icon):
    while icon and not _QUIT.is_set():
        try:
            icon.title = ("Jarvis Companion — " +
                          ("agent online" if _LAST_POLL_OK else "agent offline") +
                          (" · PAUSED" if _PAUSED else ""))
        except Exception:
            pass
        _QUIT.wait(5)

def _start_tray():
    try:
        import pystray
        from PIL import Image, ImageDraw
    except Exception:
        log("Tray icon skipped (pip install pystray Pillow to enable).")
        return
    def _icon_image():
        img = Image.new("RGB", (64, 64), (10, 13, 19))
        d = ImageDraw.Draw(img)
        d.ellipse([12, 12, 52, 52], fill=(59, 130, 246))
        d.ellipse([26, 20, 38, 32], fill=(255, 255, 255))
        d.arc([20, 30, 46, 50], 20, 160, fill=(255, 255, 255), width=5)
        return img
    menu = pystray.Menu(
        pystray.MenuItem("Open Companion", _open_companion),
        pystray.MenuItem("Approve all pending", _approve_all),
        pystray.MenuItem("Pause / Resume", _toggle_pause),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", lambda i, it: _QUIT.set()),
    )
    try:
        icon = pystray.Icon("jarvis", _icon_image(), "Jarvis Companion", menu)
        threading.Thread(target=_tray_title, args=(icon,), daemon=True).start()
        icon.run()
    except Exception as e:
        log(f"tray icon failed ({e}).")

# ── MAIN LOOP ───────────────────────────────────────────────────────────
def main():
    global workspace, _BACKEND, _SECRET, _WORKSPACE, _LAST_POLL_OK, _LAST_POLL_TS
    cfg = load_config()
    backend, secret, workspace = cfg["backend"], cfg["secret"], cfg["workspace"]
    os.makedirs(workspace, exist_ok=True)
    global _VISION_BACKEND, _VISION_SECRET
    _VISION_BACKEND, _VISION_SECRET = backend, secret
    _BACKEND, _SECRET, _WORKSPACE = backend, secret, os.path.abspath(workspace)

    # Jarvis Buddy — use a saved COM port if configured, else auto-detect on first command.
    try:
        robot_bridge.configure(port=cfg.get("robot_port"))
        if cfg.get("robot_port"):
            log(f"Buddy bridge: serial {cfg['robot_port']}")
        else:
            log("Buddy bridge: auto-detect on COM3-COM20")
    except Exception as e:
        log(f"buddy bridge init failed ({e})")

    try:
        threading.Thread(target=lambda: HTTPServer(("127.0.0.1", FILE_SERVER_PORT),
                                                   FileHandler).serve_forever(),
                         daemon=True).start()
        log(f"File browser on http://localhost:{FILE_SERVER_PORT}")
    except Exception as e:
        log(f"file server off ({e}) — Coding page file browser won't work")

    # Companion tray icon (Open Companion → localhost window). Optional.
    threading.Thread(target=_start_tray, daemon=True).start()
    log("Tray icon starting (pystray + Pillow).")

    # MIMO's eyes — continuous webcam + head-pose gaze, feeds the backend.
    threading.Thread(target=mimo_vision_loop, daemon=True).start()
    log("MIMO vision loop started (webcam + head-pose gaze)")
    # MIMO's hands-off hardware radar — notices when a dev board gets plugged in.
    threading.Thread(target=mimo_usb_loop, daemon=True).start()
    log("MIMO USB watch started (Arduino/Pi plug-in detect)")

    headers = {"Content-Type": "application/json",
               "X-Jarvis-Token": secret,
               "X-Jarvis-Workspace": workspace}
    log(f"Jarvis desktop agent online  ->  {backend}")
    log(f"Workspace: {workspace}   (file browser: http://localhost:{FILE_SERVER_PORT})")
    log("Waiting for tasks from Jarvis, Sir...")
    auth_warned = False
    while not _QUIT.is_set():
        if _PAUSED:
            time.sleep(2)
            continue
        try:
            r = requests.get(f"{backend}/api/desktop/poll", headers=headers, timeout=35)  # 35s to survive Render free-tier cold starts
            _LAST_POLL_TS = time.time()
            if r.status_code != 200:
                _LAST_POLL_OK = False
                if not auth_warned:
                    log(f"Backend responded {r.status_code} — check the URL and API Secret, Sir. ({str(r.text)[:120]})")
                    auth_warned = True
                time.sleep(5)
                continue
            _LAST_POLL_OK = True
            auth_warned = False
            task = r.json().get("task")
            if task:
                log(f"Executing [{task.get('id')}] {task.get('command')}")
                steps = run_task(task)
                requests.post(f"{backend}/api/desktop/result", headers=headers,
                              json={"task_id": task.get("id"), "steps": steps}, timeout=15)
                for s in steps:
                    status = "  OK " if s.get("ok") else " ERR "
                    log(status + s.get("action") + "  " + (s.get("done") or s.get("error") or "")[:110])
        except requests.RequestException as e:
            log(f"net err: {e}")
        except Exception as e:
            log(f"err: {e}")
        time.sleep(2)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAgent stopped. Goodbye, Sir.")
