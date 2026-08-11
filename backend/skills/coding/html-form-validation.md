---
lang: html
keywords: form validation, constraint validation, novalidate, checkValidity, reportValidity, pattern, minlength, setCustomValidity, input
---

# Form Validation with the Constraint Validation API

When a form has rules (required, format, ranges), let the browser do the validation: `pattern`, `min`/`max`, `minlength` plus `checkValidity()`/`reportValidity()` give native, localized error messages you can override.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Form validation</title>
<style>
  body { font: 16px/1.5 system-ui; max-width: 30rem; margin: 2rem auto; padding: 0 1rem; }
  label { display: block; margin: 1rem 0 .25rem; }
  input { width: 100%; padding: .5rem; border: 1px solid #666; border-radius: 4px; font: inherit; }
  input:user-invalid { border-color: #b00; }
  input:user-valid { border-color: #0a0; }
  .msg { color: #b00; font-size: .875rem; margin: .25rem 0 0; min-height: 1em; }
  button { margin-top: 1rem; padding: .5rem 1rem; }
</style>
</head>
<body>
<form id="reg" novalidate>
  <label for="user">Username (4-12 letters)</label>
  <input id="user" name="user" required pattern="[A-Za-z]{4,12}">
  <p class="msg" id="user-msg"></p>

  <label for="age">Age (13-120)</label>
  <input id="age" name="age" type="number" min="13" max="120" required>
  <p class="msg" id="age-msg"></p>

  <label for="pw">Password (min 8 chars)</label>
  <input id="pw" name="pw" type="password" required minlength="8">
  <p class="msg" id="pw-msg"></p>

  <button type="submit">Register</button>
</form>
<script>
  const form = document.getElementById('reg');
  form.addEventListener('submit', e => {
    e.preventDefault();
    if (form.checkValidity()) { alert('Valid!'); return; }
    for (const el of form.elements) {
      const msg = document.getElementById(el.id + '-msg');
      if (msg) msg.textContent = el.validationMessage || '';
    }
    form.reportValidity(); // focuses the first invalid control + native bubble
  });
</script>
</body>
</html>
```

Gotchas:
- `:invalid` styles apply before the user types; use `:user-invalid`/`:user-valid` to only style after interaction.
- `novalidate` on the form suppresses the native bubble so your custom messages show — without it the bubble appears and your text may never be seen.
- `checkValidity()` returns a boolean but shows nothing; `reportValidity()` shows the native bubbles and focuses the first invalid control.
- `pattern` is implicitly anchored: the whole value must match, so no `^`/`$` needed.
- `el.validationMessage` is localized by the browser; override with `setCustomValidity('msg')` and pass `''` to clear it.
- Browsers can't validate `pattern` on `contenteditable` or `<textarea>` without a pattern attr — stick to inputs or write your own checks.
