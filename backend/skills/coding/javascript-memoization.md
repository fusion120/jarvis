---
lang: javascript
keywords: memoization, cache, memoize, lru, function cache, expensive call, recursion memo, Map, optimization, pure function
---

# Memoization

Memoization caches a pure function's results by its arguments so repeated calls are O(1) lookups. Reach for it for recursion that recomputes subtrees (Fibonacci, edit distance) and for expensive lookups called in loops — but only for pure, deterministic functions.

```javascript
// Generic memoize: caches by the stringified argument list
function memoize(fn, keyFn = (...args) => JSON.stringify(args)) {
  const cache = new Map();
  return function (...args) {
    const key = keyFn(...args);
    if (cache.has(key)) return cache.get(key);
    const value = fn.apply(this, args);
    cache.set(key, value);
    return value;
  };
}

// Recursive Fibonacci — exponential without memo, linear with it
const fib = memoize((n) => (n < 2 ? n : fib(n - 1) + fib(n - 2)));
console.log(fib(40));                    // 102334155, instant

// Object-argument cache: key by a field, not the object identity
const expensive = memoize(
  ({ userId }) => `data-${userId}`,
  (o) => o.userId
);
console.log(expensive({ userId: 7, ignore: true }));
console.log(expensive({ userId: 7 }));   // cache hit (same key)

// LRU-ish with a size cap so the cache can't grow forever
function memoizeLimited(fn, { max = 100, keyFn = (a) => JSON.stringify(a) } = {}) {
  const cache = new Map();               // Map preserves insertion order
  return function (...args) {
    const key = keyFn(...args);
    if (cache.has(key)) {
      const v = cache.get(key);
      cache.delete(key);                 // refresh LRU position
      cache.set(key, v);
      return v;
    }
    const value = fn.apply(this, args);
    cache.set(key, value);
    if (cache.size > max) cache.delete(cache.keys().next().value); // evict oldest
    return value;
  };
}
```

Gotchas:
- Only memoize PURE functions: if it reads mutable state, the clock, or I/O, a cached result goes stale.
- The default `JSON.stringify` key collides for `undefined` and functions, and different key orders (`{a:1,b:2}` vs `{b:2,a:1}`) produce different keys — pass a stable `keyFn`.
- Unbounded caches leak memory — cap with LRU semantics (Map + delete/re-set) or a TTL.
- Recursive memoization requires the memoized reference inside the body (as above) or the recursion bypasses the cache.
- `this`-dependent methods need `.apply(this, args)` (done above); arrow-style callers lose `this`.
- Cache eviction/staleness is YOUR job — there's no built-in TTL; invalidate keys when data changes.
- A per-instance cache is fine; a shared global cache across callers can mix domains.
