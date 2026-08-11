---
lang: html
keywords: modal, dialog, showModal, native dialog, backdrop, focus trap, aria-modal, close on backdrop click, returnValue
---

# Native `<dialog>` Modal

When you need a true modal — focus trapped, background inert, Escape to close — the native `<dialog>` element gives it all for free. Reach for this instead of hand-rolling overlays.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Native dialog modal</title>
<style>
  dialog { border: 0; border-radius: 10px; padding: 1.5rem; max-width: 24rem; }
  dialog::backdrop { background: rgb(0 0 0 / .5); }
  dialog[open] { animation: pop .2s ease-out; }
  @keyframes pop { from { transform: scale(.95); opacity: 0; } }
  button { cursor: pointer; padding: .5rem 1rem; }
</style>
</head>
<body>
<button id="open">Open modal</button>
<dialog id="dlg" aria-labelledby="t">
  <h2 id="t">Delete item?</h2>
  <p>This permanently removes the item and cannot be undone.</p>
  <button id="cancel">Cancel</button>
  <button id="ok">Delete</button>
</dialog>
<script>
  const dlg = document.getElementById('dlg');
  document.getElementById('open').addEventListener('click', () => dlg.showModal());
  document.getElementById('cancel').addEventListener('click', () => dlg.close('cancel'));
  document.getElementById('ok').addEventListener('click', () => dlg.close('confirm'));
  // Close when clicking the backdrop (Escape is built in for showModal).
  dlg.addEventListener('click', e => {
    const r = dlg.getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) dlg.close();
  });
  dlg.addEventListener('close', () => alert('Result: ' + dlg.returnValue));
</script>
</body>
</html>
```

Gotchas:
- Use `showModal()` not `show()` — the first gives true modality (inert background, trapped focus, Escape), the second renders inline like a card.
- `::backdrop` only appears for modal dialogs, so a `show()` dialog has no overlay to style.
- Backdrop clicks never dispatch to the dialog — you must hit-test `clientX/Y` against `getBoundingClientRect()`; closing on any `click` would close when clicking inside too.
- Native modal restores focus to the opener on close automatically — don't add your own focus code or you'll fight the browser.
- The `cancel` event fires on Escape; `preventDefault()` on it keeps the dialog open (useful for confirm-on-close UX).
- Browser support: Safari ≥ 15.4; older Safari needs a polyfill.
