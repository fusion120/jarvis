---
lang: python
keywords: subprocess, timeout, popen, communicate, kill, run, process, shell, capture output
---

# subprocess with timeouts and forced kill

Shelling out to another program is how Python drives ffmpeg, git, or OS tools. Always bound
the wait time: a hung child hangs your whole script. Use `subprocess.run` for fire-and-collect,
`Popen.communicate` when you must stream or kill manually.

```python
import subprocess


def run_with_timeout(cmd: list[str], timeout: float = 5.0) -> str:
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {proc.stderr.strip()}")
    return proc.stdout


print(run_with_timeout(["python", "-c", "print('hello world')"], timeout=5))

# Streaming / manual control with Popen:
proc = subprocess.Popen(
    ["python", "-c", "import time; time.sleep(10); print('done')"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
try:
    stdout, stderr = proc.communicate(timeout=2)
except subprocess.TimeoutExpired:
    proc.kill()                       # SIGKILL; on POSIX use proc.terminate() first
    stdout, stderr = proc.communicate()
    print("killed after timeout")
```

Gotchas:
- `subprocess.run(...)` without `timeout=` waits forever — always pass one, and catch
  `subprocess.TimeoutExpired`.
- Pass the command as a *list* (`["git", "status"]`), never a string, or `shell=True` becomes
  tempting — shell=True invites injection when any argument comes from user input.
- After `TimeoutExpired`, the child is still running: call `proc.kill()` (or `terminate()`
  first, then `kill()`) and then `communicate()` again to reap it and drain pipes.
- `Popen(..., stdout=PIPE, stderr=PIPE)` + `communicate(timeout=...)` is safe from pipe-deadlock;
  doing manual `proc.stdout.read()` without draining stderr can deadlock on a full pipe buffer.
- `capture_output=True` plus `stdout=PIPE` at the same time is a `ValueError` — pick one style.
- `check=True` raises `CalledProcessError` on nonzero exit; without it you must inspect
  `returncode` yourself.
