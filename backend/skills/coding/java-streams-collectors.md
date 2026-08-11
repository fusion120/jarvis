---
lang: java
keywords: stream, collectors, groupingBy, partition, map reduce, joining, toMap, collecting
---

# Streams & Collectors

Use the Stream API to transform and aggregate in-memory collections without writing loops. Reach for `Collectors.groupingBy`, `partitioningBy`, `toMap`, `summingInt`, and `joining` when you need SQL-like group-by/aggregate behavior over a `List` or `Set`.

```java
import java.util.*;
import java.util.stream.*;

public class StreamsCollectors {
    record Order(String product, int qty, String store) {}

    public static void main(String[] args) {
        List<Order> orders = List.of(
            new Order("apple", 10, "store-a"),
            new Order("apple", 5, "store-b"),
            new Order("banana", 20, "store-a"));

        // group by product and sum quantities
        Map<String, Integer> byProduct = orders.stream()
            .collect(Collectors.groupingBy(Order::product,
                                           Collectors.summingInt(Order::qty)));
        System.out.println(byProduct); // {banana=20, apple=15}

        // partition into "big" vs "small" orders
        Map<Boolean, List<Order>> partitioned = orders.stream()
            .collect(Collectors.partitioningBy(o -> o.qty() >= 10));
        System.out.println(partitioned.get(true));

        // join for display
        String joined = orders.stream()
            .map(o -> o.product() + "x" + o.qty())
            .collect(Collectors.joining(", ", "[", "]"));
        System.out.println(joined);

        // toMap with merge function for duplicate keys
        Map<String, String> storeOf = orders.stream()
            .collect(Collectors.toMap(Order::product, Order::store,
                                      (a, b) -> a + "+" + b));
        System.out.println(storeOf); // {apple=store-a+store-b, banana=store-a}

        // flatMap: flatten nested collections
        List<List<Integer>> grid = List.of(List.of(1, 2), List.of(3, 4));
        List<Integer> flat = grid.stream().flatMap(List::stream).toList();
        System.out.println(flat);
    }
}
```

Gotchas:
- `groupingBy` keys are compared with `equals` — mutable keys break the map. Prefer immutable keys.
- `Collectors.toMap` throws `IllegalStateException` on duplicate keys unless you pass a merge function; use the 3-arg form for dirty data.
- `toList()` (Java 16+) returns an unmodifiable list; `Collectors.toList()` returns a mutable `ArrayList`.
- Streams are single-use: calling a terminal operation twice on the same stream throws `IllegalStateException`. Recreate the stream.
- `IntStream`/`LongStream` use primitive `sum()/count()`, while `Stream<Integer>` needs `Collectors.summingInt` or `mapToInt(...).sum()`.
