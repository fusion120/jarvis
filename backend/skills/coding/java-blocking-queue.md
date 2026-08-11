---
lang: java
keywords: blocking queue, producer consumer, put, take, poison pill, LinkedBlockingQueue, backpressure, bounded queue, offer poll
---

# BlockingQueue Producer-Consumer

A `BlockingQueue` is the standard hand-off point between producers and consumers: `put` blocks when full (bounded = backpressure), `take` blocks when empty. Use a poison pill (a sentinel value) to signal shutdown cleanly without thread interruption races.

```java
import java.util.concurrent.*;

public class ProducerConsumer {
    record Message(String payload) {}

    public static void main(String[] args) throws Exception {
        // bounded queue = backpressure: producer blocks when full
        BlockingQueue<Message> queue = new LinkedBlockingQueue<>(4);
        Message POISON = new Message("POISON");

        ExecutorService pool = Executors.newFixedThreadPool(2);

        // producer
        pool.submit(() -> {
            try {
                for (int i = 1; i <= 10; i++) {
                    queue.put(new Message("msg-" + i));
                    Thread.sleep(50);
                }
                queue.put(POISON); // sentinel: "no more work"
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        });

        // consumer
        pool.submit(() -> {
            try {
                while (true) {
                    Message m = queue.take(); // blocks while empty
                    if (m.equals(POISON)) break;
                    System.out.println(Thread.currentThread().getName() + " got " + m.payload());
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        });

        pool.shutdown();
        pool.awaitTermination(10, TimeUnit.SECONDS);
        System.out.println("done");
    }
}
```

Gotchas:
- `add`/`remove`/`element` throw exceptions when full/empty; `offer`/`poll` return a sentinel; only `put`/`take` block. Pick the semantics you need.
- A single poison pill only stops ONE consumer — broadcast it per consumer, or use `shutdownNow` + interruption for many workers.
- Interrupted consumers must restore the flag (`Thread.currentThread().interrupt()`) or the interrupt is silently swallowed.
- A bounded queue with a slow consumer is backpressure; an unbounded queue grows without limit and can OOM under bursts.
- Never `poll()` in a busy loop to emulate `take()` — you'll spin the CPU; use the blocking methods or `poll(timeout)`.
- Objects in the queue must not be mutated after being handed off, or consumers see torn state.
