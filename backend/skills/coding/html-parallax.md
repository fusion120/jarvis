---
lang: html
keywords: parallax scroll, parallax, scroll effect, background-attachment fixed, requestAnimationFrame scroll, scroll speed, depth
---

# Parallax Scroll

Layers moving at different speeds create depth. This shows the two techniques: the zero-JS `background-attachment: fixed` and the JS `translateY`-on-scroll version, throttled with `requestAnimationFrame`.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Parallax scroll</title>
<style>
  body { margin: 0; font: 16px/1.6 system-ui; }
  .hero { min-height: 60vh; display: grid; place-items: center; color: #fff; position: relative; overflow: hidden; }
  .hero .bg { position: absolute; inset: -20% 0; background: linear-gradient(180deg, #123, #07c); }
  .hero h1 { position: relative; z-index: 1; }
  .content { max-width: 44rem; margin: auto; padding: 3rem 1rem; }
  .par { background-color: #333; color: #fff; text-align: center; padding: 4rem 1rem;
         background-image: url(data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20width='40'%20height='40'%3E%3Crect%20width='40'%20height='40'%20fill='%23333'/%3E%3Cpath%20d='M0%2020h40M20%200v40'%20stroke='%23555'%20stroke-width='1'/%3E%3C/svg%3E);
         background-attachment: fixed; background-size: cover; }
</style>
</head>
<body>
<div class="hero">
  <div class="bg" id="bg"></div>
  <h1>Parallax</h1>
</div>
<div class="content">
  <p>Scrolling moves the hero background slower than the text — two layers moving at different speeds create depth.</p>
  <div class="par">background-attachment: fixed</div>
  <p>More content to scroll... Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>
</div>
<script>
  const bg = document.getElementById('bg');
  let raf = null;
  function update() {
    raf = null;
    bg.style.transform = `translateY(${scrollY * 0.4}px)`;
  }
  addEventListener('scroll', () => { if (!raf) raf = requestAnimationFrame(update); }, { passive: true });
  update();
</script>
</body>
</html>
```

Gotchas:
- Throttle scroll handlers with `requestAnimationFrame` and use `{ passive: true }` — raw scroll fires far more often than paint, and a non-passive handler janks the page.
- `background-attachment: fixed` is the zero-JS trick, but it's ignored/disabled on iOS Safari and forces expensive repaints — use JS translate for interactive sites.
- The parallax layer needs `overflow: hidden` on the section AND extra bleed (`inset: -20%`) or the edges show gaps mid-scroll.
- Respect `prefers-reduced-motion` — skip the parallax and keep content static for those users.
- Keep speed factors small (0.1–0.5); strong parallax causes motion sickness and reflows layout as it moves.
- `will-change: transform` on the parallax layer (not the section) keeps it on its own compositor layer.
