---
lang: html
keywords: web component, custom element, customElements.define, observedAttributes, attributeChangedCallback, connectedCallback, reusable component
---

# Web Component / Custom Element

Wrap a piece of UI in its own element: `customElements.define` a class that renders itself and reacts to attribute changes. This `<rating-stars>` shows the lifecycle and attribute reactivity pattern.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Web Component</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 34rem; margin: 2rem auto; padding: 0 1rem; }
  rating-stars { font-size: 2rem; }
</style>
</head>
<body>
<h1>Custom element: &lt;rating-stars&gt;</h1>
<p>Read-only star rating driven by a <code>value</code> attribute (0-5).</p>
<rating-stars value="4" label="Rated 4 out of 5"></rating-stars>
<rating-stars value="5"></rating-stars>
<p>Change the value and the stars update, no page reload needed:</p>
<button id="dec" type="button">&minus;</button> <button id="inc" type="button">+</button>

<script>
  class RatingStars extends HTMLElement {
    static observedAttributes = ['value', 'label'];

    connectedCallback() {
      this.render();
    }

    attributeChangedCallback(name, oldV, newV) {
      if (oldV !== newV) this.render();
    }

    render() {
      const value = Math.max(0, Math.min(5, Number(this.getAttribute('value')) || 0));
      const label = this.getAttribute('label') || `Rated ${value} out of 5`;
      const stars = '★'.repeat(value) + '☆'.repeat(5 - value);
      this.innerHTML = `<span role="img" aria-label="${label}" style="color:#f90">${stars}</span>`;
    }
  }
  customElements.define('rating-stars', RatingStars);

  // Demo: mutate the attribute, the element reacts.
  const el = document.querySelector('rating-stars');
  const set = v => el.setAttribute('value', Math.max(0, Math.min(5, v)));
  document.getElementById('dec').addEventListener('click', () => set((Number(el.getAttribute('value')) || 0) - 1));
  document.getElementById('inc').addEventListener('click', () => set((Number(el.getAttribute('value')) || 0) + 1));
</script>
</body>
</html>
```

Gotchas:
- Custom element names MUST contain a hyphen (`rating-stars`) — defining a single reserved word throws.
- Without `static observedAttributes`, `attributeChangedCallback` never fires — attribute reactivity is opt-in.
- `attributeChangedCallback` can run BEFORE `connectedCallback` when attributes are pre-set — render defensively or track a mounted flag.
- `innerHTML` from an attribute is XSS if the attribute holds user data — escape `label` before interpolating.
- `customElements.define` throws if the name is already defined — guard with `customElements.get(name)` or try/catch.
- If the script is in `<head>`, elements upgrade as the parser reaches them; a script at the end of `<body>` is simplest for correctness.
