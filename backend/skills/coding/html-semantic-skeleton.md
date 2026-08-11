---
lang: html
keywords: semantic html, page skeleton, landmarks, header, nav, main, footer, skip link, aria, html5 structure, accessible layout
---

# Semantic Page Skeleton with ARIA Landmarks

Every site starts as a page skeleton. Reach for this whenever you hand-code a content page from scratch: semantic landmarks (`header`, `nav`, `main`, `aside`, `footer`) plus a skip link give screen-reader and keyboard users the same structure sighted users see.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Semantic skeleton</title>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; font: 16px/1.5 system-ui, sans-serif; display: grid;
         grid-template-columns: 200px 1fr; grid-template-areas:
         "h h" "n m" "f f"; min-height: 100vh; }
  header { grid-area: h; background: #123; color: #fff; padding: 1rem; }
  nav    { grid-area: n; background: #eee; padding: 1rem; }
  nav a  { display: block; padding: .25rem 0; }
  main   { grid-area: m; padding: 1rem; }
  footer { grid-area: f; background: #123; color: #fff; padding: 1rem; text-align: center; }
  .skip-link { position: absolute; left: -999px; top: 0; background: #fff; padding: .5rem; z-index: 10; }
  .skip-link:focus { left: 0; }
</style>
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header>
    <h1>Site title</h1>
  </header>
  <nav aria-label="Primary">
    <a href="#">Home</a>
    <a href="#">About</a>
  </nav>
  <main id="main">
    <article>
      <h2>Post heading</h2>
      <p>Content goes here. <code>article</code> inside <code>main</code> is a nested landmark.</p>
    </article>
    <aside>
      <h3>Related links</h3>
      <p>Secondary content such as ads or further reading.</p>
    </aside>
  </main>
  <footer><p>&copy; 2026</p></footer>
</body>
</html>
```

Gotchas:
- Never use `<div>` for page regions — landmarks give screen-reader users a navigation menu of the page.
- One `<main>` per page, with an `id` so the skip link has a target; skip links must be visually hidden but focusable (the `left: -999px` + `:focus` pattern).
- Headings must descend without skipping levels (`h1` → `h2` → `h3`); a missing level confuses the outline.
- Add `aria-label` to `<nav>` when there are multiple nav elements, or they announce as identical landmarks.
- Put `lang` and `charset` early in the head or screen readers and SEO mis-detect content.
- Don't put `<aside>` inside `<article>` unless the aside content is specific to that article.
