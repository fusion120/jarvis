---
lang: html
keywords: service worker, offline cache, offline pwa, caches api, fetch handler, skipWaiting, clients claim, cache first
---

# Service Worker Offline Cache

A service worker precaches the shell and serves it from cache offline. SW scripts must be same-origin files, so this page ships the `sw.js` source as a download and registers it if present — the cache strategy shown is the production standard.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Service worker offline cache</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 36rem; margin: 2rem auto; padding: 0 1rem; }
  #status { padding: .75rem; border-radius: 8px; background: #fff3cd; }
  #status.online { background: #d4edda; }
</style>
</head>
<body>
<h1>Offline with a service worker</h1>
<p id="status">Checking...</p>
<p>Service workers must be same-origin scripts, so this demo cannot register one inline. Click to download <code>sw.js</code> next to this page, then reload — it precaches this page and serves it offline.</p>
<button id="dl">Download sw.js</button>
<script>
  const SW_SOURCE = `
const CACHE = 'v1';
const ASSETS = ['./', './index.html'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))));
});
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return; // skip cross-origin (e.g. analytics)
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request).then(hit => hit ||
      fetch(e.request).then(resp => {
        const copy = resp.clone(); // body is single-use
        caches.open(CACHE).then(c => c.put(e.request, copy));
        return resp;
      })
    )
  );
});
`;

  document.getElementById('dl').addEventListener('click', () => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([SW_SOURCE], { type: 'text/javascript' }));
    a.download = 'sw.js';
    a.click();
    URL.revokeObjectURL(a.href);
  });

  const status = document.getElementById('status');
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('sw.js')
      .then(() => { status.textContent = 'Service worker active — reload to cache.'; status.className = 'online'; })
      .catch(() => { status.textContent = 'No sw.js here yet — download it above, then reload.'; });
  } else {
    status.textContent = 'Service workers unsupported in this browser.';
  }
</script>
</body>
</html>
```

Gotchas:
- Service workers only run on HTTPS (or localhost) — registration fails silently on plain HTTP.
- Scope: `register('sw.js')` controls that path and below; `register('/sw.js')` controls the whole origin.
- First visit has no active worker — control starts on the SECOND load (or call `self.clients.claim()` in activate).
- The fetch handler must `resp.clone()` before caching — a response body is single-use; caching consumes the stream.
- Version the cache name (`'v2'`) and delete old caches in `activate`, or users get stale assets forever after a deploy.
- `caches.addAll` fails wholesale if any asset 404s — list only URLs that exist.
