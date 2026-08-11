---
lang: javascript
keywords: Promise.race, timeout, AbortController, deadline, race, slow request, AbortSignal.timeout, hanging promise, cancel
---

# Promise.race & timeouts

`Promise.race` settles with the first settled promise — the standard way to impose a deadline on a slow operation. Combine with `AbortController` so the losing branch actually stops network work instead of leaking in the background.

```javascript
const { setTimeout: sleep } = require("node:timers/promises");

// Timeout wrapper: reject after ms if the promise hasn't settled
function withTimeout(promise, ms, label = "operation") {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(
      () => reject(new Error(`${label} timed out after ${ms}ms`)),
      ms
    );
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

// Fetch with a real abort (cancels the socket, not just rejects)
async function fetchWithTimeout(url, ms) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  try {
    return await fetch(url, { signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function main() {
  const slow = sleep(200).then(() => "slow result");
  try {
    await withTimeout(slow, 50);
  } catch (e) {
    console.log(e.message);           // "operation timed out after 50ms"
  }

  // AbortSignal.timeout — built-in (Node 17.3+/modern browsers)
  try {
    await fetch("https://example.com", { signal: AbortSignal.timeout(50) });
  } catch (e) {
    console.log(e.name);              // "TimeoutError" when the request hangs
  }
}

main().catch((err) => { console.error(err); process.exit(1); });
```

Gotchas:
- `Promise.race` loses: the losing promise's rejection becomes an unhandled rejection unless it has its own `.catch`. Attach handlers to the slow work.
- Race the CALL, not the result — `withTimeout(someAsyncFn(), ms)` starts the work immediately; pass a thunk for lazy start.
- For `fetch`, racing without abort still consumes the socket; use `AbortController`/`AbortSignal.timeout(ms)` to actually cancel.
- Clear the timer with `.finally()` so it doesn't hold the event loop open after the promise settles.
- `AbortSignal.timeout` is Node 17.3+/modern browsers; older runtimes need the manual controller pattern.
- A timer rejection after the promise already settled is a silent no-op — but if it fires BEFORE settle, the race rejects with it (that's the intended behavior).
