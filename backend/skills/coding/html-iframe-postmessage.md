---
lang: html
keywords: postMessage, iframe, cross frame, message event, targetOrigin, e.origin, srcdoc, contentWindow, window messaging
---

# iframe postMessage (Cross-Frame)

Two `srcdoc` iframes talk to each other through the parent via `postMessage`. The pattern — validate `e.origin`, check `e.source`, relay — is exactly what embeddable widgets use. `srcdoc` keeps the whole demo self-contained.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>iframe postMessage</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 44rem; margin: 2rem auto; padding: 0 1rem; }
  iframe { width: 100%; height: 160px; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 1rem; }
  #log { background: #0d1117; color: #7ee787; font: 12px/1.5 monospace; padding: .75rem; border-radius: 8px; white-space: pre-wrap; min-height: 4rem; }
</style>
</head>
<body>
<h1>Cross-frame messaging</h1>
<p>The iframes are generated with <code>srcdoc</code> — separate documents on this origin. Each posts to the parent, which relays between them.</p>
<iframe id="a" title="Frame A"></iframe>
<iframe id="b" title="Frame B"></iframe>
<button id="ping">Parent to both frames</button>
<div id="log"></div>
<script>
  const frameHTML = name => `
    <style>body{font:14px/1.5 system-ui;padding:1rem}button{padding:.4rem .8rem}</style>
    <p>I am <b>frame ${name}</b>.</p>
    <button onclick="parent.postMessage('hello from ${name}','*')">send to parent</button>
    <script>addEventListener('message', e => {
      if (e.origin !== location.origin) return;
      document.body.insertAdjacentHTML('beforeend', '<p>got: ' + e.data + '<\/p>');
    });<\/script>`;

  const a = document.getElementById('a'), b = document.getElementById('b');
  a.srcdoc = frameHTML('A');
  b.srcdoc = frameHTML('B');

  function log(msg) { document.getElementById('log').textContent += msg + '\n'; }

  addEventListener('message', e => {
    if (e.origin !== location.origin) return log('IGNORED message from ' + e.origin);
    log(`parent received: ${e.data}`);
    // Relay to the other frame only.
    if (e.source === a.contentWindow) b.contentWindow.postMessage('A said: ' + e.data, location.origin);
    if (e.source === b.contentWindow) a.contentWindow.postMessage('B said: ' + e.data, location.origin);
  });

  document.getElementById('ping').addEventListener('click', () => {
    a.contentWindow.postMessage('ping', location.origin);
    b.contentWindow.postMessage('ping', location.origin);
  });
</script>
</body>
</html>
```

Gotchas:
- Never use `targetOrigin '*'` for data you care about — the message goes to any window that loaded your frame. Always pass the expected origin.
- ALWAYS validate `e.origin` in the receiver before trusting `e.data` — you can be loaded inside a malicious frame.
- `postMessage` uses structured clone: functions and DOM nodes throw; plain objects, arrays, Dates, and typed arrays travel fine.
- `e.source` identifies the sender — keep references to child `contentWindow`s to reply precisely instead of broadcasting to all.
- `srcdoc` iframes inherit the parent's origin, so origin checks pass trivially — good for demos, but real embeds use genuinely different origins.
- The receiver must register its listener BEFORE the sender posts or early messages are lost (a classic load-order race).
- Escaping `<\/script>` inside a JS template string is required so the literal doesn't terminate the outer script block.
