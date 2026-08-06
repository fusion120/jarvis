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
import os, sys, json, time, re, threading, subprocess, shutil, ctypes, platform, datetime
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

BASE          = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE   = os.path.join(BASE, "agent_config.json")
LOG_FILE      = os.path.join(BASE, "agent.log")
WORKSPACE_DEFAULT = os.path.join(os.path.expanduser("~"), "jarvis-workspace")
FILE_SERVER_PORT = 8765

workspace = WORKSPACE_DEFAULT

SYSTEM_DIRS = ("C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)", "C:\\ProgramData")

# ── LOGGING ─────────────────────────────────────────────────────────────
def log(msg):
    line = f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line)
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
    return run_shell(cmd, timeout=int(step.get("timeout") or 120))

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
}

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

# ── LOCAL FILE SERVER (Coding page file browser + screenshots) ─────────
# Read-only, bound to 127.0.0.1 only, restricted to the workspace.
class FileHandler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

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
        self._send(404, b'{"error":"not found"}')

    def log_message(self, *a):
        pass

# ── MAIN LOOP ───────────────────────────────────────────────────────────
def main():
    global workspace
    cfg = load_config()
    backend, secret, workspace = cfg["backend"], cfg["secret"], cfg["workspace"]
    os.makedirs(workspace, exist_ok=True)

    try:
        threading.Thread(target=lambda: HTTPServer(("127.0.0.1", FILE_SERVER_PORT),
                                                   FileHandler).serve_forever(),
                         daemon=True).start()
        log(f"File browser on http://localhost:{FILE_SERVER_PORT}")
    except Exception as e:
        log(f"file server off ({e}) — Coding page file browser won't work")

    headers = {"Content-Type": "application/json",
               "X-Jarvis-Token": secret,
               "X-Jarvis-Workspace": workspace}
    log(f"Jarvis desktop agent online  ->  {backend}")
    log(f"Workspace: {workspace}   (file browser: http://localhost:{FILE_SERVER_PORT})")
    log("Waiting for tasks from Jarvis, Sir...")
    auth_warned = False
    while True:
        try:
            r = requests.get(f"{backend}/api/desktop/poll", headers=headers, timeout=35)  # 35s to survive Render free-tier cold starts
            if r.status_code != 200:
                if not auth_warned:
                    log(f"Backend responded {r.status_code} — check the URL and API Secret, Sir. ({str(r.text)[:120]})")
                    auth_warned = True
                time.sleep(5)
                continue
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
