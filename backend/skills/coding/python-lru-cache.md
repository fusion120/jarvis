---
lang: python
keywords: lru, cache, eviction, OrderedDict, functools, memoize, caching, cache, most recent
---

# Building an LRU cache from scratch

A Least-Recently-Used cache evicts the entry that was touched longest ago. `OrderedDict` keeps
insertion order and can move any key to the end in O(1), so it's the perfect primitive: every
`get`/`put` marks the key most-recently-used, and eviction pops the front.

```python
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self._store: OrderedDict[str, int] = OrderedDict()

    def get(self, key: str) -> int | None:
        if key not in self._store:
            return None
        self._store.move_to_end(key)            # touch -> most recently used
        return self._store[key]

    def put(self, key: str, value: int) -> None:
        if key in self._store:
            self._store.move_to_end(key)        # update + refresh freshness
        self._store[key] = value
        if len(self._store) > self.capacity:
            self._store.popitem(last=False)     # evict least-recently used


cache = LRUCache(2)
cache.put("a", 1)
cache.put("b", 2)
cache.get("a")                                  # "b" is now the LRU entry
cache.put("c", 3)                               # evicts "b"
print("b ->", cache.get("b"))                   # None
print("a ->", cache.get("a"))                   # 1
print("c ->", cache.get("c"))                   # 3
```

Gotchas:
- `popitem(last=False)` pops the *first* (oldest) entry; `last=True` (the default) pops the
  newest — evicting the wrong end turns it into an MRU cache.
- On `put` of an existing key you must `move_to_end` *before* assigning, or the overwritten
  key keeps its old position and eviction order is wrong.
- For one-liner caching in real code, prefer `functools.lru_cache` — it handles hashing,
  exceptions, and eviction stats for you; hand-roll only when you need custom keys or eviction.
- A hand-rolled cache keyed on unhashable args (lists, dicts) breaks — key on a normalized
  tuple or use `repr`.
- This version is not thread-safe; guard `get`/`put` with a lock if worker threads share it.
- `get` returning `None` conflates "missing" with "cached None" — return a sentinel or use
  `KeyError` if cached-None is a real value in your domain.
