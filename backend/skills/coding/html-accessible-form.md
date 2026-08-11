---
lang: html
keywords: accessible form, aria, labels, focus, fieldset, legend, aria-describedby, autocomplete, error messages, screen reader
---

# Accessible Form (ARIA + Focus)

Use this pattern for any form where correctness for keyboard and screen-reader users matters — signup, checkout, settings. The markup does the heavy lifting: every field has a `<label>`, hints and errors are linked with `aria-describedby`, and errors are announced via `aria-live`.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Accessible form</title>
<style>
  body { font: 16px/1.5 system-ui; max-width: 32rem; margin: 2rem auto; padding: 0 1rem; }
  label { display: block; margin: 1rem 0 .25rem; font-weight: 600; }
  input, select { width: 100%; padding: .5rem; border: 1px solid #666; border-radius: 4px; font: inherit; }
  input:focus { outline: 3px solid #07c; outline-offset: 1px; }
  .hint, .error { font-size: .875rem; margin: .25rem 0 0; }
  .hint { color: #555; }
  .error { color: #b00; min-height: 1em; }
  fieldset { border: 1px solid #ccc; border-radius: 6px; margin-top: 1rem; }
  [aria-invalid="true"] { border-color: #b00; }
</style>
</head>
<body>
<form id="signup">
  <label for="name">Full name</label>
  <input id="name" name="name" autocomplete="name" required aria-describedby="name-hint name-err">
  <p class="hint" id="name-hint">As shown on your ID.</p>
  <p class="error" id="name-err" aria-live="polite"></p>

  <label for="email">Email</label>
  <input id="email" name="email" type="email" autocomplete="email" required aria-describedby="email-err">
  <p class="error" id="email-err" aria-live="polite"></p>

  <fieldset>
    <legend>How did you hear about us?</legend>
    <label><input type="radio" name="source" value="search" required> Search engine</label>
    <label><input type="radio" name="source" value="friend"> Friend</label>
  </fieldset>

  <button type="submit" style="margin-top:1rem">Submit</button>
  <p id="ok" aria-live="polite"></p>
</form>
<script>
  const form = document.getElementById('signup');
  const fields = ['name', 'email'].map(id => document.getElementById(id));
  form.addEventListener('submit', e => {
    e.preventDefault();
    let ok = true;
    for (const field of fields) {
      const err = document.getElementById(field.id + '-err');
      const bad = field.value.trim() === '';
      err.textContent = bad ? 'This field is required.' : '';
      field.setAttribute('aria-invalid', bad ? 'true' : 'false');
      if (bad) ok = false;
    }
    document.getElementById('ok').textContent = ok ? 'Submitted!' : 'Please fix the highlighted fields.';
  });
  fields.forEach(field => field.addEventListener('input', () => {
    document.getElementById(field.id + '-err').textContent = '';
    field.removeAttribute('aria-invalid');
  }));
</script>
</body>
</html>
```

Gotchas:
- Every input needs a `<label for>` (or wrapping label); placeholder alone is not a label and vanishes on focus.
- Link error text to the field with `aria-describedby` and make the region `aria-live="polite"` so the error is announced as it appears.
- Group radios/checkboxes in a `<fieldset>` with a `<legend>` — that is the accessible group name.
- Set `aria-invalid="true"` AND a border color — SR users get the state, sighted users get the visual.
- Never use implicit globals like `name` to reference inputs — it collides with `window.name`; look up by id.
- Don't remove focus styles: a custom outline (`:focus { outline: 3px solid }`) is required for keyboard users.
