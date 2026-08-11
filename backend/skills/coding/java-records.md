---
lang: java
keywords: record, immutable data, data carrier, compact constructor, accessor, value object, record class, wither
---

# Records: Immutable Data Carriers

A `record` gives you a constructor, accessors, `equals`/`hashCode`, and `toString` for free from just the component list. Reach for records for DTOs, value objects, and immutable config carriers. A *compact constructor* lets you validate or normalize before the object exists.

```java
public class RecordsDemo {
    // compact constructor validates on construction
    record Point(int x, int y) {
        Point {
            if (x < 0 || y < 0) throw new IllegalArgumentException("non-negative only");
        }
        double distanceTo(Point o) {
            return Math.hypot(x - o.x, y - o.y);
        }
        // static factory can return a "default" without allocation concerns
        static Point origin() { return new Point(0, 0); }
    }

    record Range(int from, int to) {
        Range {
            if (from > to) throw new IllegalArgumentException("from <= to");
        }
    }

    public static void main(String[] args) {
        Point a = Point.origin();
        Point b = new Point(3, 4);
        System.out.println(a + " distance=" + a.distanceTo(b));
        System.out.println("equals/hashCode auto: " + a.equals(new Point(0, 0)));
        System.out.println("accessor: " + b.x() + "," + b.y());

        try {
            new Point(-1, 5);
        } catch (IllegalArgumentException e) {
            System.out.println("rejected: " + e.getMessage());
        }
    }
}
```

Gotchas:
- Records are shallowly immutable: a `record R(List<String> xs)` can still be mutated via the list — copy/`List.copyOf` in the compact constructor for true immutability.
- Fields are implicitly `private final`, so there are no setters; update by creating a new record (or use the "wither" pattern).
- No `extends` clause is allowed, and no extra instance fields — only additional *methods* and static members.
- Accessors are `x()` not `getX()`; frameworks that require JavaBean getters (old Jackson/JPA) need adapters.
- The canonical constructor is package-private if the record is package-private; reflection `getDeclaredConstructor` can fail without `setAccessible`.
- Records are `final` and cannot be lazily cached — recompute derived values in methods or store them in a static map.
