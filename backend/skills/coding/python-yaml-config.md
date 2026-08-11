---
lang: python
keywords: yaml, pyyaml, config, safe_load, dump, settings, serialization, nested, environment
---

# YAML config files with safe_load and deep merge

YAML is friendlier than JSON for hand-edited configs (comments, nested blocks, multi-line
strings). Load it with `yaml.safe_load` — never `yaml.load` — and merge user overrides onto a
default tree recursively.

```python
# pip install pyyaml
import yaml

DEFAULT_CONFIG = """
server:
  host: 0.0.0.0
  port: 8080
logging:
  level: INFO
  file: app.log
"""


def load_yaml(text: str) -> dict:
    data = yaml.safe_load(text)
    return data if isinstance(data, dict) else {}


def deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)   # recurse into nested maps
        else:
            out[key] = value
    return out


def from_file(path: str, defaults: str) -> dict:
    raw = defaults
    try:
        with open(path, encoding="utf-8") as f:
            raw += f.read()
    except FileNotFoundError:
        pass
    return load_yaml(raw)


base = load_yaml(DEFAULT_CONFIG)
user = load_yaml("server:\n  port: 9090\nlogging:\n  level: DEBUG\n")
merged = deep_merge(base, user)
print(merged)
```

Gotchas:
- `yaml.load(text)` can execute arbitrary code via custom tags — always `yaml.safe_load`
  unless you fully trust the input.
- A YAML file can parse to a non-dict (a bare string, a list); guard the return before treating
  it as a mapping.
- YAML 1.1 (PyYAML) interprets `on/off/yes/no` as booleans — quote them
  (`"on"`) or your `"true"` strings become `True`.
- Plain `dict(base)` is a shallow merge; a nested user override replaces whole subtrees unless
  you deep-merge recursively as above.
- Duplicate keys: PyYAML silently keeps the last one — validate with a tool if your configs
  come from untrusted sources.
- Indentation is significant; an accidental tab or misaligned list yields a
  `ScannerError`/`ParserError` — always show the line number from the exception.
