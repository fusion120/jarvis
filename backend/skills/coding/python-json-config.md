---
lang: python
keywords: json, config, validate, schema, load, defaults, settings, keyerror, config file
---

# JSON config files with validation and defaults

Config-as-JSON is everywhere, but a missing key or a typo should fail loudly at startup, not
halfway through the run. Merge over explicit defaults, reject unknown keys, and coerce types.

```python
import json
from pathlib import Path

DEFAULTS = {
    "host": "127.0.0.1",
    "port": 8080,
    "retries": 3,
    "debug": False,
}


def load_config(path: Path) -> dict:
    if not path.exists():
        return dict(DEFAULTS)                    # start fresh with defaults

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object")

    unknown = set(data) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"unknown config keys: {sorted(unknown)}")

    # Type-check every override against the default's type.
    for key, value in data.items():
        if type(value) is not type(DEFAULTS[key]):
            raise ValueError(
                f"key {key!r}: expected {type(DEFAULTS[key]).__name__}, got {type(value).__name__}"
            )

    merged = dict(DEFAULTS)
    merged.update(data)
    return merged


def write_default(path: Path) -> None:
    path.write_text(json.dumps(DEFAULTS, indent=2), encoding="utf-8")


cfg = load_config(Path("app.json"))
print(cfg["host"], cfg["port"], cfg["retries"], cfg["debug"])
```

Gotchas:
- `json.load` raises `json.JSONDecodeError` on malformed input — catch it at startup and point
  at the file and line, or the user gets a raw traceback.
- `data` can legally be a list or a string; reject non-dict configs explicitly or you'll crash
  later on `data["host"]`.
- `bool` is a subclass of `int` — `type(value) is type(default)` (not `isinstance`) keeps
  `"debug": 1` from silently passing as `True`.
- Use a shallow merge (`dict(DEFAULTS)` + `update`); for nested configs you need a recursive
  deep merge or keys vanish.
- Don't trust the file to exist: defaulting to `dict(DEFAULTS)` when missing means tests and
  dev machines run without a config file.
- Secrets (API keys) do not belong in config files that get committed — route them through env
  vars instead.
