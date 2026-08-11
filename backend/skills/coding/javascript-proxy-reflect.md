---
lang: javascript
keywords: proxy, reflect, get trap, set trap, validation, metaprogramming, reactive, observable, private underscore, revocable, invariant
---

# Proxy & Reflect

`Proxy` wraps an object and intercepts fundamental operations (get/set/has/delete/ownKeys) via traps; `Reflect` mirrors those traps as plain functions. Use them for validation, logging, lazy init, and reactivity — but keep handlers small and preserve invariants.

```javascript
// Property validation proxy
const target = { name: "ada", age: 36 };
const validated = new Proxy(target, {
  set(obj, prop, value) {
    if (prop === "age") {
      if (!Number.isInteger(value) || value < 0 || value > 150) {
        throw new RangeError("age must be 0..150");
      }
    }
    return Reflect.set(obj, prop, value);   // same as obj[prop]=value, returns bool
  },
  get(obj, prop) {
    if (prop in obj) return Reflect.get(obj, prop);
    throw new ReferenceError(`missing property: ${String(prop)}`);
  },
});

validated.age = 37;        // ok
// validated.age = 999;    // RangeError

// Logging / observable access
const log = [];
const observable = new Proxy({ count: 0 }, {
  get(obj, prop) { log.push(`get ${String(prop)}`); return Reflect.get(obj, prop); },
  set(obj, prop, val) {
    log.push(`set ${String(prop)}=${val}`);
    return Reflect.set(obj, prop, val);
  },
});
observable.count++;
console.log(log);          // ["get count", "set count=1", "get count"]

// Revocable proxy: can be turned off entirely
const { proxy: p, revoke } = Proxy.revocable(target, {});
revoke();
// p.name -> TypeError: cannot perform 'get' on a proxy that has been revoked

// Private-by-convention: hide underscore keys
const hidden = new Proxy(target, {
  has(obj, k) { return !String(k).startsWith("_") && k in obj; },
  get(obj, k) {
    if (String(k).startsWith("_")) throw new Error("private");
    return Reflect.get(obj, k);
  },
  ownKeys(obj) {
    return Reflect.ownKeys(obj).filter((k) => !String(k).startsWith("_"));
  },
});
console.log("name" in hidden);              // true
```

Gotchas:
- Traps must obey Proxy invariants — e.g. a non-configurable own property must still be reported by `ownKeys`/`getOwnPropertyDescriptor` or you get a TypeError.
- `set`/`deleteProperty` traps must return a boolean; returning `false` in strict mode throws a TypeError.
- `this` inside traps is the proxy, not the target — prefer the idiomatic `Reflect.get(obj, prop, receiver)` form.
- A proxy is a different object identity: `proxy === target` is false; some APIs and `instanceof` checks behave differently.
- Revoked proxies throw on every operation forever — use `Proxy.revocable` only for short-lived wrappers.
- Don't proxy hot paths — every trapped operation carries overhead.
