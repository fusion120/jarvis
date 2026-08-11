"""
Jarvis — desktop app launcher
=============================
Starts the Jarvis desktop agent (agent/jarvis_agent.py — or the bundled
agent.exe in the packaged build), waits for its local server on 127.0.0.1:8765,
then opens the unified Jarvis window (the same window for chatting AND the
Companion panels).

First run: if agent_config.json is missing, a small setup window asks for the
backend URL + API secret, then saves them and launches.

Dev:    python jarvis-app/main.py
Build:  build_app.bat  ->  dist/Jarvis/Jarvis.exe
"""
import os, sys, json, time, subprocess, webbrowser

APP_PORT = 8765
APP_URL = f"http://127.0.0.1:{APP_PORT}/app"


def _this_dir():
    return os.path.dirname(os.path.abspath(__file__))


def _repo_root():
    """Source layout: <repo>/jarvis-app/main.py -> <repo>."""
    return os.path.dirname(_this_dir())


def _agent_command():
    """Command that launches the desktop agent."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)  # dist/Jarvis in the packaged build
        for cand in (os.path.join(base, "agent", "agent.exe"),
                     os.path.join(base, "agent.exe")):
            if os.path.isfile(cand):
                return [cand]
        return []
    return [sys.executable, os.path.join(_repo_root(), "agent", "jarvis_agent.py")]


def _config_path():
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), "agent", "agent_config.json")
    return os.path.join(_repo_root(), "agent", "agent_config.json")


def ensure_config():
    """Return {backend, secret, workspace}. First run asks in a window."""
    backend = os.environ.get("JARVIS_BACKEND", "")
    secret = os.environ.get("JARVIS_SECRET", "")
    ws = os.environ.get("JARVIS_WORKSPACE", "")
    cfg_path = _config_path()
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            backend = backend or cfg.get("backend", "")
            secret = secret or cfg.get("secret", "")
            ws = ws or cfg.get("workspace", "")
        except Exception:
            pass
    if backend and secret:
        return {"backend": backend, "secret": secret, "workspace": ws}
    # ── First run: small setup window ──
    res = _setup_dialog()
    if not res or not res.get("backend") or not res.get("secret"):
        return None
    try:
        os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
    except Exception:
        pass
    return res


SETUP_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
body{background:#0a0d13;color:#e6ebf4;font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;margin:0;padding:22px}
h1{font-size:17px;margin:0 0 6px}
p{color:#9aa5b8;font-size:12.5px;margin:0 0 16px}
label{display:block;font-size:11px;color:#9aa5b8;text-transform:uppercase;letter-spacing:.06em;margin:13px 0 5px}
input{width:100%;background:#161c28;color:#e6ebf4;border:1px solid #2c3547;border-radius:8px;padding:9px 11px;font-size:13px;box-sizing:border-box;outline:none}
input:focus{border-color:#3b82f6}
button{width:100%;margin-top:20px;background:#3b82f6;color:#fff;border:none;border-radius:8px;padding:11px;font-size:14px;font-weight:600;cursor:pointer}
button:hover{filter:brightness(1.1)}
.hint{color:#5c6a78;font-size:11.5px;margin-top:8px}
#err{color:#ef4444;font-size:12px;margin-top:10px;display:none}
</style></head><body>
<h1>🤖 Jarvis</h1>
<p>First run — connect Jarvis to its cloud brain so it can chat, use the web, and control this PC.</p>
<label>Backend URL</label>
<input id="b" placeholder="https://jarvis-3hff.onrender.com" value="https://jarvis-3hff.onrender.com">
<label>API Secret</label>
<input id="s" type="password" placeholder="your Render API_SECRET">
<label>Workspace folder (optional)</label>
<input id="w" placeholder="C:\\Users\\you\\jarvis-workspace">
<button onclick="go()">Launch Jarvis</button>
<div id="err"></div>
<div class="hint">Stored only on this PC, in agent/agent_config.json. Never shared.</div>
<script>
function go(){
  var b=document.getElementById('b').value.trim();
  var s=document.getElementById('s').value.trim();
  var w=document.getElementById('w').value.trim();
  var err=document.getElementById('err');
  if(!b||!s){err.textContent='Backend URL and API Secret are required.';err.style.display='block';return}
  try{window.pywebview.api.submit(b,s,w)}
  catch(e){err.textContent='Could not save: '+e.message;err.style.display='block'}
}
document.getElementById('s').addEventListener('keydown',function(e){if(e.key==='Enter')go()});
setTimeout(function(){document.getElementById('b').focus()},200);
</script></body></html>"""


class Api:
    """Functions the web window can call through pywebview."""

    def __init__(self):
        self.setup_result = None
        self.proc = None

    def submit(self, backend, secret, workspace):
        self.setup_result = {"backend": (backend or "").strip(),
                             "secret": (secret or "").strip(),
                             "workspace": (workspace or "").strip()}
        try:
            import webview
            if webview.windows:
                webview.windows[0].destroy()
        except Exception:
            pass
        return True

    def openChromeExtensions(self, path=""):
        """Open chrome://extensions in the user's real Chrome (extension is
        loaded unpacked from the bundled folder)."""
        cands = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        ]
        for c in cands:
            if os.path.isfile(c):
                try:
                    subprocess.Popen([c, "chrome://extensions"])
                    return True
                except Exception:
                    break
        webbrowser.open("chrome://extensions")
        return True

    def openExternal(self, url):
        webbrowser.open(url)
        return True


def _setup_dialog():
    try:
        import webview
    except ImportError:
        print("pywebview is required — pip install pywebview")
        return None
    api = Api()
    try:
        webview.create_window("Jarvis — Setup", html=SETUP_HTML, js_api=api,
                              width=540, height=470, resizable=False,
                              background_color="#0a0d13")
        webview.start()
    except Exception as e:
        print("setup window failed:", e)
        return None
    return api.setup_result


def _agent_up(timeout=3.0):
    import urllib.request
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{APP_PORT}/api/status", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.4)
    return False


def main():
    cfg = ensure_config()
    if not cfg:
        print("Setup cancelled — nothing launched.")
        return 1

    # Reuse an already-running agent (e.g. launched by run_companion.bat);
    # otherwise spawn one and terminate it when the window closes.
    proc = None
    if not _agent_up(3):
        cmd = _agent_command()
        if not cmd:
            print("agent.exe not found next to Jarvis.exe")
            return 1
        env = dict(os.environ)
        env["JARVIS_BACKEND"] = cfg["backend"]
        env["JARVIS_SECRET"] = cfg["secret"]
        if cfg.get("workspace"):
            env["JARVIS_WORKSPACE"] = cfg["workspace"]
        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            proc = subprocess.Popen(cmd, env=env, creationflags=flags)
        except Exception as e:
            print("failed to start the agent:", e)
            return 1
        if not _agent_up(60):
            print("the agent did not come up on port", APP_PORT)
            if proc is not None:
                try:
                    proc.terminate()
                except Exception:
                    pass
            return 1

    try:
        import webview
    except ImportError:
        print("pywebview is required — pip install pywebview")
        return 1

    api = Api()
    api.proc = proc
    keep_agent = False
    try:
        webview.create_window("Jarvis", APP_URL, js_api=api,
                              width=1100, height=780, min_size=(860, 600),
                              background_color="#0a0d13")
        webview.start()
    except Exception as e:
        print("webview window failed, opening in a browser tab:", e)
        keep_agent = True   # the browser tab needs the agent to keep running
        try:
            webbrowser.open(APP_URL)
        except Exception:
            pass
    finally:
        if proc is not None and not keep_agent:
            try:
                proc.terminate()
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
