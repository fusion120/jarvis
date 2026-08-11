---
lang: html
keywords: canvas drawing, pointer events, setPointerCapture, canvas paint, mouse drawing, devicePixelRatio, getContext 2d
---

# Canvas Drawing (Pointer Input)

A freehand drawing pad: pointer events paint on a 2D canvas. Pointer events unify mouse, pen, and touch, and `setPointerCapture` keeps strokes continuous even when the pointer leaves the element.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Canvas drawing</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 44rem; margin: 2rem auto; padding: 0 1rem; }
  canvas { width: 100%; border: 1px solid #ccc; border-radius: 8px; touch-action: none; cursor: crosshair; background: #fff; }
  .bar { display: flex; gap: .5rem; margin-bottom: .5rem; align-items: center; }
</style>
</head>
<body>
<h1>Drawing on canvas</h1>
<div class="bar">
  <input type="color" id="color" value="#07c" aria-label="Stroke color">
  <input type="range" id="size" min="1" max="30" value="6" aria-label="Stroke size">
  <button id="clear">Clear</button>
</div>
<canvas id="c" width="640" height="360" aria-label="Free-draw pad"></canvas>
<script>
  const canvas = document.getElementById('c');
  const ctx = canvas.getContext('2d');
  // Crisp on HiDPI screens: scale the backing store, keep logical 640x360.
  const dpr = devicePixelRatio || 1;
  canvas.width = 640 * dpr; canvas.height = 360 * dpr;
  ctx.scale(dpr, dpr);

  ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.strokeStyle = '#07c'; ctx.lineWidth = 6;
  let drawing = false;

  function pos(e) {
    const r = canvas.getBoundingClientRect();
    return { x: (e.clientX - r.left) * (640 / r.width), y: (e.clientY - r.top) * (360 / r.height) };
  }
  canvas.addEventListener('pointerdown', e => {
    drawing = true;
    canvas.setPointerCapture(e.pointerId);
    const p = pos(e);
    ctx.beginPath(); ctx.moveTo(p.x, p.y);
  });
  canvas.addEventListener('pointermove', e => {
    if (!drawing) return;
    const p = pos(e);
    ctx.lineTo(p.x, p.y); ctx.stroke();
  });
  canvas.addEventListener('pointerup', () => drawing = false);
  canvas.addEventListener('pointercancel', () => drawing = false);
  document.getElementById('color').addEventListener('input', e => ctx.strokeStyle = e.target.value);
  document.getElementById('size').addEventListener('input', e => ctx.lineWidth = e.target.value);
  document.getElementById('clear').addEventListener('click', () => ctx.clearRect(0, 0, 640, 360));
</script>
</body>
</html>
```

Gotchas:
- `touch-action: none` on the canvas is mandatory — without it, mobile browsers scroll instead of drawing.
- Resizing `canvas.width`/`height` CLEARS the bitmap; HiDPI needs `width = logical * devicePixelRatio` + `ctx.scale(dpr, dpr)` once, or strokes look blurry on retina.
- Without `setPointerCapture`, fast strokes gap out when the pointer briefly leaves the element.
- Map clientX/Y to canvas logical pixels with `(e.clientX - rect.left) * (logicalWidth / rect.width)` — CSS width rarely equals the backing store.
- Set `strokeStyle`/`lineWidth` before `stroke()`; they're read at stroke time, so mid-stroke input changes affect the current segment.
- `getContext('2d')` can return `null` after many live contexts — check it in production code.
