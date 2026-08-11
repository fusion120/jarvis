---
lang: python
keywords: file, read, write, folder, os, path, json, csv, directory
---
# Read and write files in Python

Always use `encoding="utf-8"` and `with` blocks on Windows.

```python
import os, json

path = os.path.join(os.path.expanduser("~"), "jarvis-workspace", "notes.txt")

# write
with open(path, "w", encoding="utf-8") as f:
    f.write("Hello Sir\n")

# read
with open(path, encoding="utf-8") as f:
    text = f.read()

# JSON config
cfg = {"name": "MIMO", "mood": "curious"}
with open("config.json", "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2)
```

Gotchas:
- `os.makedirs(dir, exist_ok=True)` before writing into a new folder — it
  silently no-ops if the dir exists.
- Prefer `os.path.join` over string `"\\"` concatenation so it works on any OS.
- JSON keys are strings; `json.load` returns `dict`, and non-ASCII needs
  `ensure_ascii=False` on save to stay readable.
- Deleting a folder recursively: `shutil.rmtree(path)` — check the path is NOT
  a system folder first (that's a hard-block rule for MIMO).
