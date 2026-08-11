---
lang: html
keywords: shadow dom, attachShadow, ::slotted, :host, slot, encapsulation, event retargeting, composedPath, shadow root
---

# Shadow DOM Encapsulation

Give a component its own scoped DOM and CSS with `attachShadow`. Page styles can't leak in, shadow styles can't leak out, and `::slotted` styles light-DOM children. Events inside the shadow retarget to the host.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Shadow DOM</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 34rem; margin: 2rem auto; padding: 0 1rem; }
</style>
</head>
<body>
<h1>Shadow DOM encapsulation</h1>
<my-badge color="green">Shipped</my-badge>
<my-badge>Pending</my-badge>
<button id="theme">Flip page theme</button>
<p>Each <code>&lt;my-badge&gt;</code> owns a shadow root: page styles can't leak in, shadow styles can't leak out. <code>::slotted</code> styles the light-DOM children inside the shadow tree.</p>

<script>
  class MyBadge extends HTMLElement {
    connectedCallback() {
      const root = this.attachShadow({ mode: 'open' });
      const color = this.getAttribute('color') || '#555';
      root.innerHTML = `
        <style>
          .badge {
            display: inline-block; padding: .25rem .75rem; border-radius: 999px;
            background: ${color}; color: #fff; font-size: .875rem;
          }
        </style>
        <span class="badge"><slot></slot></span>`;
    }
  }
  customElements.define('my-badge', MyBadge);

  // Events from the shadow tree retarget to the host — listen on the host.
  document.querySelector('my-badge').addEventListener('click', () =>
    console.log('event retargeted to the host'));
  document.getElementById('theme').addEventListener('click', () =>
    document.body.style.filter = document.body.style.filter ? '' : 'invert(1)');
</script>
</body>
</html>
```

Gotchas:
- Shadow DOM scopes styles, but INHERITED properties (color, font) still flow in from the page — "encapsulated" does not mean "inheritance-free".
- `::slotted()` only matches the direct children assigned to a slot and can't reach deeper descendants.
- `attachShadow` throws if the element already has one — check `this.shadowRoot` first or use a flag.
- Events inside the shadow tree retarget to the host in the composed path — outside, `e.target` is the host; use `e.composedPath()` to find the real origin.
- A per-instance `<style>` (as here) duplicates CSS per element — for many instances, share one `<style>` via a template or use constructable stylesheets.
- `mode: 'closed'` hides internals from page JS too, including your own debugging — use `open` unless you're writing a library that must hide implementation.
