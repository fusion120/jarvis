---
lang: html
keywords: keyframe animations, @keyframes, animation fill mode, infinite alternate, animation-play-state, prefers-reduced-motion, bounce, pulse
---

# Keyframe Animations

Named `@keyframes` animations for things `transition` can't express — bounces, pulses, multi-step sequences. Includes play/pause via `animation-play-state` and the `prefers-reduced-motion` kill switch.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Keyframe animations</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 30rem; margin: 2rem auto; padding: 0 1rem; }
  .dot { width: 3rem; height: 3rem; border-radius: 50%; background: #07c;
         animation: bounce 1s cubic-bezier(.3, 0, .3, 1) infinite alternate; }
  .pulse { margin-top: 1rem; padding: .75rem 1.5rem; border: 0; border-radius: 999px;
           background: #07c; color: #fff; cursor: pointer;
           animation: pulse 2s ease-in-out infinite; }
  @keyframes bounce {
    from { transform: translateY(0); }
    to { transform: translateY(2rem); }
  }
  @keyframes pulse {
    0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgb(0 119 204 / .4); }
    50% { transform: scale(1.05); box-shadow: 0 0 0 12px rgb(0 119 204 / 0); }
  }
  @media (prefers-reduced-motion: reduce) {
    .dot, .pulse { animation: none; }
  }
</style>
</head>
<body>
<h1>Keyframe animations</h1>
<div class="dot" aria-hidden="true"></div>
<button class="pulse" id="toggle">Pause</button>
<script>
  const btn = document.getElementById('toggle');
  const dot = document.querySelector('.dot');
  btn.addEventListener('click', () => {
    const paused = dot.style.animationPlayState === 'paused';
    dot.style.animationPlayState = paused ? 'running' : 'paused';
    btn.textContent = paused ? 'Pause' : 'Play';
  });
</script>
</body>
</html>
```

Gotchas:
- `animation-fill-mode` matters: with `infinite alternate` the animation holds between cycles anyway, but a one-shot with a delay snaps back unless you set `backwards`/`forwards` — `none` (default) shows the resting style during the delay.
- `from`/`to` covers exactly two stops; three-plus stops need explicit `%` blocks or the browser holds the last defined value.
- Easing inside the shorthand (`cubic-bezier(...)`) applies to the whole animation; easing declared inside `@keyframes` applies per-segment.
- Animating `box-shadow` (the pulse) is expensive — prefer `transform`/`opacity` and keep shadows static where you can.
- `prefers-reduced-motion: reduce` should set `animation: none` (or a minimal fade) — decorative motion can trigger vestibular symptoms.
- Toggling `animationPlayState` via inline style pauses/resumes without restarting — a class toggle alone restarts the animation from 0.
