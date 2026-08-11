---
lang: javascript
keywords: spread, rest operator, destructuring, object destructure, array destructure, default value, rename, rest props, shallow copy, parameter packing
---

# Spread, rest & destructuring

Spread (`...`) copies enumerable properties into a new object/array/arguments; rest gathers the leftovers in destructuring and function params. Reach for them to copy-with-update, extract named fields, and give functions flexible signatures.

```javascript
// Object spread: immutable update pattern
const base = { name: "Mimo", version: 3, env: "prod" };
const dev = { ...base, env: "dev" };              // override
const clone = { ...base };                        // shallow copy
console.log(base.env, dev.env);                   // prod dev

// Array spread + rest
const nums = [1, 2, 3];
const more = [...nums, 4, 5];                     // [1,2,3,4,5]
const [first, second, ...restNums] = more;        // first=1 restNums=[3,4,5]

// Destructuring with renames and defaults
const { name: title = "untitled", version, tags = [] } = dev;
const { env: environment, ...remaining } = dev;   // rest-object keeps the rest

// Function params: rest packs extra args
function sum(...values) {
  return values.reduce((a, b) => a + b, 0);
}
console.log(sum(1, 2, 3, 4));                     // 10

// Destructure in function params (options object pattern)
function connect({ host, port = 5432, ssl = false } = {}) {
  return `${host}:${port} ssl=${ssl}`;
}
console.log(connect({ host: "db.local", port: 5433 }));

// Swap without a temp variable
let a = 1, b = 2;
[a, b] = [b, a];

// Nested destructuring
const resp = { data: { user: { id: 7, profile: { nick: "ada" } } }, meta: {} };
const { data: { user: { id, profile: { nick } } } } = resp;
console.log(id, nick);                            // 7 ada
```

Gotchas:
- Spread is SHALLOW: nested objects/arrays are shared references; deep copies need `structuredClone`.
- Object spread order matters: later keys override earlier ones — put defaults first, overrides after.
- Rest must be last in destructuring or it's a syntax error; also only one rest per pattern.
- Destructuring `undefined`/`null` throws — use default parameters (`= {}`) and guard against null.
- `{ ...obj }` copies own enumerable props only: no prototype chain, and getters are invoked while setters are skipped.
- Array spread/rest works on iterables, but `...obj` on a plain object is a TypeError unless it has `Symbol.iterator` (use `Object.entries`).
