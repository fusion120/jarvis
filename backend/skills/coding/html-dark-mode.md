---
lang: html
keywords: dark mode, prefers-color-scheme, css variables, theme toggle, color-scheme, localStorage, fouc, dark theme
---

# Dark Mode Toggle (CSS Variables)

One class on `<html>` flips every color because the palette lives in CSS variables. The user's choice persists in `localStorage`, the OS preference is the default, and the theme is applied before first paint to avoid a light flash.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dark mode</title>
<script>
  // Apply stored preference before paint to avoid a light flash (FOUC).
  const saved = localStorage.getItem('theme');
  if (saved === 'dark' || (!saved && matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.classList.add('dark');
  }
</script>
<style>
  :root { color-scheme: light dark; --bg: #fff; --fg: #111; --accent: #07c; }
  :root.dark { --bg: #111; --fg: #eee; --accent: #59f; }
  body { margin: 0; font: 16px/1.6 system-ui; background: var(--bg); color: var(--fg);
         min-height: 100vh; transition: background .3s, color .3s; }
  main { max-width: 40rem; margin: auto; padding: 2rem 1rem; }
  .toggle { position: fixed; top: 1rem; right: 1rem; padding: .5rem 1rem; border-radius: 999px; border: 1px solid var(--fg); background: var(--bg); color: var(--fg); cursor: pointer; }
  code { background: var(--accent); color: #fff; padding: .1em .4em; border-radius: 4px; }
</style>
</head>
<body>
<button class="toggle" id="t" aria-pressed="false">Dark mode</button>
<main>
  <h1>Dark mode with CSS variables</h1>
  <p>The page theme is driven by a single class on <code>&lt;html&gt;</code>; every color is a CSS variable so nothing else changes.</p>
  <p>Your choice is saved to <code>localStorage</code> and applied before first paint.</p>
</main>
<script>
  const btn = document.getElementById('t');
  const apply = () => {
    const dark = document.documentElement.classList.toggle('dark');
    btn.textContent = dark ? 'Light mode' : 'Dark mode';
    btn.setAttribute('aria-pressed', String(dark));
    localStorage.setItem('theme', dark ? 'dark' : 'light');
  };
  btn.addEventListener('click', apply);
  apply(); // sync label at load
</script>
</body>
</html>
```

Gotchas:
- Apply the theme class in a `<script>` in `<head>` BEFORE the stylesheet paints, or users see a flash of the wrong theme (FOUC).
- Only fall back to `prefers-color-scheme` when nothing is saved — once the user chooses, their choice wins; don't override it with the OS preference.
- Every color must come from a CSS variable; one hard-coded `#fff` in a component fights the theme forever.
- Set `color-scheme: dark` alongside your dark palette so scrollbars, form controls and `canvas` defaults also go dark.
- Keep `aria-pressed` and the button label in sync in the same function, or assistive tech reports stale state.
- `transition` on background/color makes switching smooth but can feel laggy under `prefers-reduced-motion` — gate the transition.
