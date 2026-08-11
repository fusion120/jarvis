---
lang: java
keywords: atomic, volatile, cas, atomicinteger, memory visibility, increment, compareAndSet, atomiclong, atomicboolean
---

# Atomics & Volatile

`volatile` guarantees *visibility* (a write is seen by other threads) but not *atomicity* — `i++` on a volatile int still races. `AtomicInteger`/`AtomicLong` give lock-free atomic compound operations via CAS (`compareAndSet`, `incrementAndGet`, `updateAndGet`). Use atomics for counters and flags; use locks for multi-step invariants.

```java
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

public class AtomicVolatile {
    static volatile boolean running = true; // visibility only
    static final AtomicLong counter = new AtomicLong(); // atomic ops

    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(8);
        for (int t = 0; t < 8; t++) {
            pool.submit(() -> {
                while (running) {           // volatile read — sees the stop flag
                    counter.incrementAndGet();
                    // CAS-style clamp: only applies if it doesn't go past 1_000_000
                    counter.updateAndGet(n -> Math.min(n, 1_000_000));
                }
            });
        }

        Thread.sleep(300);
        running = false;                    // volatile write — visible to all workers
        pool.shutdown();
        pool.awaitTermination(5, TimeUnit.SECONDS);
        System.out.println("final counter: " + counter.get());

        // getAndAdd: thread-safe "assign me the next slot"
        AtomicInteger slot = new AtomicInteger(0);
        int assigned = slot.getAndAdd(1);
        System.out.println("assigned slot " + assigned);

        // compareAndSet: claim a resource only if untouched
        AtomicBoolean claimed = new AtomicBoolean(false);
        boolean won = claimed.compareAndSet(false, true);
        System.out.println("claimed by me? " + won);
    }
}
```

Gotchas:
- `volatile` does NOT make read-modify-write atomic: two threads doing `x++` on a volatile `int` can both read the same value and lose an increment — use an atomic class.
- `volatile` is for flags/status and for publishing an immutable reference; it cannot protect invariants spanning multiple fields (use a lock).
- `AtomicLong` uses CAS in a retry loop under contention — high contention still burns CPU, so for extreme cases prefer `LongAdder` for counting.
- `updateAndGet`/`getAndUpdate` take a function that may run more than once (retries) — it must be side-effect-free and idempotent.
- The classic deadlock/race is check-then-act (`if (x==0) x=1`) — `compareAndSet` makes it a single atomic operation instead.
- `AtomicBoolean.compareAndSet(expect, update)` compares *references* — pass the same constant you stored, not a fresh `Boolean`. And without atomics or locks, even `long`/`double` reads on 32-bit JVMs can tear — atomics/`volatile` also fix that visibility.
