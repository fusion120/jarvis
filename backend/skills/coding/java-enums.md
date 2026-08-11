---
lang: java
keywords: enum, enumerations, state machine, constant specific, values, ordinal, switch, valueOf, enum map
---

# Advanced Enums

Enums are more than named constants: they can carry fields, implement behavior, and (with constant-specific bodies) form a tiny *state machine* where each constant decides what happens next. Use `values()`, `name()`/`toString()`, `valueOf`, and your own lookup method instead of comparing stringly-typed values.

```java
public class EnumsAdvanced {
    // enum as a state machine: each constant defines its own transition
    enum Status {
        PENDING("submitted", "NEW") {
            Status advance() { return ACTIVE; }
        },
        ACTIVE("in progress", "OPEN") {
            Status advance() { return CLOSED; }
        },
        CLOSED("done", "DONE") {
            Status advance() { return CLOSED; } // terminal state
        };

        private final String label;
        private final String code;

        Status(String label, String code) {
            this.label = label;
            this.code = code;
        }

        abstract Status advance();

        String label() { return label; }
        String code() { return code; }

        static Status fromCode(String c) {
            for (Status s : values()) {
                if (s.code.equals(c)) return s;
            }
            throw new IllegalArgumentException("unknown code: " + c);
        }
    }

    public static void main(String[] args) {
        Status s = Status.fromCode("OPEN");
        System.out.println(s + " (" + s.label() + ") advances to " + s.advance());

        for (Status st : Status.values()) {
            System.out.println(st.ordinal() + " " + st.code() + " " + st.label());
        }

        // switch over an enum is exhaustive-friendly (default still optional)
        switch (Status.ACTIVE) {
            case PENDING -> System.out.println("not started");
            case ACTIVE -> System.out.println("working");
            case CLOSED -> System.out.println("finished");
        }
    }
}
```

Gotchas:
- Enum constructors cannot access *static* fields (including other constants) — initialization order makes it illegal; pass everything as constructor args.
- `ordinal()` is position-dependent — if you reorder or insert constants, persisted ordinals/`switch` indexes shift. Prefer explicit `code`/`id` fields for anything stored.
- `name()` is fixed at compile time and refactoring-unsafe; `toString()` can be overridden for display text while `name()` stays for identity.
- Constant-specific bodies mean each constant is a subclass — you can't instantiate `Status` directly, and `getDeclaringClass()` is how you compare "which enum" generically.
- `valueOf("missing")` throws `IllegalArgumentException` (an exception for a lookup); a custom `fromCode` returning `Optional` or a sentinel is friendlier for unknown input.
- `switch` over enums with a `default` hides future constants — prefer exhaustive `case` lists for sealed-like safety. Enums are singletons per classloader, but serialized enums must keep their names stable across versions.
