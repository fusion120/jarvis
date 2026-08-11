---
lang: python
keywords: semaphore, asyncio, gather, rate limit, max concurrency, throttle, async, tasks, limit, throttle requests
---

# Bound concurrency with asyncio.Semaphore + gather

When fanning out hundreds of coroutines, launching them all at once floods sockets, databases,
or external APIs. An `asyncio.Semaphore` caps how many run at any instant while `gather`
collects every result.

```python
import asyncio
import random


async def fetch(i: int) -> int:
    await asyncio.sleep(random.uniform(0.05, 0.2))
    return i


async def bounded_fetch(i: int, sem: asyncio.Semaphore) -> int:
    async with sem:                         # at most `limit` coroutines inside here
        return await fetch(i)


async def main() -> None:
    limit = 5
    sem = asyncio.Semaphore(limit)
    results = await asyncio.gather(
        *(bounded_fetch(i, sem) for i in range(50))
    )
    print(f"got {len(results)} results")


if __name__ == "__main__":
    asyncio.run(main())
```

Gotchas:
- Create the semaphore in `main()` and pass it in — a module-level `Semaphore()` is bound to a
  loop at creation and fails if a new loop runs later ("attached to a different loop").
- `Semaphore(value=0)` lets nothing in until `release()` — only use that for hand-off patterns.
- Use `async with sem:` not `sem.acquire()/release()`; the former releases even on exception.
- A semaphore limits concurrency, not total rate over time — for requests-per-second limits
  pair it with a token bucket or `asyncio.sleep` pacing.
- Remember the semaphore must be shared across tasks: each task must use the *same* semaphore
  object, not create its own.
