---
lang: java
keywords: completable future, async, supplyAsync, thenApply, thenCombine, exceptionally, join, thenCompose, non blocking
---

# CompletableFuture: Async Pipelines

`CompletableFuture` composes asynchronous steps into a dependency pipeline without blocking threads. Use `supplyAsync` for work off the calling thread, then chain `thenApply`, `thenCompose`, `thenCombine`, and `exceptionally` for branching, fan-in, and error recovery.

```java
import java.util.concurrent.*;

public class CompletableFutureDemo {
    static int fetchUserId() { sleep(100); return 42; }
    static int fetchScore(int userId) { sleep(150); return userId * 10; }

    static void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }

    public static void main(String[] args) throws Exception {
        // pipeline: id -> score -> +1, with a -1 fallback on any failure
        CompletableFuture<Integer> score = CompletableFuture.supplyAsync(CompletableFutureDemo::fetchUserId)
            .thenApplyAsync(CompletableFutureDemo::fetchScore)
            .exceptionally(ex -> { System.err.println("failed: " + ex); return -1; })
            .thenApply(s -> s + 1);

        // already-completed future
        CompletableFuture<Integer> cached = CompletableFuture.completedFuture(100);

        // combine two independent futures (fan-in)
        CompletableFuture<Integer> total = score.thenCombine(cached, Integer::sum);
        System.out.println("total = " + total.get(5, TimeUnit.SECONDS));

        // sequential composition where each step returns a future
        CompletableFuture<Integer> chained = CompletableFuture.completedFuture(1)
            .thenCompose(v -> CompletableFuture.supplyAsync(() -> v + 10))
            .thenCompose(v -> CompletableFuture.supplyAsync(() -> v * 2));
        System.out.println("chained = " + chained.join());

        // wait for several futures
        CompletableFuture.allOf(score, cached, chained).join();
        System.out.println("all done");
    }
}
```

Gotchas:
- `thenApply` runs on the same thread as its parent; `thenApplyAsync` jumps to the common ForkJoin pool — don't assume where chained code runs.
- `get()` blocks and throws checked exceptions; `join()` is unchecked — use `join()` when the exception should just propagate.
- `exceptionally` only fires on the *current* stage's failure; a failure earlier in the chain propagates until a stage handles it.
- Forget `thenCompose` and you get `CompletableFuture<CompletableFuture<T>>` — a classic accidental nesting bug.
- `thenCombine` (parallel, wait-both) vs `thenCompose` (sequential, depends-on) are different; mixing them up deadlocks or serializes wrongly.
- The common pool is sized to CPU cores; long-running blocking tasks should get a dedicated executor.
