---
lang: java
keywords: optional, null safety, orElse, orElseGet, orElseThrow, flatMap, map, nullable, empty
---

# Optional: Safe Null Handling

Use `Optional` as a return type for methods that may legitimately produce no result — like lookup by ID — so callers must handle the absence. Chain `map`/`flatMap` to transform without null checks and finish with `orElse`, `orElseGet`, or `orElseThrow`.

```java
import java.util.*;

public class OptionalDemo {
    record User(String name, String email) {}

    private static final Map<String, User> DB = Map.of(
        "a1", new User("Ada", "ada@example.com"),
        "a2", new User("Grace", null));

    public static Optional<User> findById(String id) {
        return Optional.ofNullable(DB.get(id)); // DB.get may return null
    }

    public static void main(String[] args) {
        // map + orElse: transform safely, provide fallback
        String email = findById("a1")
            .map(User::email)
            .orElse("unknown@example.com");
        System.out.println(email);

        // orElseGet is LAZY — use it for expensive defaults
        User user = findById("nope").orElseGet(() -> new User("Guest", "guest@example.com"));

        // flatMap avoids Optional<Optional<...>>
        Optional<String> maybeEmail = findById("a2")
            .flatMap(u -> Optional.ofNullable(u.email()));

        // throw a meaningful exception instead of an NPE
        try {
            findById("missing").orElseThrow(() -> new NoSuchElementException("user not found"));
        } catch (NoSuchElementException e) {
            System.out.println("caught: " + e.getMessage());
        }

        // filter: keep only values that satisfy a condition
        Optional<User> withEmail = findById("a1")
            .filter(u -> u.email() != null);
        System.out.println(withEmail.isPresent());
    }
}
```

Gotchas:
- `Optional` is not `Serializable` — never store it in fields or pass it as a method argument; it's designed only for return types.
- `orElse(x)` evaluates `x` eagerly even when the value is present; use `orElseGet(Supplier)` for expensive defaults.
- Never call `get()` without an `isPresent()` guard — it throws `NoSuchElementException`; prefer `orElseThrow()`.
- `Optional.of(x)` throws `NullPointerException` on null — use `ofNullable` when the value may be null.
- `map` returns `Optional<U>` but if the mapper itself returns `Optional`, use `flatMap` to avoid nesting.
- `Optional` of boxed primitives is wasteful — use `OptionalInt`/`OptionalLong`/`OptionalDouble` for ranges and streams.
