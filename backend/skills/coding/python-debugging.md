---
lang: python
keywords: debug, error, traceback, exception, log, logging, fix, broken
---
# Debug Python errors properly

The traceback is a map, not a wall. Read it top-down: the **last frame before
`Error:`** is almost always the line to fix.

```python
import logging, traceback

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

try:
    result = risky_function()
    logging.info("ok: %s", result)
except Exception:
    logging.error("failed:\n%s", traceback.format_exc())   # full stack, not just message
```

Common fixes by error type:
- `NameError: name 'x' is not defined` → you misspelled it or never defined it.
- `TypeError: 'NoneType' object is not subscriptable` → a call returned `None`;
  guard it before indexing.
- `KeyError: 'x'` → use `d.get("x")` or check membership first.
- `FileNotFoundError` → check the path exists; `os.path.join` a base + name.
- `IndexError: list index out of range` → the list is shorter than you think;
  iterate with `for x in lst` instead of `lst[0]`.
- `IndentationError` → spaces vs tabs; keep 4 spaces.

Rule: after you change code, run it again and confirm the error is GONE —
don't just fix the first one; there may be a second behind it.
