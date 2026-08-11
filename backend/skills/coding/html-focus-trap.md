---
lang: html
keywords: focus trap, focus management, modal accessibility, aria-modal, tab cycle, focusable elements, scroll lock, return focus
---

# Focus Trap

When you hand-build an overlay (not using `<dialog>`), you must keep Tab cycling inside it, lock page scroll, and return focus to the trigger on close. This is the manual version of what native modals give you free.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Focus trap</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 30rem; margin: 2rem auto; padding: 0 1rem; }
  .overlay { position: fixed; inset: 0; background: rgb(0 0 0 / .5); display: grid; place-items: center; }
  .overlay[hidden] { display: none; }
  .modal { background: #fff; border-radius: 10px; padding: 1.5rem; max-width: 24rem; }
</style>
</head>
<body>
<h1>Focus trap</h1>
<button id="open">Open modal</button>
<div class="overlay" id="overlay" hidden>
  <div class="modal" role="dialog" aria-modal="true" aria-labelledby="t">
    <h2 id="t">Trap demo</h2>
    <p>Tab cycles inside this dialog; Shift+Tab wraps backwards; Escape closes.</p>
    <button id="a">First</button>
    <button id="b">Second</button>
    <button id="close">Close</button>
  </div>
</div>
<script>
  const overlay = document.getElementById('overlay');
  const open = document.getElementById('open');
  const FOCUSABLE = 'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])';

  function focusables() {
    return [...overlay.querySelectorAll(FOCUSABLE)]
      .filter(el => !el.disabled && el.offsetParent !== null);
  }
  open.addEventListener('click', () => {
    overlay.hidden = false;
    focusables()[0].focus();
    document.body.style.overflow = 'hidden'; // lock scroll behind
  });
  document.getElementById('close').addEventListener('click', close);
  function close() {
    overlay.hidden = true;
    document.body.style.overflow = '';
    open.focus(); // return focus to the trigger
  }
  overlay.addEventListener('keydown', e => {
    if (e.key !== 'Tab') return;
    const f = focusables();
    const first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });
</script>
</body>
</html>
```

Gotchas:
- Trapping Tab only helps keyboard users — you ALSO need `aria-modal="true"` and the background made inert (`inert` attribute or `aria-hidden` + removing tabindexes) or screen readers still reach it.
- Filter focusables: skip `disabled` and `display:none` (`el.offsetParent !== null`), and exclude `tabindex="-1"` nodes.
- Return focus to the trigger on close — forgetting it strands keyboard users at the top of the page.
- Lock page scroll with `overflow: hidden` on `body`, and UNLOCK it on close, or the page stays frozen.
- The native `<dialog>` gives trapping, inertness, and focus restore for free — build a manual trap only for non-dialog shells (popovers, drawers).
- If the modal contains elements added later, recompute the focusable list at open time, not once at load.
