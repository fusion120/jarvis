---
lang: python
keywords: requests, api, http, fetch, get, post, endpoint, json api
---
# Call a web API from Python

The pattern behind everything in this repo (Groq, Render, Telegram).

```python
import requests

# GET with query params
r = requests.get("https://api.example.com/search", params={"q": "MIMO"}, timeout=30)
r.raise_for_status()                      # raises on 4xx/5xx
data = r.json()

# POST JSON with a token header
r = requests.post(
    "https://api.example.com/items",
    headers={"Authorization": "Bearer TOKEN", "Content-Type": "application/json"},
    json={"name": "MIMO"},
    timeout=30,
)
print(r.status_code, r.json())
```

Gotchas:
- **Always pass `timeout=`** — a hanging request without it can block forever.
- `json=` does the serialization + content-type for you; don't also
  `json.dumps` manually.
- `r.raise_for_status()` turns HTTP errors into exceptions — catch them.
- Handle rate limits: catch `requests.HTTPError`, read `r.status_code`, and
  back off (e.g. `time.sleep(2)` before retrying) when you see 429.
- Don't hardcode tokens — read from `os.environ` or a config file.
