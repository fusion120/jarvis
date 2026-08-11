---
lang: html
keywords: toast notification, toast, notifications, aria-live, polite, auto dismiss, animationend, notification container
---

# Toast Notifications

Transient status messages: a fixed container bottom-right, `toast()` creates one, auto-dismisses it, and animates it out before removing it from the DOM. The container is `aria-live="polite"` so screen readers announce arrivals without stealing focus.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Toast notifications</title>
<style>
  body { font: 16px/1.6 system-ui; margin: 0; }
  button { margin: 1rem; padding: .5rem 1rem; cursor: pointer; }
  #toasts { position: fixed; bottom: 1rem; right: 1rem; display: flex; flex-direction: column; gap: .5rem; }
  .toast { background: #222; color: #fff; padding: .75rem 1rem; border-radius: 8px;
           display: flex; gap: 1rem; align-items: center; box-shadow: 0 4px 12px rgb(0 0 0 / .2);
           animation: in .2s ease-out; }
  .toast.out { animation: out .2s ease-in forwards; }
  .toast button { margin: 0; padding: 0 .25rem; background: none; border: 0; color: #999; font-size: 1.1rem; }
  .toast[data-type="error"] { background: #a33; }
  @keyframes in { from { transform: translateY(8px); opacity: 0; } }
  @keyframes out { to { transform: translateY(8px); opacity: 0; } }
</style>
</head>
<body>
<button id="ok">Toast: saved</button>
<button id="err">Toast: error</button>
<div id="toasts" aria-live="polite"></div>
<script>
  const box = document.getElementById('toasts');
  function toast(text, type = 'info', ms = 3000) {
    const el = document.createElement('div');
    el.className = 'toast';
    el.dataset.type = type;
    el.textContent = text;
    const close = document.createElement('button');
    close.setAttribute('aria-label', 'Dismiss');
    close.textContent = '×';
    close.addEventListener('click', dismiss);
    el.append(close);
    box.append(el);
    const t = setTimeout(dismiss, ms);
    function dismiss() {
      clearTimeout(t);
      close.removeEventListener('click', dismiss);
      el.classList.add('out');
      el.addEventListener('animationend', () => el.remove(), { once: true });
    }
  }
  document.getElementById('ok').addEventListener('click', () => toast('Changes saved'));
  document.getElementById('err').addEventListener('click', () => toast('Sync failed — retrying', 'error', 5000));
</script>
</body>
</html>
```

Gotchas:
- The `aria-live` container must exist before any toast is added and sit outside other fixed elements, or the announcement is swallowed.
- Removing a toast while its exit animation is still running causes a visual pop — add `.out`, then `remove()` on `animationend`.
- Guard double-dismiss: `clearTimeout(t)` plus removing the listener keeps the timeout and the close button from double-removing.
- Use `aria-live="polite"` for most messages; `assertive` only for errors that demand immediate attention.
- Cap the stack (max-height + scroll, or drop the oldest) — 12 overlapping toasts are useless to everyone.
- Make the message self-contained: "Saved" is enough, "Operation #1234 failed" with no context is not.
