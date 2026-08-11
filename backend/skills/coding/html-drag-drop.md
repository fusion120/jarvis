---
lang: html
keywords: drag and drop, html5 dragdrop, draggable, dragover, dataTransfer, drop zone, kanban, dragstart drop
---

# HTML5 Drag and Drop

Move cards between columns with the native DnD API: `draggable="true"`, `dragstart` stores the item, `dragover` must `preventDefault()`, and `drop` re-parents it. This is the core of every kanban board.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Drag and drop</title>
<style>
  body { font: 16px/1.6 system-ui; margin: 2rem; }
  .cols { display: flex; gap: 1rem; }
  .col { flex: 1; min-height: 12rem; border: 2px dashed #bbb; border-radius: 8px; padding: .5rem; }
  .col.dragover { border-color: #07c; background: #f0f7ff; }
  .card { background: #fff; border: 1px solid #ddd; border-radius: 6px; padding: .5rem .75rem; margin-bottom: .5rem; cursor: grab; }
  .card.dragging { opacity: .4; }
  h2 { margin: 0 0 .5rem; font-size: 1rem; }
</style>
</head>
<body>
<h1>Drag cards between columns</h1>
<div class="cols">
  <div class="col" data-col="todo"><h2>To do</h2><div class="card" draggable="true">Write docs</div><div class="card" draggable="true">Review PR</div></div>
  <div class="col" data-col="done"><h2>Done</h2><div class="card" draggable="true">Ship v1</div></div>
</div>
<script>
  let dragged;
  document.addEventListener('dragstart', e => {
    if (!e.target.classList.contains('card')) return;
    dragged = e.target;
    dragged.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', e.target.textContent); // Firefox requires setData
  });
  document.addEventListener('dragend', e => {
    e.target.classList.remove('dragging');
    document.querySelectorAll('.col').forEach(c => c.classList.remove('dragover'));
  });
  document.querySelectorAll('.col').forEach(col => {
    col.addEventListener('dragover', e => {
      e.preventDefault();               // must allow drop
      e.dataTransfer.dropEffect = 'move';
      col.classList.add('dragover');
    });
    col.addEventListener('dragleave', () => col.classList.remove('dragover'));
    col.addEventListener('drop', e => {
      e.preventDefault();
      col.classList.remove('dragover');
      if (dragged) col.append(dragged);
    });
  });
</script>
</body>
</html>
```

Gotchas:
- `dragover` MUST call `preventDefault()` or `drop` never fires — the single most common DnD failure.
- Firefox will not even start a drag unless `dataTransfer.setData(...)` is called in `dragstart`.
- Keep the source element in place during the drag (style `.dragging` with opacity) and `append` on drop — moving it early breaks the drag image.
- Check `e.dataTransfer.files` vs `getData('text/plain')` to distinguish external file drops from internal card moves.
- HTML5 DnD is unusable on touch — provide a tap-to-move alternative or implement pointer-event dragging instead.
- Dragging text out of an `<input>` is native text-drag, not element-drag — make sure `dragstart` filters `e.target` or buttons/inputs behave oddly.
