---
lang: html
keywords: print stylesheet, print css, @media print, page breaks, page-break-inside, print-color-adjust, orphans widows, print preview
---

# Print Stylesheet

Make a page legible on paper: hide the nav and chrome, show link URLs, control page breaks, and keep headings with their paragraphs. Everything lives in one `@media print` block.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Print stylesheet</title>
<style>
  body { font: 16px/1.6 Georgia, serif; margin: 0; }
  header, nav { background: #123; color: #fff; padding: 1rem; }
  nav a, header a { color: #fff; margin-right: 1rem; }
  main { max-width: 44rem; margin: auto; padding: 2rem 1rem; }
  a { color: #07c; }
  /* ---- print ---- */
  @media print {
    header, nav, footer, .no-print { display: none !important; }
    body { font-size: 12pt; }
    main { max-width: none; padding: 0; }
    a { color: #000; text-decoration: none; }
    a[href^="http"]::after { content: " (" attr(href) ")"; font-size: 90%; color: #555; }
    h1, h2, h3 { page-break-after: avoid; }
    p, li { orphans: 3; widows: 3; }
    table, img, pre { page-break-inside: avoid; }
    .print-color { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  }
</style>
</head>
<body>
<header><a href="#">Site</a><nav aria-label="Main"><a href="#">Home</a><a href="#">About</a></nav></header>
<main>
  <h1>Print stylesheet demo</h1>
  <p class="print-color" style="background:#ffe08a; padding:.5rem">Colored callout — preserved with <code>print-color-adjust: exact</code>.</p>
  <p>Open print preview: the nav and header disappear, links reveal their URL, headings stay with their content, and paragraphs never split into single orphan lines. Read more at <a href="https://example.com/guide">example.com/guide</a>.</p>
</main>
</body>
</html>
```

Gotchas:
- Everything in print is opt-in: you must explicitly hide nav/ads and reset layout, or `position: fixed` elements repeat on every printed page.
- `page-break-inside: avoid` on tables/images stops mid-element splits; `page-break-after: avoid` on headings keeps them glued to the next paragraph.
- `orphans`/`widows` set minimum lines kept together — 3 is the standard safe value.
- Browsers drop background colors by default — `print-color-adjust: exact` (with `-webkit-` prefix) opts elements back in, and users must still enable "Background graphics" in the print dialog.
- Reveal link URLs with `a[href^="http"]::after { content: " (" attr(href) ")"; }` — filter to http(s) or in-page anchors get noise.
- `display: none !important` on chrome is the robust hide; a print stylesheet relying on specificity alone often leaks elements.
