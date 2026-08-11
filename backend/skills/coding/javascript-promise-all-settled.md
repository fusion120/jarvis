---
lang: javascript
keywords: Promise.all, Promise.allSettled, Promise.any, Promise.race, parallel, fail fast, settle, aggregate results, concurrency
---

# Promise.all & Promise.allSettled

`Promise.all` waits for every promise and fails fast on the first rejection; `Promise.allSettled` waits for everything and reports each outcome. Choose by semantics: allSettled for batch jobs where partial failure is fine, all for fan-out where any failure should abort.

```javascript
const { setTimeout: sleep } = require("node:timers/promises");

const fetchIt = (id) => sleep(10).then(() => ({ id, ok: true }));

async function main() {
  // Promise.all: fail fast, single result array
  const results = await Promise.all([fetchIt(1), fetchIt(2), fetchIt(3)]);
  console.log(results.map((r) => r.id));        // [1, 2, 3]

  // Promise.allSettled: every outcome reported, no throw
  const mixed = [
    Promise.resolve("ok"),
    Promise.reject(new Error("boom")),
    Promise.resolve("ok2"),
  ];
  const outcomes = await Promise.allSettled(mixed);
  for (const o of outcomes) {
    if (o.status === "fulfilled") console.log("good:", o.value);
    else console.log("bad:", o.reason.message);
  }

  // Retry only the rejected ones
  const items = [1, 2, 3];
  const fn = async (it) => {
    if (it === 2) throw new Error(`fail on ${it}`);
    return it * 10;
  };
  let pending = items.map((it) => fn(it));
  for (let attempt = 0; attempt < 2; attempt++) {
    const settled = await Promise.allSettled(pending);
    const failed = settled
      .map((r, i) => (r.status === "rejected" ? i : -1))
      .filter((i) => i >= 0);
    if (failed.length === 0) break;
    pending = failed.map((i) => fn(items[i]));
  }
  console.log(await Promise.allSettled(pending)); // all fulfilled this time

  // Promise.any: first fulfillment wins
  try {
    const any = await Promise.any([fetchIt(1), fetchIt(2)]);
    console.log("any:", any.id);
  } catch (e) {
    console.log("any: all rejected", e.errors?.length);
  }
}

main().catch((err) => { console.error(err); process.exit(1); });
```

Gotchas:
- `Promise.all` rejects with the FIRST rejection and drops the rest — use `allSettled` if you still need the fulfilled results.
- `Promise.all` on an empty array resolves `[]`; `Promise.any` on an empty array rejects with `AggregateError`.
- `allSettled` always resolves — check `.status === "fulfilled"|"rejected"` and unwrap `.value`/`.reason`.
- Careful mixing `await Promise.all([a, b])` where `b` rejects — `a`'s work still runs, but its result is lost; fine unless `a` has side effects you must sequence.
- `Promise.any`'s rejection is an `AggregateError` with `.errors` — inspect that array, not `.message`.
- Don't `Promise.all` promises that were already started with side effects unless you want them all to run regardless.
