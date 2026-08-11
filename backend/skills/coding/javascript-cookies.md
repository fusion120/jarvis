---
lang: javascript
keywords: cookies, document.cookie, set cookie, HttpOnly, SameSite, session cookie, max-age, expires, cookie parsing, third party
---

# Cookies in the browser

`document.cookie` reads and writes cookies as a single `; `-joined string. The real security work happens in attributes — `HttpOnly`, `Secure`, `SameSite` — which you set server-side via `Set-Cookie`. Use `max-age`/`expires` for lifetime, and always URL-encode values.

```javascript
// browser
// Small wrapper: encode + write, parse + read
const cookieStore = {
  set(name, value, { maxAge = 3600, path = "/", sameSite = "Lax" } = {}) {
    const parts = [
      `${encodeURIComponent(name)}=${encodeURIComponent(value)}`,
      `max-age=${maxAge}`,
      `path=${path}`,
      `samesite=${sameSite}`,
    ];
    document.cookie = parts.join("; ");
  },
  get(name) {
    const prefix = `${encodeURIComponent(name)}=`;
    for (const part of document.cookie.split("; ")) {
      if (part.startsWith(prefix)) {
        return decodeURIComponent(part.slice(prefix.length));
      }
    }
    return null;
  },
  delete(name) { this.set(name, "", { maxAge: 0 }); },
};

cookieStore.set("theme", "dark", { maxAge: 60 * 60 * 24 * 7 });
cookieStore.set("session_id", "abc-123", { sameSite: "Strict" });
console.log(cookieStore.get("theme"));           // "dark"
cookieStore.delete("theme");

// The critical flags are set by the SERVER:
// Set-Cookie: session=abc; HttpOnly; Secure; SameSite=Lax; Path=/
// HttpOnly cookies are invisible to document.cookie entirely.
```

Gotchas:
- Cookies are a single string; there's no `getCookie(name)` API — parse with `split("; ")`.
- Values must be URL-encoded (`encodeURIComponent`) — spaces and `;` break the whole cookie.
- `HttpOnly` cookies are invisible to JS — `document.cookie` won't show them; set them server-side only.
- `SameSite` matters: `Strict` breaks cross-site login flows, `Lax` is the safe default, `None` REQUIRES `Secure` (modern browsers reject `None` over http).
- Size limits: ~4KB per cookie, ~20 cookies per domain — keep payloads tiny; use localStorage for app data, cookies only for auth/preferences.
- Expiry is absolute: `max-age` (seconds, preferred) or `expires` (date string); deleting = setting `max-age=0`.
- Deleting requires matching path/domain of the original cookie or the delete silently fails.
- Never store sensitive tokens in non-HttpOnly cookies — any XSS script can read them.
