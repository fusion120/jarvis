---
lang: javascript
keywords: Object.entries, Object.fromEntries, object to array, transform object, key value, pick, omit, mapValues, invert, count by, group
---

# Object transforms with entries/fromEntries

`Object.entries` converts an object to `[key, value]` pairs (array-land where `map`/`filter`/`reduce` work); `Object.fromEntries` rebuilds an object from pairs. Together they make immutable object transformations a two-step pipeline.

```javascript
const users = {
  ada: { role: "admin", visits: 120 },
  bob: { role: "viewer", visits: 3 },
  cyd: { role: "admin", visits: 45 },
};

// pick: keep only chosen keys
const pick = (obj, keys) =>
  Object.fromEntries(keys.filter((k) => k in obj).map((k) => [k, obj[k]]));
console.log(pick(users, ["ada"]));            // { ada: {...} }

// omit: drop keys
const omit = (obj, keys) =>
  Object.fromEntries(Object.entries(obj).filter(([k]) => !keys.includes(k)));

// mapValues: transform values, keep keys
const visits = Object.fromEntries(
  Object.entries(users).map(([name, u]) => [name, u.visits])
);
console.log(visits);                          // { ada: 120, bob: 3, cyd: 45 }

// invert: swap keys/values (collisions keep the LAST)
const invert = (obj) =>
  Object.fromEntries(Object.entries(obj).map(([k, v]) => [v, k]));

// Count occurrences
const words = ["js", "node", "js", "sql", "js"];
const counts = words.reduce((acc, w) => ({ ...acc, [w]: (acc[w] ?? 0) + 1 }), {});
console.log(counts);                          // { js: 3, node: 1, sql: 1 }

// Filter by value
const admins = Object.fromEntries(
  Object.entries(users).filter(([, u]) => u.role === "admin")
);
console.log(Object.keys(admins));             // ["ada", "cyd"]

// Sorted by value (toSorted copies, ES2023)
const byVisits = Object.fromEntries(
  Object.entries(visits).toSorted(([, a], [, b]) => b - a)
);
console.log(byVisits);                        // { ada: 120, cyd: 45, bob: 3 }
```

Gotchas:
- Keys are ALWAYS strings in `Object.entries` — a key `10` becomes `"10"`, and integer-like keys are ordered first (ascending) regardless of insertion.
- `Object.fromEntries` keeps the LAST pair for duplicate keys; dedupe before rebuilding.
- `Object.entries` only sees own enumerable string keys — symbol keys and inherited props are skipped (usually what you want).
- Spread/`fromEntries` are shallow: values that are objects are shared references.
- Use `?? 0`, not `|| 0`, when counting — `|| 0` resets on any falsy value (0, "", null).
- Getters are invoked during `entries` — transforming an object with lazy getters runs them.
- For huge objects, transforming via arrays copies everything — fine for typical data, not for hot paths.
