---
lang: html
keywords: countdown timer, countdown, clock, setInterval, Date.now, tabular-nums, deadline, time remaining
---

# Countdown Timer / Clock

A time-until-midnight countdown. The key habit: never decrement a stored counter — always recompute from `target - Date.now()`, so timer drift and tab throttling can't make it wrong.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Countdown timer</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 30rem; margin: 3rem auto; padding: 0 1rem; text-align: center; }
  .time { font: 700 3rem/1 system-ui; font-variant-numeric: tabular-nums; }
  .label { color: #666; }
</style>
</head>
<body>
<h1>Countdown</h1>
<div class="time" id="countdown">--:--:--</div>
<div class="label" id="msg">To: next midnight</div>
<script>
  // Drift-free: always derive from Date.now(), never decrement a stored value.
  const target = new Date();
  target.setHours(24, 0, 0, 0); // next midnight
  const el = document.getElementById('countdown');
  const pad = n => String(n).padStart(2, '0');

  function tick() {
    let ms = target - Date.now();
    if (ms <= 0) { el.textContent = '00:00:00'; clearInterval(timer); return; }
    const h = Math.floor(ms / 3.6e6), m = Math.floor(ms % 3.6e6 / 6e4), s = Math.floor(ms % 6e4 / 1000);
    el.textContent = `${pad(h)}:${pad(m)}:${pad(s)}`;
  }
  tick();
  const timer = setInterval(tick, 250); // sub-second tick so rollovers land on time
</script>
</body>
</html>
```

Gotchas:
- Never keep `remaining -= 1` — timers drift, and a throttled background tab can skip seconds. Always derive from `target - Date.now()`.
- `setInterval(tick, 1000)` drifts and can skip the final second — tick at 250ms (or align to the next second boundary).
- A paused-tab timer comes back wrong; recomputing from `Date.now()` heals it instantly.
- `Math.floor` per unit with `%` chaining is required — `Math.floor(ms / 60000)` without the modulo gives total minutes, not minutes-of-hour.
- `padStart` needs `String(n)` — numbers have no `.padStart` and throw.
- For a display clock, use `toLocaleTimeString()` and `Date.now()` each tick; for `HH:MM:SS` math, the modulo chain above.
