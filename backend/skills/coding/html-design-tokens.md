---
lang: html
keywords: design tokens, css variables, custom properties, design system, spacing scale, color tokens, scoped override, theming
---

# Design Tokens with CSS Variables

Define your spacing, color, radius, and type scale once as CSS custom properties, then build components purely from tokens. Changing a value in `:root` re-themes the whole app — no component edits.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Design tokens</title>
<style>
  :root {
    /* spacing scale */
    --space-1: .25rem; --space-2: .5rem; --space-3: 1rem; --space-4: 2rem;
    /* color tokens */
    --color-primary: #07c; --color-text: #222; --color-muted: #666; --color-bg: #fafafa;
    --color-border: #e0e0e0;
    /* radii + shadows */
    --radius: 8px; --shadow: 0 2px 8px rgb(0 0 0 / .08);
    /* type scale */
    --text-sm: .875rem; --text-md: 1rem; --text-lg: 1.5rem;
  }
  body { margin: 0; font: 16px/1.6 system-ui; background: var(--color-bg); color: var(--color-text); }
  main { max-width: 36rem; margin: auto; padding: var(--space-4); }
  .card { background: #fff; border: 1px solid var(--color-border); border-radius: var(--radius);
          box-shadow: var(--shadow); padding: var(--space-3); margin-bottom: var(--space-3); }
  .btn { background: var(--color-primary); color: #fff; border: 0; border-radius: var(--radius);
         padding: var(--space-2) var(--space-3); cursor: pointer; font-size: var(--text-md); }
  .muted { color: var(--color-muted); font-size: var(--text-sm); }
  /* Override tokens in a scoped subtree */
  .danger-zone { --color-primary: #c00; --radius: 4px; }
</style>
</head>
<body>
<main>
  <h1>Design tokens</h1>
  <div class="card">
    <h2>Cards use tokens</h2>
    <p class="muted">Spacing, color, radius and type all come from CSS variables.</p>
    <button class="btn">Primary</button>
  </div>
  <div class="card danger-zone">
    <h2>Scoped override</h2>
    <p class="muted">Redefining <code>--color-primary</code> on a container cascades to its children only.</p>
    <button class="btn">Danger</button>
  </div>
</main>
</body>
</html>
```

Gotchas:
- Tokens only cascade — override them on a scope, never `!important` them inside components or theming breaks.
- Name tokens by role (`--color-primary`), not by value (`--blue`); when the value changes, no usage needs editing.
- Custom properties don't transition smoothly (they flip at 50%) unless registered with `@property` — animating a token change needs that.
- Keep the whole token set in ONE `:root` block; scattered definitions get overridden in unpredictable order.
- Put units in the token values (`--space-3: 1rem`); `calc(var(--space-3) * 2)` only works with unitful values, and use unitless line-heights.
- `var(--x, fallback)` gives a default for tokens that may not exist yet — use it when consuming third-party-ish CSS.
