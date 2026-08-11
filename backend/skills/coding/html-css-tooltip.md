---
lang: html
keywords: tooltip, css tooltip, ::after, data-tip, aria-describedby, focus-visible, hover text, pointer-events
---

# Pure-CSS Tooltip

A tooltip built from `::after`/`::before` and the trigger's `data-tip` attribute — no JS. It appears on hover AND keyboard focus, and the same text is wired to `aria-describedby` so screen readers get the explanation too.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CSS tooltip</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 30rem; margin: 4rem auto; padding: 0 1rem; }
  .tip { position: relative; color: #07c; cursor: help; border-bottom: 1px dashed #07c; }
  .tip::after {
    content: attr(data-tip);
    position: absolute; bottom: 130%; left: 50%; transform: translateX(-50%);
    background: #222; color: #fff; padding: .4rem .6rem; border-radius: 6px;
    font-size: .8rem; white-space: nowrap; pointer-events: none;
    opacity: 0; transition: opacity .15s ease; z-index: 10;
  }
  .tip::before {
    content: ''; position: absolute; bottom: calc(130% - 5px); left: 50%; transform: translateX(-50%);
    border: 5px solid transparent; border-top-color: #222; opacity: 0; transition: opacity .15s;
  }
  .tip:hover::after, .tip:focus-visible::after,
  .tip:hover::before, .tip:focus-visible::before { opacity: 1; }
</style>
</head>
<body>
<p>Hover or focus the <span class="tip" tabindex="0" data-tip="A useful clarification" aria-describedby="tip-1">highlighted term</span> to see a pure-CSS tooltip.</p>
<p id="tip-1" hidden>A useful clarification — linked via <code>aria-describedby</code> for screen readers.</p>
</body>
</html>
```

Gotchas:
- Tooltips must show on keyboard focus too — the `:focus-visible` rule plus `tabindex="0"` (or a real button) is what makes them accessible.
- Pseudo-element `content` isn't reliably announced by all screen readers — pair it with `aria-describedby` pointing at real text.
- `overflow: hidden` ancestors clip tooltips; give them room or they get cut off at the element edge.
- Set `pointer-events: none` on the tooltip or it intercepts hover between the trigger and the bubble.
- `white-space: nowrap` overflows tiny screens — allow wrapping (`white-space: normal` + `max-width`) for long tips.
- Pure-CSS tooltips pick one side and can't flip near screen edges — a JS tooltip can; accept the limitation or use JS.
