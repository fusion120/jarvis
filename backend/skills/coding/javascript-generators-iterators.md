---
lang: javascript
keywords: generator, function*, yield, iterator, iterable, Symbol.iterator, for of, generator delegation, infinite sequence, next value done
---

# Generators & iterators

Generators (`function*`) are functions you can pause and resume — each `yield` emits a value, `next()` pulls the next. They build lazy sequences, custom iterables, and state machines without callbacks.

```javascript
// Lazy range: no array allocated until iterated
function* range(start, end, step = 1) {
  for (let i = start; i < end; i += step) yield i;
}

const r = range(1, 6);
console.log(r.next().value);      // 1
console.log([...range(1, 6)]);    // [1,2,3,4,5]  (spread consumes)

// Infinite sequence — safe because it's lazy
function* fib() {
  let a = 0, b = 1;
  while (true) { yield a; [a, b] = [b, a + b]; }
}
const take = (n, gen) => Array.from({ length: n }, () => gen.next().value);
console.log(take(8, fib()));      // [0,1,1,2,3,5,8,13]

// Delegation: yield* forwards to another iterable
function* all(...iters) {
  for (const it of iters) yield* it;
}
console.log([...all([1, 2], range(3, 5))]);   // [1,2,3,4]

// Custom iterable via Symbol.iterator
const lines = {
  text: "a\nb\nc",
  *[Symbol.iterator]() { yield* this.text.split("\n"); },
};
for (const line of lines) console.log(line);  // a b c

// Bidirectional communication: send values into next()
function* ask() {
  const name = yield "what is your name?";
  return `hello ${name}`;
}
const g = ask();
console.log(g.next().value);      // "what is your name?"
console.log(g.next("ada").value); // "hello ada"
```

Gotchas:
- Calling a generator does NOT run it — it returns an iterator object; the body starts on the first `next()`.
- Generators can't `yield` inside arrow functions or `.map` callbacks — use `function*`.
- `yield*` flattens nested iterables; plain `yield` of an array yields the array itself.
- Iterators are single-pass: you can't reset them; re-create the generator.
- `.return()`/`.throw()` exist on the iterator for cleanup/error injection — call `.return()` to run `finally` blocks.
- Spreading an infinite generator hangs forever; cap with `take`/`slice`-style helpers.
