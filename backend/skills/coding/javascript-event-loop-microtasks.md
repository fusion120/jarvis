---
lang: javascript
keywords: event loop, microtask, macrotask, queueMicrotask, setImmediate, process.nextTick, promise then, setTimeout 0, event loop phases, concurrency model
---

# Event loop & microtasks

Node and browsers run one thread with an event loop that interleaves macrotasks (timers, I/O, `setImmediate`) and microtasks (promise reactions, `queueMicrotask`). Knowing the ordering decides whether your code runs before or after I/O callbacks.

```javascript
const fs = require("node:fs");

// Run the ordering demo inside an I/O callback where phase order is stable.
fs.readFile(__filename, () => {
  console.log("1 sync inside I/O callback");

  process.nextTick(() => console.log("2 nextTick queue"));
  queueMicrotask(() => console.log("3 microtask"));
  Promise.resolve().then(() => console.log("4 promise.then"));

  setTimeout(() => console.log("5 timers (next iteration)"), 0);
  setImmediate(() => console.log("6 check phase"));

  console.log("microtasks drain here, before the loop advances");
});

// Expected order:
// 1, "microtasks drain…", 2 nextTick, 3 microtask, 4 promise.then,
// 5 timers, 6 check. nextTick beats microtasks; microtasks beat timers.
```

Gotchas:
- Microtasks (promise `.then`, `queueMicrotask`, `process.nextTick`) drain completely between each macrotask, so a long chain of `await`s can starve timers.
- `process.nextTick` runs before promise microtasks and before the loop advances — don't use it for async control flow (prefer `queueMicrotask`/`setImmediate`).
- `setTimeout(..., 0)` is not truly 0ms: it fires in the timers phase, after current sync code and microtasks.
- `setImmediate` vs `setTimeout(0)` ordering is nondeterministic at the top level of a module (depends on loop phase); it's stable inside an I/O callback (setImmediate wins).
- Event loop phases: timers → I/O callbacks → idle/prepare → poll → check (setImmediate) → close; I/O completions queue callbacks in poll.
- A `while (true)` sync loop blocks everything — the event loop is single-threaded.
