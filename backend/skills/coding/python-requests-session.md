---
lang: python
keywords: requests, session, retry, urllib3, Retry, adapter, timeout, http, api client, backoff
---

# requests.Session with automatic retries

A `requests.Session` reuses one connection pool (TCP + TLS + HTTP keep-alive) and stores
cookies. Mount a `urllib3.Retry` adapter so 429/5xx responses and connection errors back off
and retry automatically instead of crashing your script.

```python
# pip install requests
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def build_session(retries: int = 3) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=0.5,                  # sleeps 0, 0.5, 1.0, 2.0 ... seconds
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST", "PUT"]),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def get_json(session: requests.Session, url: str) -> dict:
    resp = session.get(url, timeout=10)
    resp.raise_for_status()                  # raise on 4xx/5xx after retries
    return resp.json()


session = build_session()
data = get_json(session, "https://httpbin.org/json")
print(data["slideshow"]["title"])
```

Gotchas:
- `Retry(total=3)` counts retries on top of the first attempt — don't assume it means 3 total
  requests. `status_forcelist` triggers retries only for those status codes.
- `backoff_factor` sleeps `{backoff_factor * (2 ** (retry_number - 1))}` seconds, so 0.5 gives
  0.5, 1.0, 2.0 — set 0 for no sleep, and know the units are seconds.
- Without `respect_retry_after_header=True`, a server's `Retry-After` (e.g. on 429) is ignored
  and you hammer a rate-limited endpoint right back.
- `POST` is retried by default in some urllib3 versions — use `allowed_methods` to choose
  explicitly, because replaying a POST can double-submit.
- Connection-pool errors (`ConnectionError`, `ConnectTimeout`) are retried, but *timeouts while
  reading* (`ReadTimeout`) are not by default; add `Retry`'s `status_forcelist` plus
  `connect=...`/`read=...` params if needed.
- Retries never help a 4xx like 400/401/403 — those indicate a caller bug; don't burn retries
  on them.
