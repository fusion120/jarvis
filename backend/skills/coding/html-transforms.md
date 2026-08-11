---
lang: html
keywords: css transforms, transitions, hover card, scale, translate, rotate, transform-origin, will-change, cubic-bezier
---

# CSS Transforms + Transitions

The lift-on-hover card: `transform` (scale/translate/rotate) animated by `transition`. Transforms are compositor-friendly and don't trigger layout — the cheapest way to make UI feel alive.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Transforms &amp; transitions</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 40rem; margin: 3rem auto; padding: 0 1rem; }
  .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
  .box { aspect-ratio: 1; display: grid; place-items: center; color: #fff; font-weight: 700;
         background: #07c; border-radius: 12px; transition: transform .3s ease, box-shadow .3s ease;
         will-change: transform; }
  .box:hover, .box:focus-visible { transform: translateY(-6px) scale(1.05) rotate(2deg); box-shadow: 0 12px 24px rgb(0 0 0 / .2); }
  .spin { transition: transform 1.5s cubic-bezier(.2, .8, .2, 1); }
  .spin:hover { transform: rotate(180deg); }
</style>
</head>
<body>
<h1>Transforms &amp; transitions</h1>
<div class="grid">
  <button class="box">lift</button>
  <button class="box spin">spin</button>
  <button class="box">3-in-1</button>
</div>
<p>Transforms don't reflow layout — but a transformed ancestor becomes a containing block, so <code>position: fixed</code> children position relative to it, not the viewport.</p>
</body>
</html>
```

Gotchas:
- Transform order matters: `translateX(10px) scale(2)` is NOT the same as `scale(2) translateX(10px)` — transforms compose right-to-left.
- Any non-`none` transform makes the element a stacking context AND a containing block — fixed descendants anchor to it, not the viewport.
- Prefer `transition` on `transform`/`opacity` only; `transition: all` animates layout properties (`top`, `width`) and causes reflow churn.
- `will-change: transform` hints the compositor but costs GPU layers — add it only to elements you actually animate, and remove it when done.
- `transform-origin` defaults to center; rotating around a corner needs `transform-origin: top left`.
- Make interactive cards real `<button>`s and keep a `:focus-visible` outline — hover-only feedback is invisible to keyboard users.
