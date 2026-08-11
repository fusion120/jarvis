---
lang: javascript
keywords: EventEmitter, events, on, emit, once, removeListener, event names, async events, max listeners, emitter patterns
---

# EventEmitter

`node:events` `EventEmitter` implements the publish/subscribe pattern: `emit` fires listeners registered with `on`/`once`. Reach for it to decouple producers from consumers — progress updates, plugin hooks, state-change broadcasts.

```javascript
const { EventEmitter } = require("node:events");

// A class that emits lifecycle events
class Downloader extends EventEmitter {
  async download(url) {
    this.emit("start", { url });
    for (let i = 1; i <= 5; i++) {
      await new Promise((r) => setTimeout(r, 10));
      this.emit("progress", { url, pct: i * 20 });
    }
    this.emit("end", { url, ok: true });
  }
}

const dl = new Downloader();

// Listeners
const onProgress = ({ pct }) => console.log(`${pct}%`);
dl.on("progress", onProgress);
dl.once("start", ({ url }) => console.log("starting", url)); // fires once
dl.on("end", ({ url }) => console.log("finished", url));

dl.download("https://cdn.example.com/big.bin");

// Error events: special semantic
class Job extends EventEmitter {
  run() { this.emit("error", new Error("job exploded")); }
}
const job = new Job();
job.on("error", (err) => console.error("handled:", err.message));
job.run();

console.log("listeners:", dl.listenerCount("progress")); // 1
```

Gotchas:
- An emitted `"error"` event with NO listener throws and CRASHES the process — always attach an error listener when you emit errors.
- `emit` is synchronous: listeners run in the emitter's stack, so a slow listener blocks everyone. Offload with `setImmediate` or `queueMicrotask` if needed.
- Exceptions inside one listener stop the rest from running and propagate up — wrap listener bodies in try/catch.
- `once` removes itself before calling — re-entrant `emit` while a listener runs is safe but order can surprise.
- Default max listeners is 10 per event; exceeding it logs a memory-leak warning — raise with `setMaxListeners` deliberately.
- `removeListener` requires the exact same function reference — pass named functions, not inline arrows, when you plan to remove them.
- Events work across threads too: worker `message`/`error` are EventEmitter-style on the `Worker` instance.
