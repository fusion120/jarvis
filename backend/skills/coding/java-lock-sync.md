---
lang: java
keywords: synchronized, reentrant lock, lock, tryLock, monitor, mutual exclusion, thread safety, unlock, critical section
---

# synchronized vs ReentrantLock

`synchronized` gives simple, structured mutual exclusion; `ReentrantLock` adds non-blocking `tryLock`, timeouts, fairness, and multiple condition queues. Use `synchronized` by default; reach for `ReentrantLock` when you need to back out of a lock acquisition or interrupt a blocked lock.

```java
import java.util.concurrent.*;
import java.util.concurrent.locks.*;

public class LockVsSync {
    static final Object MONITOR = new Object();
    static int syncCount = 0;

    static final ReentrantLock lock = new ReentrantLock();
    static int lockCount = 0;

    static void incrementSync() {
        synchronized (MONITOR) {
            syncCount++;
        }
    }

    static void incrementWithLock() {
        lock.lock(); // blocks indefinitely — same guarantee as synchronized
        try {
            lockCount++;
        } finally {
            lock.unlock(); // MUST be in finally or an exception leaks the lock
        }
    }

    public static void main(String[] args) throws Exception {
        int threads = 8, iters = 100_000;
        ExecutorService pool = Executors.newFixedThreadPool(threads);
        for (int t = 0; t < threads; t++) {
            pool.submit(() -> {
                for (int i = 0; i < iters; i++) {
                    incrementSync();
                    incrementWithLock();
                }
            });
        }
        pool.shutdown();
        pool.awaitTermination(30, TimeUnit.SECONDS);
        System.out.println("sync=" + syncCount + " lock=" + lockCount);

        // ReentrantLock-only: tryLock with timeout, no indefinite block
        if (lock.tryLock(1, TimeUnit.SECONDS)) {
            try {
                System.out.println("acquired non-blocking");
            } finally {
                lock.unlock();
            }
        } else {
            System.out.println("could not acquire — backing off");
        }
    }
}
```

Gotchas:
- `unlock()` must always be in a `finally` block; a thrown exception between `lock()` and `finally` leaves the lock held forever (deadlock).
- `ReentrantLock` is reentrant (a thread may acquire the same lock multiple times), but each `lock()` needs a matching `unlock()`.
- `synchronized` releases automatically on exception — one reason it's the safer default for simple critical sections.
- `tryLock` with timeout still throws `InterruptedException` — restore the interrupt flag if you catch it.
- Use `Lock` interfaces in fields (dependency-injectable); concrete `ReentrantLock` in a field couples code to one implementation.
- For read-heavy workloads prefer `ReentrantReadWriteLock`/`StampedLock` — a plain mutex serializes all readers. And remember `synchronized` can't be interrupted or timed out; use `lockInterruptibly()`/`tryLock(time)` for that.
