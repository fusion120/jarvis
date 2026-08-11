---
lang: javascript
keywords: async await, async function, parallel, sequential, Promise.all, await loop, top-level await, async iteration, concurrency, waterfall
---

# async/await patterns

`async`/`await` reads like synchronous code on top of promises. The hard part is knowing when things run in sequence vs parallel: `await` in a loop serializes; collecting promises first runs them concurrently.

```javascript
const { setTimeout: sleep } = require("node:timers/promises");

const delay = (ms, value) => sleep(ms).then(() => value);

// SEQUENTIAL — total time = sum of delays
async function sequential() {
  const a = await delay(30, "a");
  const b = await delay(30, "b");   // waits for a first
  return [a, b];
}

// PARALLEL — start both, wait for both: total ~ max(delays)
async function parallel() {
  const [a, b] = await Promise.all([delay(30, "a"), delay(30, "b")]);
  return [a, b];
}

// Concurrency-limited queue: at most `limit` workers in flight
async function mapLimit(items, limit, worker) {
  const results = new Array(items.length);
  let next = 0;
  async function run() {
    while (next < items.length) {
      const i = next++;
      results[i] = await worker(items[i], i);
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, run));
  return results;
}

// Async generator + for-await
async function* ticker(count) {
  for (let n = 1; n <= count; n++) {
    await sleep(5);
    yield n;
  }
}

async function main() {
  console.log(await sequential());
  console.log(await parallel());
  const doubled = await mapLimit([1, 2, 3, 4], 2, async (n) => {
    await sleep(10);
    return n * 2;
  });
  console.log(doubled);                       // [2, 4, 6, 8]
  for await (const n of ticker(3)) console.log("tick", n);
}

main().catch((err) => { console.error(err); process.exit(1); });
```

Gotchas:
- `Array.prototype.map` with an async callback returns promises immediately — `Promise.all` it or you get `[Promise,…]`.
- `await` in `forEach` does NOT wait — forEach ignores the returned promise. Use a plain `for...of`.
- Parallel work still shares one thread; only true parallelism needs worker_threads.
- Top-level await works only in ESM modules (`import`), not CommonJS `require`.
- Catching per-item errors inside the loop lets one failure not kill the whole batch; a bare `Promise.all` fails fast.
