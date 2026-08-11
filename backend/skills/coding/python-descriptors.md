---
lang: python
keywords: descriptor, __get__, __set__, property, validation, attribute, data descriptor, __set_name__
---

# Descriptors: attribute validation at the class level

A descriptor is an object assigned as a class attribute whose `__get__`/`__set__` run on every
instance access. It's the engine under `property`, `classmethod`, and `staticmethod`, and the
clean way to validate or coerce attribute values in one place.

```python
class Positive:
    def __init__(self, name: str):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:                      # accessed on the class, not an instance
            return self
        return obj.__dict__[self.name]

    def __set__(self, obj, value):
        if value <= 0:
            raise ValueError(f"{self.name} must be > 0, got {value}")
        obj.__dict__[self.name] = value


class Order:
    quantity = Positive("quantity")
    price = Positive("price")

    def __init__(self, quantity: float, price: float):
        self.quantity = quantity
        self.price = price

    def total(self) -> float:
        return self.quantity * self.price


order = Order(3, 4.5)
print(order.total())
try:
    Order(0, 5)
except ValueError as exc:
    print(exc)
```

Gotchas:
- Store the real value in `obj.__dict__` — assigning `self.value` inside `__set__` would
  recurse forever because the descriptor's `__set__` fires again.
- A descriptor that defines only `__get__` is a *non-data* descriptor: a plain instance
  attribute silently shadows it. Defining `__set__` makes it a data descriptor that wins.
- `__set_name__` (Python 3.6+) auto-fills the attribute name, so you don't need the
  `Positive("quantity")` explicit argument — use it in new code.
- Descriptors work on new-style classes and `object` subclasses only, not on `type` instances.
- A shared descriptor holds no per-instance state; if you keep state on the descriptor itself,
  every instance shares it — store per-instance state in `obj.__dict__`.
