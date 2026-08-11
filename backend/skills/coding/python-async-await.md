---
lang: python
keywords: async, await, asyncio, concurrency, event loop, async def, create_task, gather, run
---

# Async/await concurrency in Python

The standard tool for I/O-bound concurrency (network calls, files, sleeps): one thread, many
cooperative tasks that yield at every `await`. Use it when a program must juggle many slow
operations at once and none of them are CPU-heavy.

```python
import asyncio
import time


async def fetch(url: str) -> str:
    """Simulate a network round-trip (real code: aiohttp/httpx)."""
    await asyncio.sleep(0.5)                 # yields control, never blocks the loop
    return f"<html>{url}</html>"


async def fetch_all(urls: list[str]) -> list[str]:
    tasks = [asyncio.create_task(fetch(u)) for u in urls]
    return await asyncio.gather(*tasks)


async def main() -> None:
    start = time.perf_counter()
    results = await fetch_all(["a.com", "b.com", "c.com", "d.com"])
    print(f"{len(results)} pages in {time.perf_counter() - start:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
```

Gotchas:
- Never call `asyncio.run()` twice in one process; create one loop in `main()` and run it once.
- Blocking calls like `time.sleep` or `requests.get` inside an async function freeze the whole
  loop — use `await asyncio.sleep` and an async client, or offload with `await loop.run_in_executor(None, fn)`.
- `asyncio.run(main())` won't run coroutines you created but never awaited — create tasks with
  `asyncio.create_task` or gather them, or they raise "Task was destroyed but it is pending".
- Exceptions in `asyncio.gather` propagate at the point of the `await`; use
  `return_exceptions=True` if you want results instead of a crash.
- `asyncio.create_task` requires a running loop — call it inside `main()`, not at module import.
