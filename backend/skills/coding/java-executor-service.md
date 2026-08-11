---
lang: java
keywords: executor, thread pool, ExecutorService, future, submit, invokeAll, shutdown, callable
---

# ExecutorService & Thread Pools

Hand-crafting `new Thread` per task is wasteful; `Executors.newFixedThreadPool(n)` reuses a bounded set of worker threads. Submit `Callable`/`Runnable` tasks, collect `Future`s, then shut the pool down deterministically so your JVM can exit.

```java
import java.util.*;
import java.util.concurrent.*;

public class ExecutorServiceDemo {
    public static void main(String[] args)
            throws InterruptedException, ExecutionException, TimeoutException {
        ExecutorService pool = Executors.newFixedThreadPool(4);

        List<Callable<Integer>> tasks = new ArrayList<>();
        for (int i = 1; i <= 8; i++) {
            int n = i; // effectively final capture
            tasks.add(() -> {
                Thread.sleep(200);
                return n * n;
            });
        }

        // run all and wait for every result
        List<Future<Integer>> futures = pool.invokeAll(tasks);
        long sum = 0;
        for (Future<Integer> f : futures) {
            sum += f.get(); // blocks; throws ExecutionException if the task failed
        }
        System.out.println("sum of squares = " + sum);

        // single task with a timeout so a hung task can't stall us
        Future<String> f = pool.submit(() -> {
            Thread.sleep(50);
            return "done";
        });
        System.out.println(f.get(1, TimeUnit.SECONDS));

        pool.shutdown(); // stop accepting new work, drain the queue
        if (!pool.awaitTermination(5, TimeUnit.SECONDS)) {
            pool.shutdownNow(); // interrupt running tasks
        }
        System.out.println("pool stopped");
    }
}
```

Gotchas:
- Always `shutdown()` when done, or non-daemon pool threads keep the JVM alive forever.
- `shutdown()` lets queued tasks run; `shutdownNow()` interrupts running tasks and returns the unstarted ones — pick per requirement.
- Never share a single `Executors.newCachedThreadPool()` for bursty workloads without limits; it creates unbounded threads.
- `Future.get()` blocks and rethrows task exceptions as `ExecutionException` (wrapping the real cause) — unwrap with `.getCause()`.
- Submitting from within tasks to the same fixed pool can deadlock if the queue fills and threads wait on `get()` of tasks that can't run.
- Prefer `ExecutorService` over raw threads; for one-shot async work, `Executors.newSingleThreadExecutor()` or `CompletableFuture` are lighter.
