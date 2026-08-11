---
lang: python
keywords: env, dotenv, environment variable, .env, config, secret, os.environ, getenv, load
---

# Environment config with a .env loader

Secrets and machine-specific settings belong in environment variables, not committed config
files. A `.env` file is the developer convenience: load it at startup, never overwriting real
env vars, and fail fast when a required key is missing.

```python
# Prefer:  pip install python-dotenv  ->  from dotenv import load_dotenv; load_dotenv()
# Stdlib fallback below (zero dependencies):

import os
from pathlib import Path


def load_dotenv(path: str | Path = ".env") -> None:
    path = Path(path)
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)        # real env vars always win


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set (copy .env.example to .env and fill it in)"
        )
    return value


# Demo: create a sample .env, then load it and require a key.
sample = Path(".env")
sample.write_text('API_KEY=abc123\nHOST=0.0.0.0\n', encoding="utf-8")
load_dotenv()
api_key = require_env("API_KEY")
host = os.environ.get("HOST", "127.0.0.1")
print(host, "key set:", bool(api_key))
```

Gotchas:
- Use `setdefault`, not assignment, when loading `.env` — an exported shell variable must win
  over the file, or you can't override per-deployment.
- Values that contain `=` need `split("=", 1)`; a naive `partition`/index truncates
  `DB_URL=postgres://u:p@h/db`.
- `.env` should never be committed; commit `.env.example` with placeholder values instead, and
  add `.env` to `.gitignore`.
- Python-dotenv's real loader also supports variable expansion (`$VAR`) and inline comments —
  the stdlib fallback here is deliberately minimal; use the library when you need more.
- `os.getenv` returns `""` for an empty variable, not `None` — treat empty as missing in
  validation or an empty API key silently passes.
- Load `.env` at the top of the entry point *before* importing modules that read env vars at
  import time, or those modules see nothing.
