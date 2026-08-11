---
lang: html
keywords: svg icons, inline svg, symbol sprite, use element, currentColor, icon system, aria-hidden, accessible icons
---

# Inline SVG Icon Sprite

Define every icon once inside an SVG `<defs>` block of `<symbol>`s, then stamp it anywhere with `<use>`. Icons inherit `currentColor`, so one CSS rule recolors the whole set, and each use carries its own `role`/`aria-label`.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Inline SVG icons</title>
<style>
  .icon { width: 1.25em; height: 1.25em; vertical-align: -.25em; fill: currentColor; }
  .icons { display: flex; gap: 1.5rem; align-items: center; padding: 1rem; font-size: 1.5rem; }
  button { display: inline-flex; align-items: center; gap: .5rem; padding: .5rem 1rem; cursor: pointer; }
</style>
</head>
<body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <defs>
    <symbol id="i-heart" viewBox="0 0 24 24"><path d="M12 21S4 14.6 4 8.9C4 6 6.4 4 8.8 4c1.3 0 2.6.6 3.2 1.7C12.6 4.6 13.9 4 15.2 4 17.6 4 20 6 20 8.9c0 5.7-8 12.1-8 12.1z"/></symbol>
    <symbol id="i-star" viewBox="0 0 24 24"><path d="M12 2l2.9 6.3 6.9.8-5.1 4.7 1.4 6.8L12 17l-6.1 3.6 1.4-6.8L2.2 9.1l6.9-.8L12 2z"/></symbol>
    <symbol id="i-save" viewBox="0 0 24 24"><path d="M5 3h12l3 3v15H4V3zm4 0v6h6V3zm-2 18h10v-8H7z"/></symbol>
  </defs>
</svg>

<h1>Inline SVG icon sprite</h1>
<div class="icons">
  <svg class="icon" role="img" aria-label="Heart"><use href="#i-heart"/></svg>
  <svg class="icon" role="img" aria-label="Star"><use href="#i-star"/></svg>
  <svg class="icon" role="img" aria-label="Save"><use href="#i-save"/></svg>
</div>
<button type="button">
  <svg class="icon" aria-hidden="true"><use href="#i-save"/></svg>
  Save changes
</button>
<p>Icons inherit <code>currentColor</code>, so one CSS rule recolors every icon across the whole app.</p>
<script>
  // Older browsers need xlink:href — add it without breaking modern ones.
  document.querySelectorAll('use').forEach(u => {
    if (!u.getAttribute('xlink:href')) u.setAttribute('xlink:href', u.getAttribute('href'));
  });
</script>
</body>
</html>
```

Gotchas:
- Give icons meaning: `role="img"` + `aria-label` for standalone icons; `aria-hidden="true"` when adjacent text already describes the action.
- Set `fill: currentColor` in CSS, not per-path, or the icons can't be recolored by text color changes.
- The hidden sprite block must not be focusable or announced — `width="0" height="0"` + `aria-hidden="true"`.
- Modern browsers use `href`; Safari < 12 needs `xlink:href`. Setting both keeps icons working everywhere.
- `<use>` references clone the symbol's internal markup, so you can't style internals differently per-use; multi-color icons deserve dedicated inline SVGs.
- Every `<symbol>` needs a `viewBox` or the icon ignores your CSS size and renders at the default scale.
