---
lang: javascript
keywords: worker_threads, worker, multithreading, CPU bound, main thread, parentPort, postMessage, workerData, thread pool, parallel
---

# worker_threads for CPU-bound work

`worker_threads` runs JavaScript in parallel OS threads — the only way to parallelize CPU-heavy work in Node (the event loop is single-threaded). Post JSON-serializable messages via `postMessage`, receive on `message` events.

```javascript
// worker.js
const { parentPort, workerData } = require("node:worker_threads");

// Heavy CPU work: count primes up to a limit
function primesUpTo(limit) {
  const sieve = new Uint8Array(limit + 1);
  let count = 0;
  for (let i = 2; i <= limit; i++) {
    if (!sieve[i]) {
      count++;
      for (let j = i * i; j <= limit; j += i) sieve[j] = 1;
    }
  }
  return count;
}

parentPort.on("message", (msg) => {
  const result = primesUpTo(msg.limit);
  parentPort.postMessage({ id: msg.id, count: result });
});
```

```javascript
// main.js
const { Worker } = require("node:worker_threads");
const path = require("node:path");

const CPUS = 4;
const LIMIT = 100_000_000;
const per = Math.ceil(LIMIT / CPUS);
const done = [];

async function run() {
  const jobs = Array.from({ length: CPUS }, (_, i) => {
    return new Promise((resolve, reject) => {
      const worker = new Worker(path.join(__dirname, "worker.js"));
      const lo = i * per + 1;
      const hi = Math.min((i + 1) * per, LIMIT);
      worker.postMessage({ id: i, limit: hi });
      worker.on("message", (m) => {
        done[m.id] = m.count;
        worker.terminate();
        resolve();
      });
      worker.on("error", reject);
    });
  });
  await Promise.all(jobs);
  console.log("total primes:", done.reduce((a, b) => a + b, 0));
}

run().catch((err) => { console.error(err); process.exit(1); });
```

Gotchas:
- `postMessage` uses structured clone — functions, symbols, and class instances are NOT transferable.
- Each worker has its own V8 heap; sharing memory requires `SharedArrayBuffer` (with matching `Atomics` for sync).
- Spawning a worker per task is expensive (~tens of ms + memory) — use a pool that reuses workers for many tasks.
- Register `parentPort.on("message")` in the worker script before long-running work; and `worker.terminate()` when done to free the thread.
- Don't use workers for I/O (network/disk) — the event loop handles those better; workers are for CPU-bound math, parsing, hashing, image processing.
- Errors in the worker surface on the main thread via `worker.on("error")`; unhandled rejections inside workers need their own handler.
