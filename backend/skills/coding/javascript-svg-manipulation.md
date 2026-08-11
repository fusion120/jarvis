---
lang: javascript
keywords: svg, createElementNS, setAttribute, viewBox, path, circle, foreignObject, transform, namespace, insertSVG
---

# SVG manipulation

SVG is XML — elements live in the `http://www.w3.org/2000/svg` namespace, so `createElement("circle")` produces an HTML element that won't render. Use `createElementNS`, set attributes with `setAttribute`, and control scaling through `viewBox`.

```javascript
// browser
const svg = document.getElementById("chart");
// <svg id="chart" viewBox="0 0 200 200" width="200" height="200"></svg>
const NS = "http://www.w3.org/2000/svg";

function makeEl(tag, attrs = {}) {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

// Build a bar chart dynamically
const data = [42, 18, 73, 55];
const barW = 40;
data.forEach((value, i) => {
  const rect = makeEl("rect", {
    x: i * (barW + 10) + 10,
    y: 200 - value,
    width: barW,
    height: value,
    fill: "#4caf50",
    rx: 4,
  });
  svg.append(rect);

  const label = makeEl("text", {
    x: i * (barW + 10) + barW / 2 + 10,
    y: 200 - value - 6,
    "text-anchor": "middle",
    class: "bar-label",
  });
  label.textContent = String(value);
  svg.append(label);
});

// Interact: SVG elements are DOM nodes — attach listeners directly
svg.querySelectorAll("rect").forEach((r) => {
  r.addEventListener("click", () => {
    r.setAttribute("fill", "#ff5722");
  });
});

// Path: draw a line chart
const points = data.map((v, i) => `${i * 50},${200 - v}`).join(" L ");
const path = makeEl("path", {
  d: `M ${points}`,
  fill: "none",
  stroke: "#2196f3",
  "stroke-width": 3,
});
svg.append(path);
```

Gotchas:
- ALWAYS use `createElementNS` for SVG tags — plain `createElement("rect")` creates an HTML element and nothing renders (a silent no-op).
- Attributes are dash-case strings: `stroke-width`, `text-anchor`, `viewBox` — `setAttribute("strokeWidth")` does nothing.
- CSS can style SVG (fill, stroke) and wins over presentation attributes; inline `style` beats both.
- `innerHTML` works on SVG for markup strings but you lose references and risk parsing quirks; prefer `createElementNS` for dynamic content.
- `viewBox` sets the coordinate system; without it, coordinates are pixels at 1:1 and scaling breaks.
- `getBoundingClientRect` works on SVG elements but `offsetWidth`/`offsetHeight` are 0 — use the former for hit-testing/layout.
- Text in SVG doesn't wrap — split lines manually with `<tspan>`.
