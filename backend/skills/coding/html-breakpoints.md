---
lang: html
keywords: media queries, breakpoints, responsive design, mobile first, min-width, grid columns, prefers-reduced-motion, viewport
---

# Media Queries / Breakpoints

Lay out for the smallest screen first, then add complexity with `min-width` queries. Mobile-first media queries only ever ADD layout — nothing needs un-doing when the screen grows.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Breakpoints</title>
<style>
  /* Mobile-first: single column */
  body { margin: 0; font: 16px/1.6 system-ui; }
  main { padding: 1rem; display: grid; gap: 1rem; }
  .card { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; }
  .banner { padding: 1rem; background: #07c; color: #fff; border-radius: 8px; }
  /* Tablet: two columns */
  @media (min-width: 700px) {
    main { grid-template-columns: 1fr 1fr; }
    .banner { grid-column: 1 / -1; }
  }
  /* Desktop: three columns */
  @media (min-width: 1000px) {
    main { grid-template-columns: 2fr 1fr 1fr; max-width: 70rem; margin: auto; }
    .banner { font-size: 1.5rem; }
  }
  /* Users who prefer less motion */
  @media (prefers-reduced-motion: reduce) {
    * { animation: none !important; transition: none !important; }
  }
</style>
</head>
<body>
<main>
  <div class="banner">Resize the window: 1 column &rarr; 2 &rarr; 3.</div>
  <div class="card">Card A</div>
  <div class="card">Card B</div>
  <div class="card">Card C</div>
</main>
</body>
</html>
```

Gotchas:
- Write mobile-first: base styles for small screens, then `min-width` queries that only add — `max-width` queries force you to reset things back.
- Breakpoint values are arbitrary — derive them from where your content naturally collapses, not from device names like "iPad".
- Mixing `min-width` and `max-width` in one stylesheet gets messy fast; pick one direction and stay consistent.
- `prefers-reduced-motion` and `prefers-color-scheme` are media queries too — different from layout breakpoints, don't lump them in the same number scheme.
- Without `<meta name="viewport" content="width=device-width, initial-scale=1">` media queries respond to the layout viewport (often 980px), not the device width.
- Query ranges can use `and`: `@media (min-width: 700px) and (max-width: 999px)` for a precise band.
