---
lang: html
keywords: fluid typography, clamp, css clamp, vw units, responsive text, type scale, min max font size
---

# Fluid Typography with `clamp()`

Make headings and body text scale smoothly between a minimum and maximum as the viewport changes — no media queries. `clamp(min, preferred, max)` picks the preferred value but never goes outside the bounds.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fluid typography</title>
<style>
  :root {
    --step-lg: clamp(1.5rem, 1rem + 2.5vw, 3rem);
    --step-md: clamp(1rem, .8rem + .8vw, 1.25rem);
  }
  body { margin: 0; font-family: system-ui; color: #222; line-height: 1.6; }
  main { max-width: 48rem; margin: auto; padding: 2rem 1rem; }
  h1 { font-size: var(--step-lg); margin: 0 0 .5em; }
  p  { font-size: var(--step-md); }
  .note { color: #666; font-size: var(--text-sm, .875rem); }
</style>
</head>
<body>
<main>
  <h1>Fluid type with clamp()</h1>
  <p><code>clamp(min, preferred, max)</code> scales text smoothly between a minimum and maximum. At 320px the h1 is ~1.5rem; at 1200px it is 3rem — no media query needed.</p>
  <p class="note">This paragraph is clamped between 1rem and 1.25rem, so it stays readable on phones and never balloons on desktops.</p>
</main>
</body>
</html>
```

Gotchas:
- `clamp()` arguments must be ordered min < preferred < max; a backwards order makes the browser clamp to the max and the rule silently misbehaves.
- The `vw` part scales with the VIEWPORT, not the container — inside a narrow sidebar the type still follows the window; use container-query units (`cqi`) for container-relative sizing.
- Give the preferred value a non-zero base (`1rem + 2.5vw`), or at 320px the pure `2.5vw` term collapses to ~8px.
- Accessibility: keep the min above ~1rem and test at 400% zoom; fluid type must not shrink below readable.
- Don't clamp `line-height` the same way — let it scale with font-size or lines get cramped on large headings.
- `clamp()` works on any length property, not just font-size — use it for fluid paddings and gaps too.
