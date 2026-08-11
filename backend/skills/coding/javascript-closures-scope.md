---
lang: javascript
keywords: closure, lexical scope, let vs var, hoisting, IIFE, module pattern, private variable, shadowing, counter, scope chain
---

# Closures & lexical scope

A closure is a function that remembers the variables from the scope where it was created, even after that scope exits. Reach for closures to hold private state (a counter, a cache, event-handler factories) without polluting globals, and to implement the module pattern.

```javascript
// Closure: a factory that captures private state
function createCounter(start = 0) {
  let count = start;               // private, only reachable via returned fns
  return {
    inc() { return ++count; },
    dec() { return --count; },
    get value() { return count; },
  };
}

const c = createCounter(10);
c.inc(); c.inc();
console.log(c.value);              // 12
console.log(typeof c.count);       // "undefined" — private

// Classic loop + closure gotcha, and the fix
const buttons = [];
for (var i = 0; i < 3; i++) {
  buttons.push(() => `button ${i}`);
}
console.log(buttons[0]());         // "button 3" — all share final i!

const fixed = [];
for (let j = 0; j < 3; j++) {      // let is per-iteration bound
  fixed.push(() => `button ${j}`);
}
console.log(fixed[0]());           // "button 0"

// Module pattern: one closure, public API only
const logger = (() => {
  const log = [];
  return { log: (m) => log.push(m), dump: () => [...log] };
})();
logger.log("hi");
console.log(logger.dump());        // ["hi"]

// Curried add via closure
const add = (a) => (b) => a + b;
console.log(add(2)(3));            // 5
```

Gotchas:
- `var` is function-scoped and hoisted; `let`/`const` are block-scoped. Prefer `let`/`const`.
- Loops with `var` capture the same binding — use `let` or an IIFE/`.bind()`.
- Closures keep the whole captured scope alive; don't close over huge objects in hot loops expecting GC.
- Arrow functions don't have their own `this` or `arguments`; they close over the enclosing ones.
- Each call to the outer function creates a fresh closure — state is not shared between instances.
