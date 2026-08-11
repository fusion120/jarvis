---
lang: python
keywords: dataclass, slots, frozen, asdict, field, dataclasses, namedtuple, immutable, class
---

# Dataclasses with slots and frozen for compact value objects

`@dataclass` removes boilerplate for classes that mainly carry data. `slots=True` stores
attributes in a compact fixed table instead of a per-instance dict (smaller, faster, typo-safe);
`frozen=True` makes the instance immutable so it can be hashed and shared safely.

```python
import dataclasses
from dataclasses import dataclass, field, asdict


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float
    label: str = field(default="origin", compare=False)

    def norm(self) -> float:
        return (self.x ** 2 + self.y ** 2) ** 0.5


p = Point(3, 4)
print(p.norm())
print(asdict(p))

try:
    p.x = 10
except dataclasses.FrozenInstanceError as exc:
    print("frozen:", exc)


@dataclass(slots=True)
class Team:
    name: str
    members: list[str] = field(default_factory=list)   # never use a mutable default!
```

Gotchas:
- Mutable defaults are rejected at class creation — use `field(default_factory=list)`, not
  `members: list = []`.
- `frozen=True` does not deep-freeze; a frozen dataclass holding a list can still be mutated
  through that list.
- `slots=True` classes cannot have attributes not declared in the class — a `self.extra = 1`
  in `__post_init__` raises `AttributeError` unless declared with `field(init=False)`.
- Inheriting slots dataclasses: the base must also use `slots=True`, or the subclass silently
  falls back to a dict.
- `field(compare=False)` excludes a field from equality; useful for ids, caches, or labels.
- For quick immutable value types you don't want to expand, `namedtuple` is the lightweight
  alternative; dataclasses win when you need validation, defaults, or methods.
