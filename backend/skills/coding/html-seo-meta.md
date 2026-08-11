---
lang: html
keywords: seo meta, open graph, og tags, twitter card, meta description, canonical, robots, link preview, share card
---

# SEO Meta + OpenGraph

The `<head>` that makes a page rankable and shareable: `title`, `description`, `canonical`, OpenGraph for social link previews, and Twitter cards. The demo card below shows how platforms render `og:image`.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Acme Widget — Build faster with reusable components | Acme</title>
<meta name="description" content="Acme Widget turns JSON into sortable tables in one line. Free to install, works offline.">
<link rel="canonical" href="https://acme.example/widget">
<meta name="robots" content="index, follow">
<!-- OpenGraph (Facebook, LinkedIn, iMessage) -->
<meta property="og:type" content="product">
<meta property="og:site_name" content="Acme">
<meta property="og:title" content="Acme Widget">
<meta property="og:description" content="Sortable, filterable tables from JSON in one line.">
<meta property="og:url" content="https://acme.example/widget">
<meta property="og:image" content="https://acme.example/img/widget-card.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<!-- Twitter card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Acme Widget">
<meta name="twitter:description" content="Sortable, filterable tables from JSON in one line.">
<meta name="twitter:image" content="https://acme.example/img/widget-card.png">
<style>
  body { font: 16px/1.6 system-ui; max-width: 44rem; margin: 2rem auto; padding: 0 1rem; }
  .card { border: 1px solid #ddd; border-radius: 10px; overflow: hidden; max-width: 32rem; }
  .card .pic { width: 100%; aspect-ratio: 1200/630; object-fit: cover; background: linear-gradient(135deg, #07c, #4b8); display: block; }
  .card .body { padding: 1rem; }
  .card h2 { margin: 0 0 .25rem; font-size: 1.1rem; }
  .card p { margin: 0; color: #555; font-size: .9rem; }
</style>
</head>
<body>
<h1>SEO meta + OpenGraph</h1>
<p>This page's &lt;head&gt; is the real thing. Below is how platforms render the share card at the recommended 1200&times;630.</p>
<div class="card">
  <div class="pic" role="img" aria-label="Acme Widget marketing image"></div>
  <div class="body">
    <h2>Acme Widget</h2>
    <p>acme.example &middot; Sortable, filterable tables from JSON in one line.</p>
  </div>
</div>
</body>
</html>
```

Gotchas:
- `title` and `description` are the two highest-value tags; keep descriptions under ~155 chars or search engines truncate them.
- `og:image` should be 1200×630 (1.91:1) — small or wrong-ratio images render badly or are dropped in link previews.
- OpenGraph uses `property="og:..."`; Twitter uses `name="twitter:..."` — different attributes, get them right.
- `og:url` and `<link rel="canonical">` must point to the SAME canonical URL, or share counts and ranking split across variants.
- OG values must be absolute URLs — relative ones are ignored or broken by crawlers.
- Meta tags are suggestions, not guarantees — Google rewrites titles; strong visible `<h1>`s and content still matter most.
