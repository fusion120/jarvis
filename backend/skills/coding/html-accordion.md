---
lang: html
keywords: accordion, details summary, disclosure, faq, exclusive accordion, toggle event, expandable
---

# `<details>`/`<summary>` Accordion

For FAQ lists and collapsible sections, `<details>`/`<summary>` gives a disclosure widget with zero JavaScript — the browser handles open/close, Enter/Space keys, and focus. Reach for it before building any custom collapser.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Accordion</title>
<style>
  body { font: 16px/1.5 system-ui; max-width: 40rem; margin: 2rem auto; padding: 0 1rem; }
  details { border: 1px solid #ddd; border-radius: 8px; margin-bottom: .5rem; overflow: hidden; }
  summary { cursor: pointer; padding: .75rem 1rem; font-weight: 600; list-style: none; }
  summary::-webkit-details-marker { display: none; }
  summary::after { content: '+'; float: right; font-weight: 400; }
  details[open] summary::after { content: '\2212'; }
  .body { padding: 0 1rem 1rem; color: #333; }
  details[open] .body { animation: fade .25s ease-out; }
  @keyframes fade { from { opacity: 0; transform: translateY(-4px); } }
</style>
</head>
<body>
<h1>FAQ</h1>
<details name="faq" open>
  <summary>Why use details/summary?</summary>
  <div class="body">Zero-JS disclosure widget — the browser handles open/close, keyboard (Enter/Space), and focus for you.</div>
</details>
<details name="faq">
  <summary>Can only one stay open?</summary>
  <div class="body">Yes: give every <code>details</code> the same <code>name</code> attribute and the browser enforces exclusive accordions natively.</div>
</details>
<details name="faq">
  <summary>Any styling gotchas?</summary>
  <div class="body">The disclosure triangle is a UA <code>::marker</code>; hide it with <code>list-style: none</code> plus the webkit marker rule.</div>
</details>
</body>
</html>
```

Gotchas:
- A shared `name` attribute gives exclusive accordions natively (Chrome 120+); in older browsers all sections just stay open — don't rely on exclusivity alone.
- The disclosure triangle is a `::marker` — kill it with `list-style: none` and `summary::-webkit-details-marker { display:none }`, then use `summary::after` for your own indicator.
- Listen for the `toggle` event and read `details.open` rather than assuming `click` means closed.
- You can't animate `details` content with `transition` — the reveal is a discrete swap; wrap content in a `div` and keyframe that instead.
- Only phrasing content is valid inside `summary` — interactive elements like `<button>` there break keyboard handling.
- Closed `details` content stays in the DOM: links inside are still tabbable. Move focusable content out or it's reachable while invisible.
