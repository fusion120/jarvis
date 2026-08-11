---
lang: python
keywords: rate limit, token bucket, throttle, quota, limiter, requests per second, backoff, burst
---

# Token-bucket rate limiter

A token bucket allows a fixed *burst* (`capacity`) while enforcing a long-run average
(`rate` tokens/second): every action consumes a token, tokens refill over time, and when the
bucket is empty the action is refused (or waits). This protects external APIs from bursts.

```python
import threading
import time


class TokenBucket:
    def __init__(self, rate: float, capacity: float):
        self.rate = rate                    # tokens refilled per second
        self.capacity = capacity
        self.tokens = capacity              # start full -> allows an initial burst
        self.updated = time.monotonic()
        self._lock = threading.Lock()

    def take(self, n: float = 1.0) -> bool:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.updated
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.updated = now
            if self.tokens >= n:
                self.tokens -= n
                return True
            return False

    def wait(self, n: float = 1.0) -> None:
        while not self.take(n):
            time.sleep(0.05)


bucket = TokenBucket(rate=2, capacity=2)      # 2 req/s, burst of 2
for i in range(6):
    if bucket.take():
        print(i, "ok")
    else:
        print(i, "throttled")

limiter = TokenBucket(rate=1, capacity=1)     # enforce in front of an API call
for job in range(3):
    limiter.wait()
    print("call", job)
```

Gotchas:
- Use `time.monotonic()` for rate math, never `time.time()` — wall-clock jumps (NTP, manual
  change) corrupt the refill calculation.
- Refill *before* checking the bucket (`tokens + elapsed*rate`, capped at `capacity`), then
  subtract; doing it after lets a stale timestamp allow more tokens than intended.
- `min(capacity, ...)` caps the bucket so idle time doesn't bank unlimited tokens.
- Wrap the state in a `threading.Lock` if multiple threads share the limiter; without it the
  check-and-subtract races and bursts exceed the limit.
- A token bucket controls *rate*, not *ordering* — it can't guarantee "no two calls in the same
  second", it only averages out. For strict spacing add a wait loop.
- Persist `updated` inside the lock and set it on every refill, or a thread that waits on the
  lock computes its own refill from an old timestamp.
