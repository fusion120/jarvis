---
lang: python
keywords: hmac, jwt, token, signature, sha256, verify, secret, payload, base64, header, json
---

# HMAC-signed tokens (JWT HS256) with the stdlib

A JWT is `header.payload.signature` where the signature is an HMAC-SHA256 of the first two
segments keyed by a shared secret. Anyone can read the payload (it's only base64), so
signatures prove *who wrote it*, not secrecy — and verify with a constant-time compare.

```python
import base64
import hashlib
import hmac
import json
import time


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)               # restore stripped padding
    return base64.urlsafe_b64decode(data + padding)


def make_jwt(payload: dict, secret: str, ttl: int = 300) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    body = dict(payload, exp=int(time.time()) + ttl)
    compact = lambda d: _b64url(json.dumps(d, separators=(",", ":")).encode())
    signing_input = f"{compact(header)}.{compact(body)}"
    signature = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url(signature)}"


def verify_jwt(token: str, secret: str) -> dict:
    header, payload, signature = token.split(".")
    expected = hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _b64url_decode(signature)):
        raise ValueError("bad signature")
    data = json.loads(_b64url_decode(payload))
    if data.get("exp", 0) < time.time():
        raise ValueError("token expired")
    return data


token = make_jwt({"user": "ada", "role": "admin"}, "super-secret")
print(verify_jwt(token, "super-secret"))
```

Gotchas:
- The payload is **not encrypted** — never put passwords or secrets in a JWT. Anyone with the
  token base64-decodes the payload.
- Compare signatures with `hmac.compare_digest`, never `==`, to avoid timing attacks.
- Base64url needs its `=` padding restored before `urlsafe_b64decode`, or you get an incorrect
  padding error.
- Always check `alg` on decode: accepting `"alg": "none"` or `"HS256"` tokens signed with the
  *public* key of an RSA setup are classic bypasses.
- Validate `exp` (and ideally `nbf`) — a token without an expiry check never expires.
- For production, use `PyJWT` or `python-jose` rather than a hand-rolled verifier; they handle
  algorithms, key types, and edge cases. This code is for learning and offline tools.
