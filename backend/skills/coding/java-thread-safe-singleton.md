---
lang: java
keywords: singleton, thread safe, enum, double checked locking, volatile, lazy init, getInstance, readResolve
---

# Thread-Safe Singleton

The enum singleton is the simplest thread-safe, serialization-safe singleton — the JVM guarantees one instance. When you need lazy initialization of a heavyweight object with classic locking, use **volatile double-checked locking**: check outside the lock, take a local copy, synchronize, re-check, publish through a `volatile` field.

```java
import java.util.concurrent.*;

public class ThreadSafeSingleton {
    // 1) enum singleton — recommended for most cases
    enum Holder {
        INSTANCE;
        private final Database db = new Database();
        public Database db() { return db; }
    }

    // 2) lazy double-checked locking
    static volatile Lazy lazy;

    static Lazy lazy() {
        Lazy local = lazy;          // read volatile once
        if (local == null) {        // fast path — no lock
            synchronized (ThreadSafeSingleton.class) {
                local = lazy;
                if (local == null) {          // slow path — re-check
                    local = new Lazy();
                    lazy = local;             // publish via volatile write
                }
            }
        }
        return local;
    }

    static class Database { }
    static class Lazy { }

    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(8);
        CountDownLatch start = new CountDownLatch(1);
        for (int i = 0; i < 8; i++) {
            pool.submit(() -> {
                try {
                    start.await();
                    Lazy l = lazy();
                    System.out.println(Thread.currentThread().getName() + " -> " + l);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            });
        }
        start.countDown();
        pool.shutdown();
        pool.awaitTermination(5, TimeUnit.SECONDS);
        System.out.println("enum instance: " + Holder.INSTANCE.db());
    }
}
```

Gotchas:
- Double-checked locking WITHOUT `volatile` is broken: another thread can observe the partially-constructed object (`new Lazy()` publishes the reference before the constructor finishes).
- Read the volatile into a local variable first — every `lazy` read is a memory barrier, so repeated reads defeat the optimization.
- The naive `synchronized` method singleton (`getInstance()` synchronized) is correct but serializes every call — DCL keeps the fast path lock-free.
- Eager static-field singletons initialize at class-load time; if construction is heavy or may fail, prefer the lazy forms or an enum.
- The enum singleton survives serialization and reflection attacks by construction; class-based singletons must implement `readResolve()` and handle reflection.
- "Singleton" is a global — it makes code hard to test (no clean dependency injection) and hard to parallelize; reach for it sparingly. And multiple classloaders (app servers, custom loaders) can each load the singleton class, producing multiple instances despite the pattern.
