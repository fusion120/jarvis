---
lang: javascript
keywords: canvas, 2d context, getContext, drawImage, fillRect, arc, requestAnimationFrame, toDataURL, high dpi, canvas width height
---

# Canvas 2D drawing

`<canvas>` gives a pixel buffer you draw into with a 2D context: shapes, paths, text, images. The canvas coordinate system is device pixels, so for crisp text/shapes scale by `devicePixelRatio`; redraw on every frame inside `requestAnimationFrame`.

```javascript
// browser
const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");

// HiDPI: match canvas backing store to device pixels
const dpr = window.devicePixelRatio || 1;
function resize(w, h) {
  canvas.style.width = `${w}px`;
  canvas.style.height = `${h}px`;
  canvas.width = Math.round(w * dpr);       // backing store
  canvas.height = Math.round(h * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);   // CSS pixels -> device
}
resize(800, 600);

// Draw a scene
function draw(t) {
  ctx.clearRect(0, 0, 800, 600);

  // gradient background
  const grad = ctx.createLinearGradient(0, 0, 0, 600);
  grad.addColorStop(0, "#1e3c72");
  grad.addColorStop(1, "#2a5298");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 800, 600);

  // moving ball
  const x = 400 + Math.cos(t / 500) * 200;
  const y = 300 + Math.sin(t / 300) * 150;
  ctx.beginPath();
  ctx.arc(x, y, 25, 0, Math.PI * 2);
  ctx.fillStyle = "#ffd166";
  ctx.fill();
  ctx.strokeStyle = "#fff";
  ctx.lineWidth = 3;
  ctx.stroke();

  // text
  ctx.font = "bold 28px system-ui";
  ctx.fillStyle = "#fff";
  ctx.fillText(`frame ${Math.floor(t / 16)}`, 20, 40);
}

let raf;
function loop(t = 0) {
  draw(t);
  raf = requestAnimationFrame(loop);
}
loop();
// cancel: cancelAnimationFrame(raf)

// Export: PNG data URL
// const img = canvas.toDataURL("image/png");
```

Gotchas:
- Canvas is NOT SVG: it's a bitmap — resize wipes it, and shapes can't be selected/moved after drawing; redraw the whole frame.
- Forgetting `ctx.clearRect` makes frames smear onto previous frames.
- HiDPI: default canvas width/height are CSS-pixel counts, so text looks blurry on Retina; scale with `devicePixelRatio` as shown.
- Setting `canvas.width` resets the context state (fillStyle, transform) — set attributes once, then draw.
- `ctx.arc` uses RADIANS: a full circle is `2 * Math.PI`, not 360 — off-by-`Math.PI` arcs are the classic bug.
- `drawImage` needs the image loaded — draw in the `img.onload`/`img.decode()` callback.
- `getImageData` is slow unless you create the context with `{ willReadFrequently: true }`.
