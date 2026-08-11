---
lang: javascript
keywords: matchMedia, media query, responsive, prefers-color-scheme, breakpoint, addListener, change event, prefers-reduced-motion, orientation
---

# matchMedia & responsive behavior

`window.matchMedia(query)` evaluates a CSS media query in JS and gives you a `MediaQueryList` you can listen to — the JS mirror of CSS breakpoints, dark mode, and reduced-motion preferences. Use the change event (not resize hacks) to react when the query flips.

```javascript
// browser
const dark = window.matchMedia("(prefers-color-scheme: dark)");

function applyTheme(isDark) {
  document.documentElement.dataset.theme = isDark ? "dark" : "light";
  document.getElementById("status").textContent =
    isDark ? "dark mode on" : "light mode on";
}

// initial state (synchronous)
applyTheme(dark.matches);

// react to changes (fires on flip, also respects OS change while open)
dark.addEventListener("change", (e) => applyTheme(e.matches));

// Breakpoint: switch a layout behavior at 768px
const tablet = window.matchMedia("(min-width: 768px)");
function applyLayout(matches) {
  document.body.classList.toggle("tablet-layout", matches);
}
tablet.addEventListener("change", (e) => applyLayout(e.matches));
applyLayout(tablet.matches);

// Reduced motion: disable heavy animation for users who ask
const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
if (reduce.matches) {
  document.documentElement.classList.add("reduce-motion");
}

// Combining queries
const landscapeNarrow = window.matchMedia(
  "(orientation: landscape) and (max-width: 700px)"
);
console.log(landscapeNarrow.matches);
```

Gotchas:
- `addEventListener("change", …)` is the modern API; `addListener`/`removeListener` are deprecated legacy aliases (don't mix per-instance).
- Read `.matches` synchronously at load for the initial state — the change event only fires on transitions, not for the current value.
- The event object is a new `MediaQueryListEvent` each time — use `e.matches`, don't reuse a stored event.
- Don't duplicate CSS: matchMedia in JS shouldn't re-implement styles — use it for BEHAVIOR (data loading, chart sizing) while CSS keeps visuals.
- `prefers-color-scheme` is a hint, not a guarantee — users can override; also handle an explicit theme toggle in localStorage taking priority.
- Resize-based breakpoint logic (`window.onresize`) fires continuously; matchMedia fires only on actual flips — prefer matchMedia.
- Older browsers need a `change` event polyfill; modern evergreen browsers are fine.
