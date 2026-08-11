---
lang: html
keywords: css grid, grid layout, auto-fit, minmax, grid-template-areas, responsive columns, grid gap, repeat, span
---

# CSS Grid Layout

Grid is the tool for two-dimensional page and card layouts. Reach for it when you need columns AND rows to align — a card grid that flows into extra rows automatically, or a page shell where header/nav/main/footer each own a named area.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CSS grid layout</title>
<style>
  body { font: 16px/1.5 system-ui; margin: 0; }
  main { display: grid; gap: 1rem; padding: 1rem;
         grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
  .card { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; background: #fff; }
  .card.featured { grid-column: span 2; border-color: #07c; }
  header { display: grid; grid-template-columns: 1fr auto; align-items: center;
           padding: 1rem; background: #123; color: #fff; }
  header nav { display: flex; gap: 1rem; }
  header a { color: #fff; text-decoration: none; }
  footer { padding: 1rem; text-align: center; background: #eee; }
</style>
</head>
<body>
<header>
  <h1>Grid demo</h1>
  <nav aria-label="Main"><a href="#">Home</a><a href="#">About</a></nav>
</header>
<main>
  <article class="card featured"><h2>Feature</h2><p>Spans two columns on wide screens, collapses to one on small ones.</p></article>
  <article class="card"><h2>Card</h2><p>auto-fit + minmax means no media query needed for the columns.</p></article>
  <article class="card"><h2>Card</h2><p>Rows are auto-sized; gap handles all spacing.</p></article>
  <article class="card"><h2>Card</h2><p>minmax(240px, 1fr) caps cards at ~240px before wrapping.</p></article>
</main>
<footer>Footer spans the full width automatically.</footer>
</body>
</html>
```

Gotchas:
- `repeat(auto-fit, minmax(240px, 1fr))` collapses empty tracks (auto-fill keeps them) — pick based on whether the last row should stretch full width.
- `grid-column: span 2` overflows when the screen fits only one column — reset it to `span 1` in a small-screen media query.
- Grid tracks default to `auto`; tall content then dictates row height — set `grid-auto-rows` when you want uniform rows.
- `1fr` is really `minmax(auto, 1fr)`, so long unbreakable words blow out a column; add `min-width: 0` to grid children.
- Use `gap` for spacing, never margin hacks — margins on children double up with gutters.
- `grid-template-areas` is the readable way to name regions; the ASCII layout must spell a valid rectangle or the rule is dropped silently.
