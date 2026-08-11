---
lang: html
keywords: svg chart, bar chart, line chart, data visualization, createElementNS, viewBox, svg text, scale data
---

# SVG Bar + Line Chart from Data

Build charts as SVG with `createElementNS` so they stay crisp at any size and remain inspectable DOM. The pattern here — scale data into pixel coordinates, append bars, overlay a line — extends to any chart type.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SVG chart</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 40rem; margin: 2rem auto; padding: 0 1rem; }
  .chart { width: 100%; height: auto; }
  .bar { fill: #07c; }
  .bar:hover { fill: #05a; }
  .label { font: 12px system-ui, sans-serif; fill: #555; }
</style>
</head>
<body>
<h1>SVG bar + line chart</h1>
<svg class="chart" viewBox="0 0 560 300" role="img" aria-label="Monthly sales, rising from 12 to 55">
  <title>Monthly sales</title>
  <desc>Bars show sales for January through June: 12, 18, 24, 33, 42, 55.</desc>
  <g id="plot"></g>
</svg>
<script>
  const data = [12, 18, 24, 33, 42, 55];
  const W = 560, H = 300, pad = 30, max = Math.max(...data) * 1.1;
  const ns = 'http://www.w3.org/2000/svg';
  const plot = document.getElementById('plot');
  const bw = (W - pad * 2) / data.length;

  // Bars + labels
  data.forEach((v, i) => {
    const x = pad + i * bw, h = (v / max) * (H - pad * 2), y = H - pad - h;
    const bar = document.createElementNS(ns, 'rect');
    bar.setAttribute('class', 'bar');
    bar.setAttribute('x', x + bw * .15); bar.setAttribute('width', bw * .7);
    bar.setAttribute('y', y); bar.setAttribute('height', h);
    plot.append(bar);
    const lab = document.createElementNS(ns, 'text');
    lab.setAttribute('class', 'label'); lab.setAttribute('x', x + bw / 2); lab.setAttribute('y', H - pad + 16);
    lab.setAttribute('text-anchor', 'middle'); lab.textContent = 'M' + (i + 1);
    plot.append(lab);
  });

  // Line series on top
  let d = '';
  data.forEach((v, i) => {
    const x = pad + i * bw + bw / 2, y = H - pad - (v / max) * (H - pad * 2);
    d += (i ? 'L' : 'M') + x + ' ' + y;
  });
  const line = document.createElementNS(ns, 'path');
  line.setAttribute('d', d);
  line.setAttribute('fill', 'none'); line.setAttribute('stroke', '#c00'); line.setAttribute('stroke-width', '2');
  plot.append(line);
</script>
</body>
</html>
```

Gotchas:
- SVG text doesn't inherit page fonts — set `font-family` on a `.label` class or labels render in the UA default.
- `createElementNS('http://www.w3.org/2000/svg', 'rect')` is required; plain `createElement('rect')` makes an HTMLUnknownElement that renders nothing.
- SVG attributes are case-sensitive: `viewBox`, `text-anchor`, `preserveAspectRatio` — typo them and the element silently ignores them.
- Pad your scale on all sides or axis labels clip; and use `max * 1.1` so the tallest bar never touches the top edge.
- Screen readers can't see SVG bars — add `role="img"` + `aria-label`, `<title>`, and `<desc>` with the data summary.
- The chart is empty until the script runs; for content-critical data, ship static markup or a `<noscript>` fallback.
