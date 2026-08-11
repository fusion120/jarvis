---
lang: html
keywords: pwa manifest, manifest.json, web app manifest, installable, theme_color, start_url, maskable icon, apple-touch-icon, app install
---

# PWA Manifest

The `manifest.json` that makes a site installable. Like the service worker, it must be a same-origin file — this page ships a ready-to-download manifest and shows the head tags that wire it up.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PWA manifest</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 36rem; margin: 2rem auto; padding: 0 1rem; }
  pre { background: #f4f4f4; padding: 1rem; border-radius: 8px; overflow-x: auto; font-size: .85rem; }
</style>
</head>
<body>
<h1>PWA manifest</h1>
<p>A manifest makes your site installable (Add to Home Screen / Desktop). Like the service worker it must be a same-origin file, so this page ships <code>manifest.json</code> as a download and shows the head tags.</p>
<button id="dl">Download manifest.json</button>
<pre id="out"></pre>
<script>
  const MANIFEST = {
    name: 'Acme Reader',
    short_name: 'Acme',
    description: 'Read articles offline.',
    start_url: '/index.html',
    scope: '/',
    display: 'standalone',
    background_color: '#ffffff',
    theme_color: '#07c',
    icons: [
      { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
      { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
  };
  document.getElementById('out').textContent = JSON.stringify(MANIFEST, null, 2);
  document.getElementById('dl').addEventListener('click', () => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(MANIFEST, null, 2)], { type: 'application/manifest+json' }));
    a.download = 'manifest.json';
    a.click();
    URL.revokeObjectURL(a.href);
  });
</script>
<!-- Wire-up in the real app:
  <link rel="manifest" href="/manifest.json">
  <meta name="theme-color" content="#07c">
  <link rel="apple-touch-icon" href="/icons/icon-192.png">
-->
</body>
</html>
```

Gotchas:
- Chrome installability needs ALL of: manifest with `name` + 192 and 512 icons, a `start_url`, HTTPS, AND an active service worker with a `fetch` handler.
- `display: standalone` opens its own window; `minimal-ui`/`browser` are the fallbacks — there's no "popup" mode.
- `theme_color` colors the browser chrome; `background_color` paints the launch splash — mismatch with the real UI looks broken at startup.
- `maskable` icons get cropped to circles/rounded squares by launchers — keep safe padding or logos get clipped.
- iOS ignores the manifest for install — you still need `<link rel="apple-touch-icon">` and `<meta name="apple-mobile-web-app-capable">`.
- A missing icon size makes install fail with cryptic errors — always ship both 192 and 512 PNGs.
