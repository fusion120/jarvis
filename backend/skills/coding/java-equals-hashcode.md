---
lang: java
keywords: equals, hashcode, contract, hash set, hash map, Objects.equals, identity, value equality
---

# The equals/hashCode Contract

Override `equals` (value equality) and `hashCode` together: equal objects MUST have equal hash codes, or hash-based collections break — a `HashSet` can hold "duplicates" and `contains` returns false for an equal instance. `Objects.hash` and `Objects.equals` remove most boilerplate; records give you both for free.

```java
import java.util.*;

public class EqualsHashCode {
    static final class Money {
        private final String currency;
        private final int cents;

        Money(String currency, int cents) {
            this.currency = Objects.requireNonNull(currency);
            this.cents = cents;
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (!(o instanceof Money other)) return false;
            return cents == other.cents && currency.equals(other.currency);
        }

        @Override
        public int hashCode() {
            return Objects.hash(currency, cents);
        }

        @Override
        public String toString() {
            return currency + " " + cents;
        }
    }

    public static void main(String[] args) {
        Set<Money> wallet = new HashSet<>();
        wallet.add(new Money("USD", 100));

        // must find an equal-but-distinct instance
        System.out.println("contains equal: " + wallet.contains(new Money("USD", 100))); // true

        // hashCode consistency is required for this to work
        Map<Money, String> ledger = new HashMap<>();
        ledger.put(new Money("USD", 100), "deposit");
        System.out.println("map get: " + ledger.get(new Money("USD", 100)));

        // records implement both correctly, automatically
        record Point(int x, int y) {}
        Set<Point> points = new HashSet<>();
        points.add(new Point(1, 2));
        System.out.println("record contains: " + points.contains(new Point(1, 2)));
    }
}
```

Gotchas:
- Violating the contract (equal objects, unequal hashes) silently breaks `HashMap`, `HashSet`, and `containsKey` — no exception, just wrong answers.
- Use `Objects.equals` for fields that may be null — `a.equals(b)` on a null field NPEs.
- `hashCode` must be stable across the object's *life*: computing it from a mutable field means the object changes bucket after insertion (the classic "lost entry" bug).
- Use the *same fields* in `equals` and `hashCode`; omitting a field from one but not the other breaks the contract.
- `instanceof`-based equals (shown above) treats a subclass equal to a superclass — if you have inheritance, consider `getClass()` comparison instead, or prefer composition/records.
- Records/`Objects.hash` make correct code easy; hand-rolled hash functions mixing fields with `+`/`*` collide badly. And `equals` must be symmetric and reflexive — comparing against `null` must return false (the `instanceof` check handles it).
