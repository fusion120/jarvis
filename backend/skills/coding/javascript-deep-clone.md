---
lang: javascript
keywords: deep clone, structuredClone, deep copy, shallow copy, JSON.parse JSON.stringify, clone object, circular reference, Map Set, clone array, immutable
---

# Deep cloning

`structuredClone` (Node 17+/modern browsers) deep-copies arbitrary values including `Map`, `Set`, `Date`, typed arrays, and circular references. Reach for it instead of the `JSON.parse(JSON.stringify(x))` hack, which mangles dates, functions, and cycles.

```javascript
// structuredClone: the modern answer
const original = {
  name: "state",
  updatedAt: new Date(),
  counts: new Map([["a", 1]]),
  tags: new Set(["x", "y"]),
  nested: { arr: [1, 2, { deep: true }] },
};
original.self = original;              // circular reference

const clone = structuredClone(original);
clone.nested.arr[2].deep = false;      // mutate the clone
clone.counts.set("a", 99);

console.log(original.nested.arr[2].deep); // true  — original untouched
console.log(original.self === original);   // true  (cycle preserved)
console.log(clone.self === clone);         // true
console.log(clone.updatedAt instanceof Date); // true — not a string

// Fallback when structuredClone is unavailable (old engines):
function deepClone(v, seen = new Map()) {
  if (v === null || typeof v !== "object") return v;
  if (seen.has(v)) return seen.get(v);
  if (v instanceof Date) return new Date(v.getTime());
  if (v instanceof RegExp) return new RegExp(v.source, v.flags);
  const copy = Array.isArray(v) ? [] : {};
  seen.set(v, copy);
  for (const [k, val] of Object.entries(v)) copy[k] = deepClone(val, seen);
  return copy;
}
console.log(deepClone({ a: [1, { b: 2 }] }));
```

Gotchas:
- `JSON.parse(JSON.stringify(x))` fails on `undefined`/`function`/`Symbol` values, `Date` (becomes string), `Map`/`Set` (become `{}`), and throws on circular refs — never use it for state you control.
- `structuredClone` does NOT clone functions, DOM nodes, or class instances with private fields (throws `DataCloneError`) — those need manual copying.
- `structuredClone` doesn't run class constructors — custom-class prototypes are lost (result is a plain object).
- Object spread `{...x}` is shallow: nested arrays/objects stay shared — mutating a nested field mutates the original.
- `Object.assign({}, x)` is also shallow and triggers getters while copying.
- For immutable updates prefer spread + targeted overrides over cloning whole trees; cloning every render is a perf trap.
