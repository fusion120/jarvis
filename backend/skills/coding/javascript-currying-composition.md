---
lang: javascript
keywords: currying, compose, pipe, function composition, partial application, unary, point-free, higher order function, functional
---

# Currying & composition

Currying turns `f(a, b)` into `f(a)(b)` — each call returns a function waiting for the next argument. Composition (or piping) chains unary functions so output of one feeds the next. Use both to build small, testable transforms that read left-to-right.

```javascript
// Curried function: configurable prefix + value
const logWith = (prefix) => (level) => (msg) => `${prefix} [${level}] ${msg}`;
const consoleLog = logWith("app");        // app is captured now
const info = consoleLog("info");          // level captured
console.log(info("started"));             // "app [info] started"
console.log(consoleLog("error")("boom")); // "app [error] boom"

// curry a normal function
function curry(fn, arity = fn.length) {
  return function curried(...args) {
    if (args.length >= arity) return fn(...args);
    return (...more) => curried(...args, ...more);
  };
}
const add = curry((a, b, c) => a + b + c);
console.log(add(1)(2)(3));                // 6
console.log(add(1, 2)(3));                // 6

// pipe: left-to-right composition
const pipe = (...fns) => (input) => fns.reduce((acc, fn) => fn(acc), input);
const trim = (s) => s.trim();
const slug = (s) => s.toLowerCase().replace(/\s+/g, "-");
const shout = (s) => s.toUpperCase() + "!";
const process = pipe(trim, slug, shout);

console.log(process("  Hello World  "));  // "hello-world!"

// compose: right-to-left
const compose = (...fns) => (input) => fns.reduceRight((acc, fn) => fn(acc), input);
const double = (n) => n * 2;
const inc = (n) => n + 1;
console.log(compose(double, inc)(3));     // 8 — inc runs first, then double
```

Gotchas:
- Argument ORDER matters: `compose(f, g)(x)` is `f(g(x))`; `pipe(f, g)(x)` is `g(f(x))`. Pick one and document it.
- Curry with `fn.length` breaks on default/rest parameters (length becomes 0 or excludes them) — pass arity explicitly for those.
- Currying doesn't work with variadic functions (`...args`); define the fixed arity first.
- Per-call `curried` allocates closures — fine for typical sizes, but don't curry in hot inner loops needlessly.
- Composition works best with unary functions; multi-arg functions need currying/partial application first.
- `this` is lost across composed/curried boundaries — use arrow functions or bind.
- Debugging composed pipelines is hard — add a `tap` step `(x) => (console.log(x), x)` between stages.
