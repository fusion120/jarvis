---
lang: html
keywords: video element, poster, controls, webm, captureStream, MediaRecorder, video preload, video source, html5 video
---

# Video with Poster + Controls

Embedding video is a `<video>` tag plus a poster and sources. This demo has no video file to host, so it generates a short WebM from an animated canvas at runtime — the same `captureStream` trick powers live-preview recorders.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Video element</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 44rem; margin: 2rem auto; padding: 0 1rem; }
  video { width: 100%; aspect-ratio: 16/9; background: #000; border-radius: 8px; }
  .note { color: #666; font-size: .9rem; }
</style>
</head>
<body>
<h1>Video with poster + controls</h1>
<video id="v" controls preload="metadata"
       poster="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='640' height='360'%3E%3Crect width='100%25' height='100%25' fill='%23123'/%3E%3Ctext x='50%25' y='50%25' fill='%23fff' font-size='28' text-anchor='middle'%3Egenerating%20video...%3C/text%3E%3C/svg%3E">
  <source src="media/demo.webm" type="video/webm">
  <p>Your browser does not support the video element.</p>
</video>
<p class="note">The <code>source</code> above would be a real file; this page synthesizes one via canvas + MediaRecorder so it runs anywhere.</p>
<script>
  const video = document.getElementById('v');
  (async () => {
    const canvas = document.createElement('canvas');
    canvas.width = 640; canvas.height = 360;
    const ctx = canvas.getContext('2d');
    const stream = canvas.captureStream(30);
    const rec = new MediaRecorder(stream, { mimeType: 'video/webm' });
    const chunks = [];
    rec.ondataavailable = e => chunks.push(e.data);
    rec.onstop = () => {
      video.src = URL.createObjectURL(new Blob(chunks, { type: 'video/webm' }));
      video.load();
    };
    rec.start();
    let f = 0;
    const timer = setInterval(() => {
      ctx.fillStyle = `hsl(${(f * 6) % 360} 70% 50%)`;
      ctx.fillRect(0, 0, 640, 360);
      ctx.fillStyle = '#fff';
      ctx.font = '48px sans-serif';
      ctx.fillText(`Frame ${f}`, 30, 200);
      if (++f >= 90) { clearInterval(timer); rec.stop(); }
    }, 33);
  })();
</script>
</body>
</html>
```

Gotchas:
- Always provide multiple `<source>` types (webm + mp4) plus a fallback paragraph; if nothing plays, the video fires `error`.
- `preload="metadata"` fetches only the poster/timeline — `preload="auto"` downloads the whole file; never guess with huge videos.
- The poster is a URL like an image: a giant poster hurts load as much as a giant image — optimize it.
- iOS Safari blocks `autoplay` with sound; start muted (`muted autoplay playsinline`) or wait for a user gesture.
- `captureStream` + `MediaRecorder`: check `MediaRecorder.isTypeSupported('video/webm')` first or `new MediaRecorder` throws.
- `URL.createObjectURL` blobs are per-session — don't persist the src across reloads; regenerate or store the Blob in IndexedDB.
