---
lang: html
keywords: scroll reveal, IntersectionObserver, reveal on scroll, fade in, threshold, rootMargin, unobserve, scroll animation
---

# IntersectionObserver Scroll Reveal

Fade elements up as they enter the viewport. `IntersectionObserver` fires once per element, so a `threshold` decides how much must be visible, and `unobserve` stops the work after the reveal.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Scroll reveal</title>
<style>
  body { margin: 0; font: 16px/1.6 system-ui; }
  main { max-width: 40rem; margin: auto; padding: 2rem 1rem; }
  .reveal { opacity: 0; transform: translateY(24px); transition: opacity .6s ease, transform .6s ease; }
  .reveal.visible { opacity: 1; transform: none; }
  .card { background: #f4f7fb; border: 1px solid #e0e6ef; border-radius: 10px; padding: 1.5rem; margin-bottom: 2rem; }
</style>
</head>
<body>
<main>
  <h1>IntersectionObserver reveal</h1>
  <p>Cards start invisible and fade up as they enter the viewport. The observer runs once and unobserves each card.</p>
  <div class="reveal card"><h2>One</h2><p>First fold.</p></div>
  <div class="reveal card"><h2>Two</h2><p>Below the fold.</p></div>
  <div class="reveal card"><h2>Three</h2><p>Further down.</p></div>
</main>
<script>
  const io = new IntersectionObserver(entries => {
    for (const e of entries) {
      if (e.isIntersecting) {
        e.target.classList.add('visible');
        io.unobserve(e.target); // one-shot: no more callbacks
      }
    }
  }, { threshold: 0.15 });
  document.querySelectorAll('.reveal').forEach(el => io.observe(el));
</script>
</body>
</html>
```

Gotchas:
- `threshold: 0.15` means 15% of the ELEMENT must be visible; threshold 0 fires the moment one pixel enters — pick by element size, big cards need higher thresholds.
- Always `unobserve` after revealing; otherwise the callback fires on every scroll forever and holds the observation alive.
- If JS fails or IO is unsupported, content stays invisible — ship a `.no-js`/noscript rule that sets everything visible.
- The transition needs the base state (`.reveal`) and the changed state (`.visible`) — putting the `transition` only on `.visible` breaks the animation in both directions.
- `rootMargin` pre-triggers the reveal; too aggressive a margin reveals things before users actually scroll to them.
- Under `prefers-reduced-motion`, skip the translate (keep a subtle fade or show content immediately).
