---
lang: python
keywords: decorator, retry, memoize, timing, wrapper, functools, wraps, backoff, cache
---

# Custom decorators: retry, timing, memoize

Decorators wrap a function to add cross-cutting behavior — retries on flaky network calls,
automatic timing, or result caching — without touching the function body. Always keep the
original metadata with `functools.wraps`.

```python
import functools
import random
import time


def retry(times: int = 3, delay: float = 0.2):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(1, times + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    if attempt == times:
                        raise
                    time.sleep(delay * attempt)    # linear backoff
            return None
        return wrapper
    return deco


def timed(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        print(f"{fn.__name__} took {time.perf_counter() - start:.3f}s")
        return result
    return wrapper


def memoize(fn):
    cache = {}

    @functools.wraps(fn)
    def wrapper(*args):
        if args not in cache:
            cache[args] = fn(*args)
        return cache[args]
    return wrapper


@retry(times=3)
def flaky() -> int:
    if random.random() < 0.5:
        raise ConnectionError("boom")
    return 42


@timed
def work() -> None:
    time.sleep(0.05)


@memoize
def slow_square(n: int) -> int:
    print("computing", n)
    return n * n


print(flaky())
work()
print(slow_square(7), slow_square(7))
```

Gotchas:
- Without `@functools.wraps(fn)`, the wrapped function loses its `__name__` and `__doc__`,
  which breaks help and some debuggers.
- `memoize` keyed on `args` fails for unhashable arguments (lists, dicts) — hash a normalized
  form or use `functools.lru_cache`.
- A decorator that takes arguments (`@retry(times=3)`) must be a triple-nested function; the
  `@retry` form without parentheses needs a separate no-arg code path.
- Default arguments are evaluated at decoration time, not call time — never use a mutable
  default as the cache inside the wrapper unless you share it deliberately.
- Retry loops that raise on the last attempt re-raise the original exception; decide whether
  callers expect that or a sentinel.
