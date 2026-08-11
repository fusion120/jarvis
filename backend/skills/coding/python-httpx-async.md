---
lang: python
keywords: httpx, async client, aiohttp, AsyncClient, asyncio, gather, http, stream, response
---

# httpx async HTTP client

httpx is the modern choice when your code is already async: one `AsyncClient` fans out many
requests concurrently and shares a connection pool. Its sync/async API is near-identical, so
code ports easily between the two.

```python
# pip install httpx
import asyncio

import httpx


async def fetch_many(urls: list[str]) -> list[dict]:
    async with httpx.AsyncClient(timeout=10.0, limits=httpx.Limits(max_connections=20)) as client:
        tasks = [client.get(url) for url in urls]      # coroutines, not yet run
        responses = await asyncio.gather(*tasks)
        results = []
        for resp in responses:
            resp.raise_for_status()
            results.append(resp.json())
        return results


async def download_big(url: str, dest: str) -> None:
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as f:
                async for chunk in resp.aiter_bytes(64 * 1024):
                    f.write(chunk)


async def main() -> None:
    pages = await fetch_many(["https://httpbin.org/json"] * 3)
    print("fetched", len(pages), "pages")


if __name__ == "__main__":
    asyncio.run(main())
```

Gotchas:
- `client.get(url)` inside `AsyncClient` returns a coroutine — wrap in `asyncio.gather`, never
  `await` it inside the list comprehension (that serializes the requests).
- Reuse one `AsyncClient` for many requests; creating a client per request rebuilds the
  connection pool and kills concurrency.
- `resp.json()` on an empty body raises `ValueError`; guard with `resp.headers.get("content-type")`
  or `await resp.aread()` checks for 204s.
- Streaming: use `client.stream(...)` + `aiter_bytes`, not `client.get()` then `resp.content`,
  or a huge download is buffered entirely in memory.
- A failed request (`ConnectError`, timeout) raises at `await` — gather one bad URL and the
  whole `gather` raises unless you pass `return_exceptions=True` or a `Semaphore`.
- Keep timeouts explicit: httpx's default is 5s connect + no read timeout on some versions —
  set `timeout=` on the client or per request.
