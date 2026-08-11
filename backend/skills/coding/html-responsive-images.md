---
lang: html
keywords: responsive images, picture element, srcset, sizes, art direction, source media, img fallback, retina, responsive
---

# Responsive Images: `<picture>`, `srcset`, `sizes`

Two jobs, two tools: `srcset` + `sizes` picks the right file size for the viewport (resolution switching); `<picture>` + `<source media>` swaps the whole crop (art direction). Both belong whenever an image renders at different widths.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Responsive images</title>
<style>
  body { margin: 0; font: 16px/1.6 system-ui; }
  main { max-width: 60rem; margin: auto; padding: 1rem; }
  img { width: 100%; height: auto; display: block; border-radius: 8px; }
  figure { margin: 1.5rem 0; }
  figcaption { color: #666; font-size: .9rem; margin-top: .5rem; }
</style>
</head>
<body>
<main>
  <h1>Responsive images</h1>

  <!-- Art direction: crop changes with screen width -->
  <figure>
    <picture>
      <source media="(min-width: 1000px)" srcset="images/hero-wide.jpg">
      <source media="(min-width: 600px)" srcset="images/hero-mid.jpg">
      <img src="images/hero-narrow.jpg" alt="Mountain valley at dawn"
           onerror="swap(this,'560 380')">
    </picture>
    <figcaption>Art direction: same subject, different crops.</figcaption>
  </figure>

  <!-- Resolution switching: same image, different pixel sizes -->
  <figure>
    <img src="images/detail-480.jpg"
         srcset="images/detail-480.jpg 480w, images/detail-960.jpg 960w, images/detail-1440.jpg 1440w"
         sizes="(min-width: 1000px) 60rem, 100vw"
         alt="Detail shot of the valley"
         onerror="swap(this,'960 540')">
    <figcaption>srcset + sizes pick the closest candidate for the viewport and DPR.</figcaption>
  </figure>
</main>
<script>
  // Stand-in so the demo renders without the real image files.
  window.swap = (img, dims) => {
    img.onerror = null;
    img.removeAttribute('srcset');
    const [w, h] = dims.split(' ').map(Number);
    const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='${w}' height='${h}'><rect width='100%' height='100%' fill='%234b79a1'/><text x='50%' y='50%' fill='%23fff' font-size='24' text-anchor='middle' dominant-baseline='middle'>${w}x${h} placeholder</text></svg>`;
    img.src = 'data:image/svg+xml,' + encodeURIComponent(svg);
  };
</script>
</body>
</html>
```

Gotchas:
- `<source>` elements have no DOM events and aren't addressable — put fallback/error logic on the `<img>` inside the `<picture>`.
- `sizes` is REQUIRED with `w` descriptors; without it the browser assumes `100vw` and downloads the largest image.
- `sizes` must describe the TRUE rendered width (CSS included), or you get giant or soft images — guess wrong and you waste megabytes.
- `alt` lives on `<img>`, never on `<source>`; only the img is exposed to assistive tech.
- Use `media` for art direction and `srcset` for resolution — swapping crops via srcset or sizing via picture is misuse that either breaks or duplicates.
- Add `fetchpriority="high"` to the hero image and `loading="lazy"` to below-fold ones; images are the #1 cause of slow LCP.
