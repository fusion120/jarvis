---
lang: python
keywords: queue, producer, consumer, threading, worker, thread safe, task_done, sentinel, pipeline
---

# Thread-safe producer-consumer with queue.Queue

The canonical work pipeline: one or more producer threads enqueue jobs, N worker threads
consume them. `queue.Queue` handles locking, blocking when full, and blocking when empty — you
never touch a `Lock` directly.

```python
import queue
import random
import threading
import time

q: queue.Queue = queue.Queue(maxsize=10)
N_CONSUMERS = 2
STOP = object()                          # sentinel: signals "no more work"


def producer(items):
    for item in items:
        q.put(item)                      # blocks while queue is full
        time.sleep(random.uniform(0.01, 0.05))
    for _ in range(N_CONSUMERS):         # one STOP per consumer
        q.put(STOP)


def consumer(name):
    while True:
        item = q.get()
        try:
            if item is STOP:
                break
            print(f"{name} handled {item}")
        finally:
            q.task_done()                # decrements the unfinished-task count


threads = [threading.Thread(target=producer, args=(range(20),))]
threads += [threading.Thread(target=consumer, args=(f"c{i}",)) for i in range(N_CONSUMERS)]

for t in threads:
    t.start()
for t in threads:
    t.join()
q.join()                                 # waits until every task is marked done
print("all work finished")
```

Gotchas:
- The `STOP` sentinel must be pushed once *per consumer* — a single sentinel stops one worker
  and the others block forever on `q.get()`.
- Call `q.task_done()` once per `get()` in a `finally`; mismatch (extra or missing calls) makes
  `q.join()` hang forever.
- `q.get()` blocks by default — use `q.get(timeout=...)` or `q.get_nowait()` with a sentinel
  check if workers must be able to exit when work dries up.
- `maxsize` back-pressures the producer, which bounds memory — omit it and a fast producer can
  buffer unbounded jobs.
- Prefer `queue.Queue` over a bare `list` for hand-off; a plain list needs external locking and
  still races between check-and-act.
- Mark worker threads `daemon=True` only when you're fine with them dying mid-task at exit.
