---
lang: javascript
keywords: requestAnimationFrame, rAF, animation, cancelAnimationFrame, delta time, frame rate, smooth animation, performance, fps, canvas animation
---

# requestAnimationFrame animation

`requestAnimationFrame` schedules your draw callback right before the browser paints — once per display refresh, throttled to the screen and paused in background tabs. The timestamp argument is the key: compute `deltaTime` and move by `speed * dt` so animation is frame-rate independent.

```javascript
// browser
// Animate a box; speed is per-second, independent of refresh rate
const box = document.getElementById("box");
const SPEED = 300;          // px/second
let last = null;
let pos = 0;
let rafId;

function frame(t) {
  if (last === null) last = t;
  const dt = (t - last) / 1000;      // seconds
  last = t;

  pos += SPEED * dt;
  box.style.transform = `translateX(${pos % 800}px)`;

  if (document.getElementById("stop").dataset.running === "1") {
    rafId = requestAnimationFrame(frame);
  }
}

document.getElementById("start").addEventListener("click", () => {
  document.getElementById("stop").dataset.running = "1";
  last = null;
  rafId = requestAnimationFrame(frame);
});
document.getElementById("stop").addEventListener("click", () => {
  document.getElementById("stop").dataset.running = "0";
  cancelAnimationFrame(rafId);
});

// FPS counter: measure real frame rate
let frames = 0, fps = 0, lastSec = performance.now();
function countFrames(now) {
  frames++;
  if (now - lastSec >= 1000) {
    fps = frames;
    frames = 0;
    lastSec = now;
    document.getElementById("fps").textContent = String(fps);
  }
  requestAnimationFrame(countFrames);
}
requestAnimationFrame(countFrames);
```

Gotchas:
- rAF fires before paint, not "as fast as possible" — don't pile on extra logic between frames or you stutter.
- Without `deltaTime`, movement is tied to refresh rate: 144Hz runs ~2.4x faster than 60Hz. Always scale by dt.
- First timestamp is NOT 0 — it's the load time; initialize `last` on the first frame or you get a huge `dt` jump.
- rAF pauses when the tab is hidden (saving battery) — timers that must track wall-clock use `Date.now()` separately.
- The `t` timestamp is in ms since time-origin; it's identical to `performance.now()`.
- `cancelAnimationFrame(id)` needs the SAME id the last `requestAnimationFrame` returned — overwrite your stored id each frame.
- For scroll-linked animation, pair rAF with a `scroll` listener that only records `scrollY` and does the layout work in the frame callback.
