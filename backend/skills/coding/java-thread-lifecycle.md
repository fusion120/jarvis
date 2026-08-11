---
lang: java
keywords: thread, runnable, join, interrupt, thread state, lifecycle, daemon, sleep, start
---

# Thread Lifecycle & Cooperative Interruption

A `Thread` moves NEW -> RUNNABLE -> (BLOCKED/WAITING/TIMED_WAITING) -> TERMINATED. `join()` lets one thread wait for another; interruption is a *cooperative* flag, not a kill switch — the interrupted thread must check it and clean up.

```java
public class ThreadLifecycle {
    public static void main(String[] args) throws InterruptedException {
        Runnable work = () -> {
            try {
                Thread.sleep(300);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt(); // restore the flag
            }
        };

        Thread t = new Thread(work, "worker");
        System.out.println("state after create: " + t.getState());   // NEW
        t.start();
        System.out.println("state after start: " + t.getState());    // RUNNABLE
        Thread.sleep(50);
        System.out.println("state while sleeping: " + t.getState()); // TIMED_WAITING
        t.join();                                                     // wait for death
        System.out.println("state after join: " + t.getState());     // TERMINATED

        // cooperative interruption: loop checks the flag
        Thread sleeper = new Thread(() -> {
            while (!Thread.currentThread().isInterrupted()) {
                try {
                    Thread.sleep(10_000);
                } catch (InterruptedException e) {
                    // sleeping was aborted; decide to exit
                    Thread.currentThread().interrupt();
                    System.out.println("interrupted, exiting loop");
                }
            }
        });
        sleeper.start();
        Thread.sleep(100);
        sleeper.interrupt();
        sleeper.join();
        System.out.println("sleeper finished");
    }
}
```

Gotchas:
- `getState()` is a snapshot, not a guarantee — a thread can change state between reading and using the value; never base synchronization decisions on it.
- An `InterruptedException` clears the interrupt flag — re-`interrupt()` in `catch` or the flag is lost and callers can't detect the interruption.
- `join()`/`sleep()` throw `InterruptedException`; if you catch it and swallow it, the thread can't stop cleanly.
- `start()` twice throws `IllegalThreadStateException`; `run()` called directly runs on the calling thread, not a new one.
- Spawning an unbounded number of threads is an anti-pattern — use an `ExecutorService` with a bounded pool.
- Daemon threads (`setDaemon(true)`) don't prevent JVM exit and can be killed mid-work; don't rely on them for critical cleanup.
