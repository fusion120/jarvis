---
lang: javascript
keywords: map, filter, reduce, array methods, forEach, find, some, every, sort, flatMap, groupBy
---

# Array methods: map/filter/reduce

`map`, `filter`, `reduce` (plus `find`, `some`, `every`, `flatMap`) transform arrays without mutating them and without index bookkeeping. Reach for them whenever you'd write a for-loop over an array — except when you need to `break` early or walk two arrays together.

```javascript
const orders = [
  { id: 1, user: "ada", total: 120, status: "paid" },
  { id: 2, user: "bob", total: 45, status: "pending" },
  { id: 3, user: "ada", total: 80, status: "paid" },
];

// map: same length, transformed
const ids = orders.map((o) => o.id);                  // [1, 2, 3]
const withVat = orders.map((o) => ({ ...o, total: Math.round(o.total * 1.2) }));

// filter: subset
const paid = orders.filter((o) => o.status === "paid");
const ada = orders.filter((o) => o.user === "ada");

// reduce: aggregate to anything
const revenue = orders
  .filter((o) => o.status === "paid")
  .reduce((sum, o) => sum + o.total, 0);              // 200

// groupBy (ES2024)
const byUser = Object.groupBy(orders, (o) => o.user); // { ada: [...], bob: [...] }

// find / some / every
const firstPending = orders.find((o) => o.status === "pending");
const hasRefund = orders.some((o) => o.total > 1000);
const allHaveId = orders.every((o) => Number.isInteger(o.id));

// flatMap: one-to-many flattening
const tags = orders.flatMap((o) => [o.user, o.status]);

// Chaining with a non-mutating sort (toSorted, ES2023)
const topPaid = orders
  .filter((o) => o.status === "paid")
  .toSorted((a, b) => b.total - a.total)
  .slice(0, 1);

console.log(revenue, ids, topPaid[0].id);
```

Gotchas:
- `reduce` without an initial value uses the first element — a bug on empty arrays (throws TypeError). Always pass the seed.
- `map`/`filter` return new arrays; they don't mutate. For in-place sort use `sort()` (mutates), `toSorted()` (copies).
- Don't `await` inside `map` — you get an array of promises; use `Promise.all(items.map(...))`.
- `filter(Boolean)` keeps `0`/`""` too — it's a truthiness check, not a null check; filter on the exact predicate you mean.
- `Object.groupBy` (ES2024) returns a null-prototype object — `toString` lookups behave differently; older runtimes need a reduce-based groupBy.
- `forEach` can't `break`/`return` early — use `some`/`find`/`every` for early exit.
