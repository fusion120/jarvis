---
lang: html
keywords: flexbox nav, navigation bar, flex-wrap, margin-right auto, brand logo, align-items, responsive navbar, aria-current
---

# Flexbox Navigation Bar

The default header layout: brand on the left, links on the right, wrapping gracefully on small screens. Use this whenever a site has a horizontal nav that must survive narrow viewports without a hamburger.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Flexbox nav</title>
<style>
  body { margin: 0; font: 16px/1.5 system-ui; }
  header { background: #123; color: #fff; }
  .nav { max-width: 60rem; margin: auto; padding: 0 1rem; display: flex;
         align-items: center; gap: 1rem; flex-wrap: wrap; min-height: 3.5rem; }
  .brand { font-weight: 700; font-size: 1.25rem; margin-right: auto; }
  .nav a { color: #fff; text-decoration: none; padding: .5rem; border-radius: 4px; }
  .nav a:hover, .nav a[aria-current="page"] { background: rgb(255 255 255 / .15); }
  .cta { background: #07c; padding: .5rem 1rem !important; border-radius: 999px; }
  main { max-width: 60rem; margin: auto; padding: 1rem; }
</style>
</head>
<body>
<header>
  <nav class="nav" aria-label="Main">
    <span class="brand">Acme</span>
    <a href="#" aria-current="page">Home</a>
    <a href="#">Products</a>
    <a href="#">Blog</a>
    <a href="#" class="cta">Sign up</a>
  </nav>
</header>
<main>
  <h1>Flexbox navigation</h1>
  <p>Resize the window: links wrap to a second line because of <code>flex-wrap: wrap</code>, and the brand keeps <code>margin-right: auto</code> to push the links right.</p>
</main>
</body>
</html>
```

Gotchas:
- `margin-right: auto` on the first item is the classic "push the rest to the far side" trick — `justify-content: space-between` leaves the brand off-flush.
- Without `flex-wrap: wrap`, long link lists overflow horizontally on small screens — add it early, not after a bug report.
- `gap` in flexbox is unsupported in Safari < 14.1 — use margins on children if you must support it.
- Vertical centering: default `align-items` is `stretch`, which makes the whole bar as tall as its tallest item; set `align-items: center` for a compact bar.
- Keep tap targets comfortable: vertical padding of at least `.5rem` and full-height hit areas via `align-items: stretch`.
- Mark the current page with `aria-current="page"` on the link, not just a CSS class, or screen readers can't tell where they are.
