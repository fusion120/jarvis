---
lang: java
keywords: comparator, sort, comparing, thenComparing, reversed, naturalOrder, nullsLast, comparingInt, sort by field
---

# Sorting Collections with Comparators

`Comparator.comparing(...)` builds comparators declaratively and chains them with `thenComparing` for multi-key sorts. Reach for it whenever `Comparable`'s natural order isn't what the screen needs (reverse, null-first, secondary keys).

```java
import java.util.*;

public class ComparatorSorting {
    record Employee(String name, double salary, int years) {}

    public static void main(String[] args) {
        List<Employee> staff = new ArrayList<>(List.of(
            new Employee("Ada", 120_000, 5),
            new Employee("Grace", 90_000, 3),
            new Employee("Linus", 90_000, 12)));

        // salary desc, then years asc
        staff.sort(Comparator.comparingDouble(Employee::salary)
                             .reversed()
                             .thenComparingInt(Employee::years));
        System.out.println(staff);

        // null-safe ordering of strings
        List<String> names = new ArrayList<>(Arrays.asList("b", null, "a"));
        names.sort(Comparator.nullsLast(Comparator.naturalOrder()));
        System.out.println(names);

        // comparator for a Map by value
        Map<String, Integer> scores = new HashMap<>(Map.of("ada", 3, "grace", 9, "linus", 6));
        List<Map.Entry<String, Integer>> sorted = new ArrayList<>(scores.entrySet());
        sorted.sort(Map.Entry.comparingByValue());
        System.out.println(sorted);

        // custom key extractor
        List<String> words = new ArrayList<>(List.of("bb", "a", "ccc"));
        words.sort(Comparator.comparingInt(String::length));
        System.out.println(words);
    }
}
```

Gotchas:
- `Comparator.comparing` on a `double`/`int` field boxes — use `comparingDouble`/`comparingInt` for performance and to avoid NaN surprises on doubles.
- `reversed()` on a chain reverses the *whole* comparator built so far; to reverse only one key, invert that key's comparator (`comparing(x).reversed().thenComparing(y)`).
- Calling `.reversed()` twice on the same comparator is a no-op only if applied to the same instance — chaining order matters.
- Default `Comparable` fields must be non-null; use `nullsFirst`/`nullsLast` before natural-order comparators, or you get NPE at compare time.
- `TreeMap`/`TreeSet` use a comparator for *ordering* — if the comparator is inconsistent with `equals`, sets/maps can hold "duplicate" keys.
- `Comparator` should be consistent with `equals` when used in `SortedSet`/`SortedMap`, or lookups behave unexpectedly.
