---
lang: python
keywords: async generator, yield, async for, pipeline, streaming, producer, consumer, transform, async iteration
---

# Async generator pipelines

Like a normal generator, but each `yield` can be preceded by an `await` — so it streams values
out of slow I/O (websockets, API pagination, file tailing) and composes into filter/map stages.

```python
import asyncio
from typing import AsyncGenerator


async def read_lines() -> AsyncGenerator[str, None]:
    for i in range(10):
        await asyncio.sleep(0.05)           # pretend each line arrives over a socket
        yield f"line-{i}"


async def loud(lines: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
    async for line in lines:
        yield line.upper()


async def only_evens(lines: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
    async for line in lines:
        n = int(line.split("-")[1])
        if n % 2 == 0:
            yield line


async def main() -> None:
    async for item in only_evens(loud(read_lines())):
        print(item)


if __name__ == "__main__":
    asyncio.run(main())
```

Gotchas:
- Consume an async generator with `async for`, never a plain `for` — a plain loop just iterates
  the coroutine objects.
- An async generator is single-use: after the loop finishes it is exhausted; don't try to rewind.
- Pipes are lazy: nothing runs until you start the outermost `async for`, so keep the whole
  pipeline alive at once or data waits in the sink.
- If you `return` early in the middle of a pipeline, use `try/finally` to run cleanup —
  generators only run their `finally` when closed or garbage-collected.
- `AsyncGenerator[YieldType, SendType]` is the annotation; the second slot is almost always
  `None` unless you use `gen.send(value)`.
