---
lang: javascript
keywords: symbol, Symbol.iterator, well-known symbols, Symbol.for, unique key, iterator protocol, Symbol.toStringTag, symbol properties, enum-like, property key
---

# Symbol & iterator protocol

`Symbol` creates unique, non-string property keys; well-known symbols like `Symbol.iterator` are the hooks that make objects usable with `for...of`, spread, and `...rest`. Reach for symbols for collision-free keys and for custom iteration behavior.

```javascript
// Unique keys: two symbols never collide
const idA = Symbol("id");
const idB = Symbol("id");
console.log(idA === idB);                 // false

const user = { name: "ada" };
user[idA] = 1001;                          // invisible to normal APIs
console.log(Object.keys(user));            // ["name"] — symbol keys skipped
console.log(user[idA]);                    // 1001

// Symbol.for: shared global registry
const g1 = Symbol.for("app.version");
const g2 = Symbol.for("app.version");
console.log(g1 === g2);                    // true (same registry entry)

// Symbol.iterator: make a custom collection iterable
class Tags {
  #tags = new Set();
  add(t) { this.#tags.add(t); return this; }
  *[Symbol.iterator]() { yield* this.#tags; }
}
const t = new Tags().add("js").add("node").add("js");
console.log([...t]);                       // ["js", "node"] — Set dedupes

// Symbol.iterator also powers object spread-free for..of
const iterable = {
  *[Symbol.iterator]() { yield 1; yield 2; },
};
console.log([...iterable]);                // [1, 2]

// Symbol.toStringTag / Symbol.hasInstance — customize built-in behavior
class Widget { get [Symbol.toStringTag]() { return "Widget"; } }
console.log(Object.prototype.toString.call(new Widget())); // [object Widget]
```

Gotchas:
- Symbol-keyed properties are skipped by `Object.keys`, `JSON.stringify`, `for...in`, and spread — good for metadata, bad if you expected serialization.
- `Object.getOwnPropertySymbols()` finds them, `Reflect.ownKeys` shows all keys.
- `Symbol("x")` ≠ `Symbol("x")` (local), but `Symbol.for("x")` is global/shared — pick deliberately.
- Symbols aren't auto-stringified in templates: `` `id ${idA}` `` throws TypeError without `String(idA)`.
- An object whose `Symbol.iterator` returns a non-iterator throws at `next()` time, not at spread time.
- Symbols are not strings — where a string key is expected, use `String(sym)`/`sym.toString()` explicitly.
