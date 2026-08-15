"""Jarvis — Windows app build script.

Builds agent.exe + j11.exe (PyInstaller), assembles the app folder and zips
it. Run from anywhere:

    python jarvis-app/build_app.py

The output is dist/j11/ (run j11.exe) and dist/j11.zip (download).

PyInstaller does its work under %TEMP%/jarvis-build — outside the repo — because
this repo lives inside OneDrive, which locks files mid-build and makes the
build flaky. Only the finished files are copied into dist/.
"""
import os, sys, shutil, subprocess, zipfile, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")
APP = os.path.join(DIST, "j11")
BUILD = os.path.join(tempfile.gettempdir(), "jarvis-build")   # NOT in OneDrive


def retry_rm(path):
    """rmtree/remove with retries — OneDrive/Defender can hold a handle briefly."""
    for i in range(6):
        try:
            if os.path.islink(path) or os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
            return
        except PermissionError:
            time.sleep(2)
    # last resort: best-effort, ignore whatever is still locked
    shutil.rmtree(path, ignore_errors=True)


def python():
    venv = os.path.join(ROOT, "backend", ".venv", "Scripts", "python.exe")
    return venv if os.path.isfile(venv) else sys.executable


def ensure_deps(py):
    for mod, pkg in (("PyInstaller", "pyinstaller"), ("webview", "pywebview")):
        r = subprocess.run([py, "-c", f"import {mod}"], capture_output=True)
        if r.returncode != 0:
            print(f"installing {pkg}...")
            subprocess.run([py, "-m", "pip", "install", "--quiet", pkg], check=True)


def run(args):
    print(">", " ".join(args))
    r = subprocess.run(args)
    if r.returncode != 0:
        sys.exit(f"FAILED (exit {r.returncode}): {' '.join(args)}")


def build_agent(py):
    """agent.exe (one-folder) -> BUILD/dist_agent/agent/"""
    tmp = os.path.join(BUILD, "dist_agent")
    retry_rm(tmp)
    retry_rm(os.path.join(BUILD, "agent"))
    run([py, "-m", "PyInstaller", "--noconfirm", "--clean", "--noconsole",
         "--distpath", tmp,
         "--workpath", os.path.join(BUILD, "agent"),
         "--specpath", os.path.join(BUILD, "spec"),
         "--name", "agent",
         "--paths", os.path.join(ROOT, "agent"),
         os.path.join(ROOT, "agent", "jarvis_agent.py")])
    return os.path.join(tmp, "agent")


def build_main(py):
    """j11.exe (one-folder) -> BUILD/dist_main/j11/"""
    tmp = os.path.join(BUILD, "dist_main")
    retry_rm(tmp)
    retry_rm(os.path.join(BUILD, "main"))
    run([py, "-m", "PyInstaller", "--noconfirm", "--clean", "--noconsole",
         "--distpath", tmp,
         "--workpath", os.path.join(BUILD, "main"),
         "--specpath", os.path.join(BUILD, "spec"),
         "--name", "j11",
         os.path.join(ROOT, "jarvis-app", "main.py")])
    return os.path.join(tmp, "j11")


def assemble(agent_src, main_src):
    """Flatten into dist/Jarvis/ with agent.exe, extension, pages, config."""
    retry_rm(APP)
    os.makedirs(APP)
    shutil.copytree(main_src, APP, dirs_exist_ok=True)          # Jarvis.exe + _internal
    shutil.copytree(agent_src, os.path.join(APP, "agent"), dirs_exist_ok=True)
    shutil.copy(os.path.join(ROOT, "agent", "companion.html"),
                os.path.join(APP, "agent", "companion.html"))
    cfg = os.path.join(ROOT, "agent", "agent_config.json")
    if os.path.isfile(cfg):
        shutil.copy(cfg, os.path.join(APP, "agent", "agent_config.json"))
    shutil.copytree(os.path.join(ROOT, "extension"),
                    os.path.join(APP, "extension"), dirs_exist_ok=True)
    shutil.copy(os.path.join(ROOT, "jarvis-app", "app.html"),
                os.path.join(APP, "app.html"))
    # tidy the temp build area
    for p in (agent_src, main_src):
        retry_rm(os.path.dirname(p))


def make_zip():
    zpath = os.path.join(DIST, "Jarvis.zip")
    if os.path.exists(zpath):
        retry_rm(zpath)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(APP):
            for f in files:
                full = os.path.join(root, f)
                z.write(full, os.path.relpath(full, DIST))
    return zpath


def main():
    py = python()
    print("=== Jarvis — Windows app build ===")
    print("Python:", py)
    print("Temp build area:", BUILD)
    # clean stale artifacts from earlier builds (specs land in repo root otherwise)
    for stale in (os.path.join(ROOT, "agent.spec"), os.path.join(ROOT, "Jarvis.spec"),
                  os.path.join(ROOT, "build")):
        retry_rm(stale)
    os.makedirs(BUILD, exist_ok=True)
    retry_rm(APP)
    ensure_deps(py)
    print("\n[1/4] building desktop agent (agent.exe)...")
    agent_src = build_agent(py)
    print("\n[2/4] building launcher (j11.exe)...")
    main_src = build_main(py)
    print("\n[3/4] assembling dist/j11/ ...")
    assemble(agent_src, main_src)
    print("\n[4/4] zipping...")
    z = make_zip()
    print("\n=== Done ===")
    print("  Run:", os.path.join(APP, "j11.exe"))
    print("  Zip:", z)
    return 0


if __name__ == "__main__":
    sys.exit(main())
