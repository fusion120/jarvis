---
lang: html
keywords: canvas animation, requestAnimationFrame, animation loop, bouncing ball, delta time, fps, canvas performance
---

# Canvas Animation Loop

Anything that moves on canvas should run off `requestAnimationFrame`, which syncs to the display and pauses automatically when the tab is hidden. This demo bounces 12 balls and shows why rAF beats `setInterval`.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Canvas animation loop</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 44rem; margin: 2rem auto; padding: 0 1rem; }
  canvas { width: 100%; border: 1px solid #ccc; border-radius: 8px; background: #102; display: block; }
</style>
</head>
<body>
<h1>Animation loop</h1>
<canvas id="c" width="640" height="360" aria-label="Bouncing balls animation"></canvas>
<script>
  const canvas = document.getElementById('c');
  const ctx = canvas.getContext('2d');
  const dpr = devicePixelRatio || 1;
  canvas.width = 640 * dpr; canvas.height = 360 * dpr;
  ctx.scale(dpr, dpr);

  const balls = Array.from({ length: 12 }, (_, i) => ({
    x: Math.random() * 640, y: Math.random() * 360,
    vx: (Math.random() - .5) * 6, vy: (Math.random() - .5) * 6,
    r: 8 + Math.random() * 16, hue: i * 30,
  }));

  let raf;
  function frame() {
    ctx.clearRect(0, 0, 640, 360);
    for (const b of balls) {
      b.x += b.vx; b.y += b.vy;
      if (b.x < b.r || b.x > 640 - b.r) b.vx *= -1;
      if (b.y < b.r || b.y > 360 - b.r) b.vy *= -1;
      ctx.beginPath();
      ctx.arc(b.x, b.y, b.r, 0, Math.PI * 2);
      ctx.fillStyle = `hsl(${b.hue} 80% 60%)`;
      ctx.fill();
    }
    raf = requestAnimationFrame(frame);
  }
  raf = requestAnimationFrame(frame);

  // rAF already pauses when the tab is hidden; this is belt-and-braces.
  document.addEventListener('visibilitychange', () => {
    cancelAnimationFrame(raf);
    if (!document.hidden) raf = requestAnimationFrame(frame);
  });
</script>
</body>
</html>
```

Gotchas:
- `requestAnimationFrame` throttles to the display refresh and PAUSES when the tab is hidden — prefer it over `setInterval` for any continuous animation.
- Position increments per-frame are frame-rate dependent: at 120Hz balls move 2x faster than at 60Hz. Use delta time: capture `performance.now()` and scale velocity by `dt`.
- `ctx.clearRect` erases everything each frame — draw order matters (background first) or you get ghost trails (unless trails are the goal).
- Each `ctx.fill` is a state change; for hundreds of objects, batch by fillStyle or use a single path to avoid GC/state thrash.
- HiDPI: back the store with `devicePixelRatio` and `ctx.scale` once, or everything blurs.
- Never build a loop that also runs when hidden — battery and CPU burn for nothing; the `visibilitychange` guard or rAF's native pause handles it.
