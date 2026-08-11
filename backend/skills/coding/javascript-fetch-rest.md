---
lang: javascript
keywords: fetch, REST, GET POST PUT DELETE, json, headers, Content-Type, retry, AbortController, response.ok, API client
---

# fetch + REST client

`fetch` is the built-in HTTP client in Node 18+ and browsers. Wrap it in a small API layer that sets JSON headers, checks `res.ok`, parses errors, and adds retry/abort so callers never repeat the boilerplate.

```javascript
// REST client with retry + timeout + typed errors
class ApiError extends Error {
  constructor(status, body) {
    super(`HTTP ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

async function request(path, { method = "GET", body, headers = {}, retries = 2, timeoutMs = 5000 } = {}) {
  for (let attempt = 0; ; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const res = await fetch(`https://api.example.com${path}`, {
        method,
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          ...headers,
        },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: controller.signal,
      });
      const text = await res.text();
      const data = text ? JSON.parse(text) : null;
      if (!res.ok) throw new ApiError(res.status, data);
      return data;
    } catch (err) {
      if (err instanceof ApiError && err.status < 500 && err.status !== 429) throw err;
      if (attempt >= retries) throw err;
      const wait = Math.min(1000 * 2 ** attempt, 5000);   // backoff
      await new Promise((r) => setTimeout(r, wait));
    } finally {
      clearTimeout(timer);
    }
  }
}

async function main() {
  const user = await request("/users/1");                     // GET
  await request("/users", { method: "POST", body: { name: "Ava" } });
  await request("/users/1", { method: "PUT", body: { name: "Ava B" } });
  await request("/users/1", { method: "DELETE" });
  console.log(user.name);
}

main().catch((err) => console.error(err.message, err.status));
```

Gotchas:
- `res.ok` is false for 400-599; always check it — `fetch` does NOT reject on HTTP errors, only on network failure.
- A 204/empty body will throw on `res.json()` — read `res.text()` first, or sniff `res.status`.
- Recreate the `AbortController` per attempt (as above) — one controller shared across retries stays aborted after the first timeout.
- Retry only idempotent methods (GET/PUT/DELETE); retrying a POST may duplicate side effects unless you send an idempotency key.
- JSON errors come back as non-OK with a body — parse it so error messages are useful.
- In browsers, CORS must be allowed by the server or the request throws a TypeError; you can't fix it client-side.
