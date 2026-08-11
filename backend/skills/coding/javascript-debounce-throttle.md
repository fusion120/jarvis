---
lang: javascript
keywords: debounce, throttle, trailing, leading, input event, resize, scroll, rate limit, requestAnimationFrame, idle
---

# Debounce & throttle

Debounce runs a function only after a quiet period (search-as-you-type, autosave); throttle guarantees at most one run per interval (scroll/resize/position updates). Both wrap a callback and return a new function — know the difference so you don't use the wrong one.

```javascript
// debounce: fires after `wait` ms of silence
function debounce(fn, wait = 300) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), wait);
  };
}

// throttle: fires at most once per interval (leading + trailing)
function throttle(fn, wait = 100) {
  let last = 0;
  let timer;
  return function (...args) {
    const now = Date.now();
    const remaining = wait - (now - last);
    const invoke = () => { last = Date.now(); fn.apply(this, args); };
    if (remaining <= 0) {                        // leading edge
      clearTimeout(timer);
      invoke();
    } else if (!timer) {                         // schedule trailing edge
      timer = setTimeout(() => { timer = null; invoke(); }, remaining);
    }
  };
}

// browser — search box fires once after the user pauses
const searchInput = document.getElementById("search");
searchInput.addEventListener("input", debounce((e) => {
  console.log("search:", e.target.value);
}, 300));

// browser — scroll logging at most every 100ms
window.addEventListener("scroll", throttle(() => {
  console.log("y:", window.scrollY);
}, 100), { passive: true });

// browser — autosave form changes after 1s idle
const save = debounce(() => {
  console.log("saving draft…");
}, 1000);
document.getElementById("title").addEventListener("input", save);
```

Gotchas:
- Debounce delays output — a button that must react instantly (game input, like/dislike) should use throttle, not debounce.
- Plain `setTimeout` debounce is trailing-only; if you need an immediate first call, call `fn()` when `timer` was null and don't schedule.
- Trailing throttle can fire once after the last event; if that's wrong, drop the trailing branch.
- Store the timer id per instance — a module-level `setTimeout` shared across elements makes them cancel each other.
- For animation-affecting work, `requestAnimationFrame` throttles to the display refresh for free.
- `clearTimeout` on an already-fired timer is a harmless no-op, so clearing unconditionally is safe.
