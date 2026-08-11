---
lang: html
keywords: theme switcher, multiple themes, data-theme, css variables, color-scheme, select dropdown, persist theme, sepia
---

# Theme Switcher (Multiple Themes)

More than two themes (light, dark, sepia...)? Drive it with a `data-theme` attribute on `<html>` and one CSS rule per theme that overrides the same variable names. A `<select>` writes the choice to `localStorage`.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Theme switcher</title>
<script>
  // Apply before paint to prevent FOUC.
  document.documentElement.dataset.theme = localStorage.getItem('theme') || 'light';
</script>
<style>
  :root { color-scheme: light; --bg: #fff; --fg: #111; --panel: #f4f4f4; --accent: #07c; }
  [data-theme="dark"] { color-scheme: dark; --bg: #111; --fg: #eee; --panel: #1c1c1c; --accent: #59f; }
  [data-theme="sepia"] { --bg: #f7efdd; --fg: #4a3f2f; --panel: #efe4c8; --accent: #9a5b1f; }
  body { margin: 0; font: 16px/1.6 system-ui; background: var(--bg); color: var(--fg); transition: background .3s; }
  main { max-width: 36rem; margin: auto; padding: 2rem 1rem; }
  select { padding: .4rem; font: inherit; }
</style>
</head>
<body>
<main>
  <label for="theme">Theme</label>
  <select id="theme">
    <option value="light">Light</option>
    <option value="dark">Dark</option>
    <option value="sepia">Sepia</option>
  </select>
  <h1>Theme switcher</h1>
  <p>A <code>data-theme</code> attribute on <code>&lt;html&gt;</code> selects a token set. Add as many themes as you like — each is just another rule.</p>
</main>
<script>
  const sel = document.getElementById('theme');
  const root = document.documentElement;
  sel.value = root.dataset.theme;
  sel.addEventListener('change', () => {
    root.dataset.theme = sel.value;
    localStorage.setItem('theme', sel.value);
  });
</script>
</body>
</html>
```

Gotchas:
- Set `data-theme` in a head script so the correct theme paints on the first frame; a deferred script causes a flash.
- Keep each theme a single rule overriding the same variable names — never write `.dark .card {}`-style forks or you get one rule per theme per component.
- Validate the stored value: a corrupted `localStorage` string silently disables theming — fall back to 'light' with a whitelist check.
- `color-scheme` must be set per theme (or on `:root` light too) or native form controls keep the OS look that clashes with your palette.
- `<select>` is a native control: its drop-down styling follows `color-scheme`, not your CSS variables.
- If themes affect more than colors (fonts, spacing), the same `data-theme` scope still works — keep ALL themed values as variables.
