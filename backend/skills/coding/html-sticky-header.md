---
lang: html
keywords: sticky header, position sticky, scroll-margin-top, backdrop-filter, navbar, anchor scroll, scroll shadow
---

# Sticky Header

A header that pins to the top while content scrolls under it. Add `scroll-margin-top` so in-page anchors don't hide their titles beneath the pinned bar, and a shadow that appears once you scroll.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sticky header</title>
<style>
  html { scroll-behavior: smooth; }
  body { margin: 0; font: 16px/1.5 system-ui; }
  header { position: sticky; top: 0; z-index: 10; background: rgb(255 255 255 / .85);
           backdrop-filter: blur(8px); border-bottom: 1px solid #eee; transition: box-shadow .2s; }
  .inner { max-width: 60rem; margin: auto; padding: .75rem 1rem; display: flex;
           justify-content: space-between; align-items: center; }
  nav { display: flex; gap: 1rem; }
  a { text-decoration: none; color: #07c; }
  main { max-width: 60rem; margin: auto; padding: 1rem; }
  section { scroll-margin-top: 5rem; border-bottom: 1px dashed #ddd; padding: 3rem 0; }
  .scrolled { box-shadow: 0 2px 8px rgb(0 0 0 / .1); }
</style>
</head>
<body>
<header id="top">
  <div class="inner">
    <strong>Logo</strong>
    <nav aria-label="Main">
      <a href="#one">One</a><a href="#two">Two</a><a href="#three">Three</a>
    </nav>
  </div>
</header>
<main>
  <section id="one"><h1>One</h1><p>Scroll down — the header stays pinned.</p></section>
  <section id="two"><h2>Two</h2><p>Anchors jump clear of the header thanks to <code>scroll-margin-top</code>.</p></section>
  <section id="three"><h2>Three</h2><p>Shadow appears once you scroll, via a class toggle.</p></section>
</main>
<script>
  const header = document.getElementById('top');
  const onScroll = () => header.classList.toggle('scrolled', scrollY > 8);
  addEventListener('scroll', onScroll, { passive: true });
  onScroll();
</script>
</body>
</html>
```

Gotchas:
- `position: sticky` needs a `top`/`bottom` offset AND a scrollable ancestor; a parent with `overflow: hidden/auto/scroll` silently breaks it (acts static).
- Without `z-index`, later siblings paint over the sticky element — content scrolls on top of the header.
- Anchored sections need `scroll-margin-top` roughly equal to header height, or their titles hide underneath when jumped to.
- `backdrop-filter: blur` has no fallback on old browsers — keep a translucent `background` under it or text shows through sharp.
- Scroll listeners should be `{ passive: true }`; also cache the header element and use `classList.toggle` instead of reading/writing layout each frame.
- `top: 0` sticks to the viewport top; a sticky footer uses `bottom: 0` — but only one axis sticks per element.
