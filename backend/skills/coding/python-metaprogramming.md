---
lang: python
keywords: metaclass, metaprogramming, dynamic class, type, __init_subclass__, plugin registry, introspection, register
---

# Metaprogramming: plugin registry via metaclass

Metaclasses intercept class creation, so a base class can auto-register every subclass in a
plugin registry. This powers frameworks where new handlers "just work" without an import list.

```python
plugins = {}


class PluginMeta(type):
    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        if name != "BasePlugin":                  # skip the abstract base itself
            plugins[name.lower()] = cls
        return cls


class BasePlugin(metaclass=PluginMeta):
    def run(self) -> str:
        raise NotImplementedError


class Ping(BasePlugin):
    def run(self) -> str:
        return "pong"


class Echo(BasePlugin):
    def run(self) -> str:
        return "hello"


for name, cls in plugins.items():
    print(name, "->", cls().run())
```

Gotchas:
- `super().__new__` must be called first and its result returned, or the class is never created.
- The metaclass runs for *every* subclass creation, including the base itself — guard with a
  name check or a `register = False` class flag.
- Prefer `__init_subclass__` on the base class for simple registries: it runs per subclass
  without a metaclass, so it composes with other metaclass users.
- A metaclass must be a subclass of `type`; you cannot register an arbitrary class as a
  metaclass.
- `plugins` ordering follows definition order, which is import order — if imports are lazy,
  classes defined in never-imported modules won't register.
- You can also build classes dynamically with `type(name, bases, namespace)` — useful for
  generating many similar classes from data at runtime.
