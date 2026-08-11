---
lang: python
keywords: factory, strategy, singleton, observer, design pattern, ABC, abstractmethod, OOP, registry
---

# OOP design patterns: factory + strategy

Patterns are canned structures for recurring problems. The factory + strategy pair is the most
used: a strategy interface defines an algorithm, concrete classes implement it, and a factory
picks the right one from a name.

```python
from abc import ABC, abstractmethod


class PriceCalculator(ABC):
    @abstractmethod
    def total(self, subtotal: float) -> float:
        ...


class Standard(PriceCalculator):
    def total(self, subtotal: float) -> float:
        return subtotal


class Loyalty(PriceCalculator):
    def total(self, subtotal: float) -> float:
        return subtotal * 0.9


class Bulk(PriceCalculator):
    def __init__(self, min_qty: int = 10, discount: float = 0.8):
        self.min_qty = min_qty
        self.discount = discount

    def total(self, subtotal: float) -> float:
        return subtotal * self.discount


CALCULATORS = {"standard": Standard, "loyalty": Loyalty, "bulk": Bulk}


def make_calculator(kind: str) -> PriceCalculator:
    try:
        return CALCULATORS[kind]()
    except KeyError:
        raise ValueError(f"unknown pricing tier: {kind}") from None


for kind in ("standard", "loyalty", "bulk"):
    calc = make_calculator(kind)
    print(f"{kind:8s} -> {calc.total(100.0):.2f}")
```

Gotchas:
- An ABC with `@abstractmethod` cannot be instantiated — if you get `TypeError: Can't
  instantiate abstract class`, a subclass forgot to implement a method.
- Don't build strategy instances in a big `if/elif`; a name-to-class dict is data, easier to
  extend and test.
- For a thread-safe singleton, guard creation with a `threading.Lock`; Python's GIL does not
  make a double-checked instantiation race-free.
- Observer pattern: keep subscribers in a set and iterate a copy (`tuple(subscribers)`) so a
  subscriber can unsubscribe during notification.
- Factories returning subclasses should be annotated with the base type; callers then rely on
  the interface, not the concrete class.
