---
lang: python
keywords: token, refresh, auth, oauth, bearer, api key, 401, expiry, client credentials, access token
---

# API client with token refresh

OAuth2/API-key tokens expire, so an API client must fetch a token before the first call and
refresh it before expiry — and handle a 401 mid-flight (revoked/expired early) by refetching
once and retrying.

```python
# pip install requests
import time

import requests

TOKEN_URL = "https://auth.example.com/token"


class TokenClient:
    def __init__(self, client_id: str, client_secret: str):
        self.auth = (client_id, client_secret)
        self.access_token: str | None = None
        self.expires_at: float = 0.0

    def _fetch_token(self) -> None:
        resp = requests.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=self.auth,
            timeout=10,
        )
        resp.raise_for_status()
        body = resp.json()
        self.access_token = body["access_token"]
        # Buffer 30s so we never race right at the edge.
        self.expires_at = time.time() + int(body.get("expires_in", 3600)) - 30

    def _headers(self) -> dict[str, str]:
        if self.access_token is None or time.time() >= self.expires_at:
            self._fetch_token()
        return {"Authorization": f"Bearer {self.access_token}"}

    def request(self, url: str) -> requests.Response:
        resp = requests.get(url, headers=self._headers(), timeout=10)
        if resp.status_code == 401:              # token rejected — force refresh once
            self.access_token = None
            resp = requests.get(url, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp


client = TokenClient("client-id", "client-secret")
data = client.request("https://api.example.com/users/1")
print(data.json())
```

Gotchas:
- Store `expires_at` as an absolute epoch time, not a remaining-seconds count, so the check
  doesn't drift as the process runs.
- Clock skew between client and server can expire tokens early — buffer the refresh by 30–60s
  as shown, and still handle 401.
- Only refresh once per 401; looping forever on a bad secret burns requests. Refetch, retry
  once, then let the 401 propagate.
- The refresh endpoint itself needs a `timeout`; a hung auth server blocks every request.
- If the refresh is shared across threads, guard `_fetch_token` with a `threading.Lock` so two
  threads don't fetch two tokens simultaneously.
- Never log the access token or client secret — a single DEBUG log line leaks credentials.
