---
lang: javascript
keywords: service worker, offline, cache, Cache API, navigator.serviceWorker, precache, fetch handler, workbox, PWA, install activate
---

# Service worker & offline caching

A service worker is a script the browser installs and runs separately from the page — it can intercept every network request via the `fetch` event and serve cached responses when offline. Precache app shell on `install`, update the cache on `activate`, and serve stale-while-revalidate in `fetch`.

```javascript
// sw.js — served at the site root with a Service-Worker-Allowed header
const CACHE = "app-shell-v1";
const ASSETS = [
  "/",
  "/index.html",
  "/app.js",
  "/styles.css",
  "/icon.png",
];

// Precache on install (finish before the SW activates)
self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE)
      .then((c) => c.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

// Clean old caches on activate
self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
      )
      .then(() => self.clients.claim())
  );
});

// Stale-while-revalidate: serve cache fast, refresh in background
self.addEventListener("fetch", (e) => {
  const { request } = e;
  if (request.method !== "GET") return;           // never cache POST/PUT
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return; // same-origin only (demo)

  e.respondWith((async () => {
    const cached = await caches.match(request);
    const network = fetch(request)
      .then((res) => {
        if (res.ok) {
          const copy = res.clone();               // response bodies are one-shot
          caches.open(CACHE)
            .then((c) => c.put(request, copy))
            .catch(() => {});                     // cache write failures are non-fatal
        }
        return res;
      })
      .catch(() => cached);                       // offline fallback
    return cached ?? network;
  })());
});
```

```javascript
// register in your page script
// if ("serviceWorker" in navigator) {
//   navigator.serviceWorker.register("/sw.js").catch(console.error);
// }
```

Gotchas:
- Service workers require HTTPS (or `localhost`) — a page over plain http can't register one.
- The SW only controls pages after first load + reload (unless `clients.claim()`); the first visit still goes over the network.
- `e.waitUntil` keeps the SW alive for async work during install/activate/fetch — without it the worker may die mid-cache.
- Response bodies are one-shot: use `res.clone()` before putting into cache, then return the original.
- Scope: an SW at `/js/sw.js` only controls `/js/…` by default — serve it from the root or send `Service-Worker-Allowed: /`.
- Update strategy: bump the cache name on every deploy or stale versions stick; `skipWaiting` + `clients.claim` make the new SW take over promptly.
- A bad SW can break the site (serving stale/404s): cache-bust asset filenames and test with DevTools "Bypass for network".
