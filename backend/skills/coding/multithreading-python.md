---
lang: python
keywords: thread, threading, background, daemon, queue, concurrent, parallel
---
# Background threads in Python

The pattern this repo uses for its loops (reminders, vision, proactive MIMO) —
long-running work that must not block the main program.

```python
import threading, time, queue

q = queue.Queue()                     # thread-safe way to pass data

def worker(name):
    while True:
        item = q.get()
        print(f"{name} got {item}")
        time.sleep(1)

for i in range(2):
    threading.Thread(target=worker, args=(f"w{i}",), daemon=True).start()

q.put("task 1")
q.put("task 2")
time.sleep(3)
```

Gotchas:
- **`daemon=True`** means the thread dies when the main program exits — right
  for background loops, wrong if you need it to finish.
- Shared plain lists/dicts between threads can corrupt under race; use
  `queue.Queue` or a `threading.Lock`.
- Don't call `time.sleep` in a way that blocks UI/polling — sleep is fine
  inside a worker thread.
- Python threads don't speed up CPU-heavy math (GIL) — for that use
  `multiprocessing` or `concurrent.futures.ProcessPoolExecutor`.
- Start threads with `threading.Thread(target=fn, daemon=True).start()`; keep
  the target a plain function so it's testable.
