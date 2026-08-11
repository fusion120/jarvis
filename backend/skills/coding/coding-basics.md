---
lang: general
keywords: code, program, script, python, javascript, function, class
---
# General coding baseline

Apply these every time, whatever the language:

1. **Write real, runnable code** — no pseudocode, no placeholders.
2. **Run it, then read the errors** — don't assume it works. The full
   traceback tells you what to fix; fix and re-run until clean.
3. **Keep functions small and named for what they do.** One job each.
4. **Handle the failure path** — file missing, network down, empty list,
   invalid input. `try/except` or `if` guards, not silent crashes.
5. **Don't hardcode secrets** — read them from env vars or a config file.

Minimal Python example that shows the pattern:

```python
import os, sys, json

def load_config(path):
    if not os.path.exists(path):
        print(f"no config at {path}", file=sys.stderr)
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def main():
    cfg = load_config("config.json")
    name = os.environ.get("NAME", cfg.get("name", "Sir"))
    print(f"Hello, {name}.")

if __name__ == "__main__":
    main()
```

Gotchas: always `encoding="utf-8"` when opening text files on Windows;
use `if __name__ == "__main__"` so the script can also be imported;
write errors to `sys.stderr`/logging, results to stdout.
