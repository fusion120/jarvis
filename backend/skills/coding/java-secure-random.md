---
lang: java
keywords: securerandom, random, token, uuid, cryptography, password, entropy, nextInt
---

# SecureRandom: Cryptographically Strong Randomness

`Math.random()` and `java.util.Random` are predictable — never use them for tokens, passwords, salt, or session IDs. `SecureRandom` draws from the OS entropy pool and is the right tool for anything security-relevant. `UUID.randomUUID()` is also strong for identifiers.

```java
import java.security.SecureRandom;
import java.util.Base64;
import java.util.UUID;

public class SecureRandomDemo {
    public static void main(String[] args) {
        // prefer SecureRandom for anything security-related
        SecureRandom rng = new SecureRandom();

        // bounded integer (0..5) + 1
        int dice = rng.nextInt(6) + 1;
        System.out.println("dice: " + dice);

        // 32 random bytes -> URL-safe token, no padding
        byte[] token = new byte[32];
        rng.nextBytes(token);
        System.out.println("token: " + Base64.getUrlEncoder().withoutPadding().encodeToString(token));

        // bounded long
        System.out.println("long in range: " + rng.nextLong(1_000_000));

        // UUIDs are random and collision-safe for identifiers
        System.out.println("uuid: " + UUID.randomUUID());

        // integers as a stream (e.g., random salt bytes from hex)
        rng.ints(8, 0, 16).forEach(i -> System.out.printf("%x", i));
        System.out.println();
    }
}
```

Gotchas:
- Never seed `SecureRandom` yourself (`new SecureRandom(new byte[]{...})`) — you'd shrink its entropy; let the OS seed it.
- `nextInt(6)` gives 0-5; forgetting the bound is harmless for `Math.random()` but `SecureRandom.nextInt()` returns any int — always pass bounds.
- `java.util.Random` (and `Math.random`) can have their future outputs predicted from a few samples — the "random" IDs they produce are guessable.
- `Base64.getUrlEncoder().withoutPadding()` produces URL/file-safe tokens; the default encoder includes `+/=` that break URLs and filenames.
- A token's entropy depends on its *byte* length, not its base64 length — 16 bytes ≈ 128 bits is a sensible floor for secrets.
- `UUID.randomUUID()` uses the default secure random and is fine for IDs, but UUIDs are not secret tokens if leaked in logs. And `SecureRandom` can block on slow-entropy systems — generate secrets at startup, not per-request.
