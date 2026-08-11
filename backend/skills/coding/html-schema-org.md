---
lang: html
keywords: schema.org, microdata, json-ld, structured data, itemscope, itemprop, rich results, product schema, aggregate rating
---

# Schema.org Microdata + JSON-LD

Tell search engines what a page IS with structured data. Two syntaxes exist: microdata (`itemscope`/`itemprop`) lives in the markup, JSON-LD in a `<script>`. Google prefers JSON-LD; microdata still works.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Acme Widget 2.0 — product schema</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 40rem; margin: 2rem auto; padding: 0 1rem; }
  .price { font-weight: 700; }
  .rating { color: #b90; }
</style>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Acme Widget 2.0",
  "image": "https://acme.example/img/widget.png",
  "description": "Sortable tables from JSON in one line.",
  "brand": { "@type": "Brand", "name": "Acme" },
  "offers": { "@type": "Offer", "priceCurrency": "USD", "price": "29.00", "availability": "https://schema.org/InStock" },
  "aggregateRating": { "@type": "AggregateRating", "ratingValue": "4.7", "reviewCount": "128" }
}
</script>
</head>
<body>
<h1>Schema.org microdata + JSON-LD</h1>
<p>This page declares itself a Product <b>twice</b> to demonstrate both syntaxes:</p>
<div itemscope itemtype="https://schema.org/Product">
  <h2 itemprop="name">Acme Widget 2.0</h2>
  <p itemprop="description">Sortable tables from JSON in one line.</p>
  <span class="price" itemprop="offers" itemscope itemtype="https://schema.org/Offer">
    <meta itemprop="priceCurrency" content="USD"><meta itemprop="price" content="29.00">
    $<span itemprop="price">29.00</span>
  </span>
  <div itemprop="aggregateRating" itemscope itemtype="https://schema.org/AggregateRating">
    <span class="rating" itemprop="ratingValue">4.7</span>/5 from <span itemprop="reviewCount">128</span> reviews
  </div>
</div>
<p>Microdata uses <code>itemscope</code>/<code>itemprop</code> attributes; the JSON-LD block in the head is the modern alternative — most sites ship JSON-LD only.</p>
</body>
</html>
```

Gotchas:
- JSON-LD is the Google-preferred syntax; microdata works but you don't need both — this page shows each for reference.
- Nest scopes correctly: an `itemprop="offers"` value must itself carry `itemscope` + its own `itemtype`, or its properties attach to the wrong node.
- Use `<meta>` tags for data that isn't visible (currency, dates) — crawlers read them, users don't see them.
- `price` should be a plain string "29.00" (no comma formatting); `ratingValue` is 0–5, `reviewCount` an integer.
- Validate with Google's Rich Results Test before shipping — one wrong type name silently disables the snippet.
- Don't mark up what isn't true — fabricated aggregate ratings can get your domain actioned for spam.
