---
lang: html
keywords: keyboard shortcuts, keydown, hotkeys, ctrl k, focus trap shortcuts, keyboard navigation, e.key, shift slash help
---

# Global Keyboard Shortcuts

Page-wide shortcuts handled in one `keydown` listener, with the rules that keep them safe: never hijack keys while typing, check modifiers explicitly, and avoid clobbering browser/OS shortcuts.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Keyboard shortcuts</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 30rem; margin: 2rem auto; padding: 0 1rem; }
  kbd { background: #eee; border: 1px solid #bbb; border-bottom-width: 2px; border-radius: 4px; padding: .1rem .4rem; font: inherit; }
  dialog { border: 0; border-radius: 10px; }
  dialog::backdrop { background: rgb(0 0 0 / .4); }
</style>
</head>
<body>
<h1>Shortcuts</h1>
<p>Press <kbd>?</kbd> for help, <kbd>j</kbd>/<kbd>k</kbd> to move, <kbd>Ctrl</kbd>+<kbd>K</kbd> to focus search.</p>
<button id="a">Target item 1</button> <button id="b">Target item 2</button>
<input id="search" placeholder="search...">
<dialog id="help">
  <h2>Help</h2>
  <ul><li><kbd>?</kbd> this dialog</li><li><kbd>j</kbd>/<kbd>k</kbd> next/prev button</li><li><kbd>Ctrl</kbd>+<kbd>K</kbd> focus search</li></ul>
  <button id="help-close">Close</button>
</dialog>
<script>
  const buttons = [...document.querySelectorAll('button')];
  let focusIdx = 0;
  const dialog = document.getElementById('help');

  addEventListener('keydown', e => {
    // Never hijack keys while the user is typing.
    const t = document.activeElement;
    const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) || t.isContentEditable;
    if (typing && e.key !== 'Escape') return;

    if (e.key === '/' && e.shiftKey) { e.preventDefault(); dialog.showModal(); return; }
    if (e.key === 'j' || e.key === 'k') {
      e.preventDefault();
      focusIdx = (focusIdx + (e.key === 'j' ? 1 : -1) + buttons.length) % buttons.length;
      buttons[focusIdx].focus();
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      document.getElementById('search').focus();
    }
    if (e.key === 'Escape') dialog.close();
  });
  document.getElementById('help-close').addEventListener('click', () => dialog.close());
</script>
</body>
</html>
```

Gotchas:
- The typing guard is essential: check the active element's tag / `isContentEditable` and return early, or shortcuts fire mid-sentence.
- `?` arrives as `e.key === '/' && e.shiftKey` — `e.key` is the produced character, and `e.code` is the physical key (different layouts!). Test `key`, not `code`, for characters.
- `e.key.toLowerCase()` before comparing — CapsLock makes `'K'` on some setups.
- Check `ctrlKey`/`metaKey` explicitly; on Mac, `metaKey` is Cmd, on Windows `ctrlKey` is Ctrl — handle both if you want cross-platform.
- Don't override browser/OS shortcuts (Ctrl+W, Ctrl+T, Cmd+Q) — users lose muscle memory and can't recover.
- Re-scan focusable targets each time a shortcut moves focus, or a removed button leaves focus on a stale node.
- Publish the shortcuts — a help dialog is the accessible pattern; unlisted magic keys are traps.
