---
lang: python
keywords: password, hash, bcrypt, secrets, hashlib, salt, verify, login, security, store password
---

# Storing and verifying passwords with bcrypt

Never store plaintext or a raw SHA hash. `bcrypt` is a deliberately slow, salted hash built for
passwords: each user's password gets a random salt, the work factor makes brute force
expensive, and verification is a constant-time comparison.

```python
# pip install bcrypt
import bcrypt


def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt(rounds=12)                  # rounds = work factor (10-12 typical)
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def check_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False                                  # malformed hash -> reject


stored = hash_password("hunter2!")
print("correct:", check_password("hunter2!", stored))
print("wrong:  ", check_password("hunter2", stored))


# The hash is self-contained: algorithm, rounds, salt, digest.
print(stored[:29])
```

Gotchas:
- bcrypt has a **72-byte input limit** — a 100-char password is silently truncated. Either cap
  password length, or pre-hash long inputs with SHA-256 (base64) before bcrypt.
- `hashpw` returns bytes; decode to `str` for database storage, and never trim or re-encode
  the stored string — every byte matters.
- Two calls to `hash_password` for the same password produce *different* hashes (random salt).
  Verify with `checkpw`, never by comparing stored strings.
- `checkpw` raises `ValueError` on a malformed stored hash (e.g. NULL bytes) — wrap it, or a
  corrupt DB row crashes login.
- Pick a work factor that costs ~0.1–0.3s on your hardware; 12 is a good default. Too low
  defeats the purpose, too high enables DoS on the login endpoint.
- For new code, `hashlib.scrypt` or `argon2-cffi` are also good choices; raw
  `hashlib.sha256(password)` is never acceptable for passwords.
