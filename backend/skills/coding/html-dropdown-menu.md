---
lang: html
keywords: dropdown menu, menu button, aria-haspopup, aria-expanded, menuitem, arrow keys, escape, close on outside click
---

# Dropdown Menu (Click + Keyboard)

A menu button that opens a `role="menu"`, navigable with Arrow keys, closed by Escape or an outside click. This is the ARIA menu pattern — trigger has `aria-haspopup`/`aria-expanded`, items are `role="menuitem"`.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dropdown menu</title>
<style>
  body { font: 16px/1.6 system-ui; margin: 2rem; }
  .menu { position: relative; display: inline-block; }
  button { padding: .5rem 1rem; cursor: pointer; }
  [role="menu"] {
    position: absolute; top: 100%; left: 0; min-width: 12rem; margin: .25rem 0 0;
    background: #fff; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 4px 12px rgb(0 0 0 / .12);
    list-style: none; padding: .25rem; display: none;
  }
  [role="menu"][data-open="true"] { display: block; }
  [role="menuitem"] { display: block; width: 100%; text-align: left; padding: .5rem .75rem; border: 0; background: none; border-radius: 6px; }
  [role="menuitem"]:hover, [role="menuitem"]:focus { background: #f0f4ff; }
</style>
</head>
<body>
<div class="menu">
  <button id="btn" aria-haspopup="menu" aria-expanded="false" aria-controls="m">Actions &#9662;</button>
  <ul role="menu" id="m" data-open="false" aria-labelledby="btn">
    <li role="none"><button role="menuitem" data-act="Edit">Edit</button></li>
    <li role="none"><button role="menuitem" data-act="Duplicate">Duplicate</button></li>
    <li role="none"><button role="menuitem" data-act="Delete">Delete</button></li>
  </ul>
</div>
<script>
  const btn = document.getElementById('btn');
  const menu = document.getElementById('m');
  const items = [...menu.querySelectorAll('[role=menuitem]')];

  function setOpen(open, focusIndex = 0) {
    menu.dataset.open = String(open);
    btn.setAttribute('aria-expanded', String(open));
    if (open) items[focusIndex].focus();
  }
  btn.addEventListener('click', () => setOpen(menu.dataset.open !== 'true'));
  btn.addEventListener('keydown', e => {
    if (['ArrowDown', 'Enter', ' '].includes(e.key)) { e.preventDefault(); setOpen(true); }
  });
  menu.addEventListener('keydown', e => {
    if (e.key === 'Escape') { e.preventDefault(); setOpen(false); btn.focus(); }
    const dir = { ArrowDown: 1, ArrowUp: -1 }[e.key];
    if (dir) {
      e.preventDefault();
      const i = items.indexOf(document.activeElement);
      setOpen(true, (i + dir + items.length) % items.length);
    }
  });
  document.addEventListener('click', e => {
    if (!e.target.closest('.menu')) setOpen(false);
  });
  items.forEach(item => item.addEventListener('click', () => {
    alert('Chose ' + item.dataset.act);
    setOpen(false);
  }));
</script>
</body>
</html>
```

Gotchas:
- `aria-haspopup="menu"` + `aria-expanded` on the trigger, `role="menu"` on the list, `role="menuitem"` on items, and `role="none"` on the wrapper `<li>`s.
- Keyboard contract: ArrowDown/Up moves (wrapping), Home/End jumps to ends, Escape closes and returns focus to the trigger, Enter/Space activates.
- Outside-click close must ignore clicks inside the menu — check `closest('.menu')`, not `!menu.contains(e.target)`.
- Escape must restore focus to the trigger or keyboard users are stranded after closing.
- Hide with `display: none` (not `visibility`) so the menu leaves the a11y tree when closed.
- An `overflow: hidden` or `overflow: auto` ancestor clips the absolutely-positioned menu — check your layout containers.
