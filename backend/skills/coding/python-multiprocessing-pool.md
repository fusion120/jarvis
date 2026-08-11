---
lang: python
keywords: multiprocessing, process pool, ProcessPoolExecutor, cpu count, parallel, map, chunk, fork
---

# CPU-bound parallelism with ProcessPoolExecutor

Python threads can't speed up CPU-heavy math because of the GIL. `ProcessPoolExecutor`
distributes work across real processes — essential for numeric crunching, image processing,
and batch hashing. The process pool owns the workers; you submit work and collect results.

```python
import math
from concurrent.futures import ProcessPoolExecutor


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    for d in range(2, int(math.isqrt(n)) + 1):
        if n % d == 0:
            return False
    return True


def count_primes_upto(limit: int) -> int:
    return sum(1 for n in range(limit + 1) if is_prime(n))


if __name__ == "__main__":                 # REQUIRED on Windows (spawn)
    ranges = [200_000, 200_000, 200_000, 200_000]
    with ProcessPoolExecutor() as pool:
        results = list(pool.map(count_primes_upto, ranges))
    print(results)
```

Gotchas:
- Windows (and macOS) start workers with *spawn*: the module is re-imported in each child, so
  all top-level work must live under `if __name__ == "__main__":` or you get infinite recursion.
- The function passed to `pool.map` must be importable (top-level, not a lambda or a closure) —
  picklability is required to ship the function to the workers.
- Arguments and return values must be picklable; lambdas, open sockets, and local classes break.
- Starting processes is expensive: the pool pays per process, not per item, but keep work
  chunks coarser than a microsecond or the IPC overhead dominates.
- Exceptions in workers propagate to the caller on `result()`/iteration, but the traceback is
  from the child — wrap worker bodies to add context.
- For I/O-bound work use threads, not processes: `ProcessPoolExecutor` gives you no benefit and
  costs more memory.
