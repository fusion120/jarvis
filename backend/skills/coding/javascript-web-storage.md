---
lang: javascript
keywords: localStorage, sessionStorage, JSON, storage event, key value store, same origin, quota, persistence, cache, setItem getItem
---

# localStorage / sessionStorage

`localStorage` persists key/value strings across tabs and sessions for one origin; `sessionStorage` lasts only for the tab. Store structured data as JSON strings, wrap access in a safe helper, and watch the `storage` event to sync tabs.

```javascript
// browser
// Typed storage helper: JSON in, safe reads out
const store = {
  get(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw === null ? fallback : JSON.parse(raw);
    } catch {
      return fallback;               // corrupt JSON -> fallback
    }
  },
  set(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  },
  remove(key) { localStorage.removeItem(key); },
};

// Usage: settings object
store.set("settings", { theme: "dark", fontSize: 14 });
const s = store.get("settings", { theme: "light", fontSize: 12 });
console.log(s.theme);                // "dark"

// Cache pattern with expiry
store.set("lastFetch", { at: Date.now(), items: [1, 2, 3] });
const cached = store.get("lastFetch", null);
const fresh = cached && Date.now() - cached.at < 60_000 ? cached.items : null;
console.log(fresh);                  // [1,2,3]

// Tab sync: fires in OTHER tabs when this tab writes
window.addEventListener("storage", (e) => {
  if (e.key === "settings") {
    const next = e.newValue ? JSON.parse(e.newValue) : null;
    document.getElementById("theme").textContent = next?.theme ?? "light";
  }
});

// Session storage: cleared when the tab closes
sessionStorage.setItem("draft", JSON.stringify({ body: "half-written" }));

// Keys are per-origin: protocol + host + port
console.log(location.origin);
```

Gotchas:
- Values must be strings — objects are stored as `"[object Object]"` unless JSON.stringify'd first.
- `getItem` returns `null` for missing keys (not `undefined`); an empty string is a valid stored value.
- Quota is ~5MB per origin; `setItem` throws `QuotaExceededError` (wrap in try/catch).
- Same-origin only: `http://localhost:3000` and `http://localhost:4000` do NOT share storage; subdomains don't either.
- The `storage` event fires only in OTHER tabs/windows, not the one that wrote.
- Private mode and cleared-cache settings can make storage unavailable or ephemeral — always guard with try/catch.
- Never store secrets or tokens in localStorage — XSS can read them; keep them on the server.
