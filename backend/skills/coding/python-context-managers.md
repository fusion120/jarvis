---
lang: python
keywords: context manager, with statement, contextlib, __enter__, __exit__, suppress, closing, resource cleanup
---

# Context managers and the with statement

`with` guarantees setup and teardown even when the body raises — the right tool for files,
locks, transactions, timers, and temporarily mutating environment or config.

```python
import contextlib
import os
import time


class Timer:
    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.elapsed = time.perf_counter() - self.start
        return False                     # False = let exceptions propagate


@contextlib.contextmanager
def temp_env(**kwargs):
    saved = {k: os.environ.get(k) for k in kwargs}
    os.environ.update(kwargs)
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


with Timer() as t:
    time.sleep(0.05)
print(f"{t.elapsed:.3f}s")

with temp_env(DEBUG="1"):
    print("inside:", os.environ.get("DEBUG"))
print("outside:", os.environ.get("DEBUG"))

with contextlib.suppress(FileNotFoundError):     # ignore one specific error
    os.remove("missing.txt")
```

Gotchas:
- Returning `True` from `__exit__` swallows exceptions — usually the wrong choice; return
  `False` unless you intentionally suppress.
- An exception raised inside `__exit__` replaces any in-flight exception; don't raise there
  unless you mean to convert it.
- The value from `__enter__` is what `with ... as name:` binds — return a useful handle, not
  the context object itself, unless that is the handle.
- For `@contextlib.contextmanager`, put cleanup in `finally`, never after `yield` — code after
  `yield` runs only when the body exits normally.
- Acquire multiple resources in nested `with` statements or use `contextlib.ExitStack`; one
  `with` line per resource keeps teardown order correct.
