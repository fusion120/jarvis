---
lang: java
keywords: parallel stream, parallelstream, parallel, fork join, reduce, combiner, concurrency, parallel processing, split
---

# Parallel Streams

`.parallel()` splits the source across the common ForkJoin pool. It pays off only when the workload is CPU-bound, each element is expensive, and the reduction is *associative*. The `reduce` identity and combiner must satisfy the laws or you get silently wrong results.

```java
import java.util.*;
import java.util.stream.*;
import java.util.concurrent.ConcurrentHashMap;

public class ParallelStreams {
    static int heavy(int n) {
        // simulate a CPU-bound per-element cost
        return (int) (Math.sqrt(n * n + 1) * 1000);
    }

    public static void main(String[] args) {
        // CPU-bound filter+count — parallelizable
        long count = IntStream.rangeClosed(1, 10_000_000)
            .parallel()
            .filter(n -> n % 3 == 0)
            .count();
        System.out.println("multiples of 3: " + count);

        // associative reduce: identity + combiner MUST obey (a op b) op c == a op (b op c)
        int sum = IntStream.rangeClosed(1, 100)
            .parallel()
            .reduce(0, Integer::sum);
        System.out.println("sum: " + sum);

        // map + reduce with a parallel-safe collector
        int total = IntStream.rangeClosed(1, 1_000_000)
            .parallel()
            .map(ParallelStreams::heavy)
            .sum();
        System.out.println("heavy total: " + total);

        // concurrent collections avoid merge overhead
        Set<String> tags = List.of("a", "b", "c", "d")
            .parallelStream()
            .collect(Collectors.toCollection(ConcurrentHashMap::newKeySet));
        System.out.println(tags);
    }
}
```

Gotchas:
- The identity must be a true identity (`x op identity == x`) and the combiner must be associative; `(a,b) -> a-b` or `a-b` reduce gives wrong results silently.
- Parallelism is not free: tiny workloads pay more in split/merge overhead than they save — measure before sprinkling `.parallel()`.
- The common pool's parallelism equals CPU cores (configurable via `-Djava.util.concurrent.ForkJoinPool.common.parallelism=N`); blocking tasks in it starve other streams.
- Non-thread-safe mutable state inside lambdas (a shared `ArrayList`, a counter) races and corrupts — use `Collectors.toConcurrentMap` or `ConcurrentHashMap` instead.
- Order is not preserved: `findFirst` on a parallel stream still respects encounter order, but `forEach` doesn't — use `forEachOrdered` if order matters.
- `skip`/`limit` on parallel streams are O(n) and defeat the parallelism — pre-filter instead. And shared `Random` contends; use `ThreadLocalRandom` or `SplittableRandom`.
