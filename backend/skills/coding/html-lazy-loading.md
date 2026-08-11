---
lang: html
keywords: lazy loading, loading lazy, IntersectionObserver, image loading, data-src, rootMargin, below the fold, performance
---

# Lazy Loading Images

Native `loading="lazy"` defers off-screen `<img>` loads for free. Background images can't use it, so the IntersectionObserver `data-src` pattern covers those — swap the URL only when the element nears the viewport.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lazy loading</title>
<style>
  body { margin: 0; font: 16px/1.6 system-ui; }
  main { max-width: 40rem; margin: auto; padding: 1rem; }
  img, .ph { width: 100%; height: 240px; display: block; margin-bottom: 2rem; border-radius: 8px; }
  .ph { background: linear-gradient(135deg, #79b, #7b9); display: grid; place-items: center; color: #fff; }
</style>
</head>
<body>
<main>
  <h1>Lazy loading images</h1>
  <!-- Native: the browser decides when to fetch; below-fold images wait. -->
  <img src="images/a.jpg" loading="lazy" width="640" height="240" alt="Photo A">
  <div class="ph">scroll past to trigger the observers</div>
  <div class="ph">scroll past to trigger the observers</div>
  <!-- IO fallback: background image swapped in near the viewport. -->
  <div class="ph" data-src="images/b.jpg">Photo B loads via IntersectionObserver</div>
  <div class="ph" data-src="images/c.jpg">Photo C</div>
</main>
<script>
  // Placeholder so the demo renders even with no real image files.
  const swap = img => {
    img.onerror = null;
    img.removeAttribute('srcset');
    img.src = 'data:image/svg+xml,' + encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' width='640' height='240'><rect width='100%' height='100%' fill='%2379b'/></svg>`);
  };
  for (const img of document.images) img.onerror = () => swap(img);

  const io = new IntersectionObserver(entries => {
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      const el = e.target;
      el.style.backgroundImage = `url(${el.dataset.src})`;
      io.unobserve(el); // one-shot: no more callbacks
    }
  }, { rootMargin: '200px 0px' });
  document.querySelectorAll('[data-src]').forEach(el => io.observe(el));
</script>
</body>
</html>
```

Gotchas:
- `loading="lazy"` is native and works without JS, but only for `<img>`/`<iframe>` — background images need the IntersectionObserver pattern.
- Give lazy images explicit `width`/`height` (or `aspect-ratio`) so the space is reserved — otherwise the layout jumps as images load.
- Don't lazy-load above-the-fold content: the browser waits to paint it, hurting LCP.
- `rootMargin: '200px 0px'` prefetches slightly early; a huge margin (like 3000px) loads everything anyway and defeats the purpose.
- Always `unobserve` after loading, or the observer keeps running and firing for nothing.
- A lazy image that 404s below the fold doesn't fire `error` until it's scrolled into view — error handling is deferred too.
- `width`/`height` attributes plus `height: auto` in CSS preserve the aspect ratio while still being responsive.
