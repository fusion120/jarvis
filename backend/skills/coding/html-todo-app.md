---
lang: html
keywords: todo app, localStorage, crud, persist, json parse, escape html, filter todos, checkboxes, localstorage app
---

# localStorage Todo App

The classic persistence demo done right: one state array, JSON to `localStorage` on every change, and a single `render()` that draws list + filters. Shows CRUD, filtering, and the escape-XSS habit.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Todo app</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 30rem; margin: 2rem auto; padding: 0 1rem; }
  form { display: flex; gap: .5rem; }
  input[type=text] { flex: 1; padding: .5rem; font: inherit; }
  button { padding: .5rem .75rem; cursor: pointer; }
  ul { list-style: none; padding: 0; }
  li { display: flex; gap: .5rem; align-items: center; padding: .4rem 0; border-bottom: 1px solid #eee; }
  li.done span { text-decoration: line-through; color: #888; }
  .filters { display: flex; gap: .5rem; margin: .5rem 0; }
  .filters button.active { outline: 2px solid #07c; }
</style>
</head>
<body>
<h1>Todo</h1>
<form id="add"><input id="txt" type="text" placeholder="What needs doing?" autocomplete="off"><button>Add</button></form>
<div class="filters" role="group" aria-label="Filter todos">
  <button data-f="all" class="active">All</button>
  <button data-f="active">Active</button>
  <button data-f="done">Done</button>
</div>
<ul id="list"></ul>
<script>
  const KEY = 'todos';
  let todos = JSON.parse(localStorage.getItem(KEY) || '[]');
  let filter = 'all';
  const list = document.getElementById('list');
  const txt = document.getElementById('txt');
  const escapeHtml = s => s.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  function save() { localStorage.setItem(KEY, JSON.stringify(todos)); }
  function render() {
    const shown = todos.filter(t => filter === 'all' ? true : filter === 'active' ? !t.done : t.done);
    list.innerHTML = shown.map(t => `
      <li class="${t.done ? 'done' : ''}">
        <input type="checkbox" data-id="${t.id}" ${t.done ? 'checked' : ''} aria-label="Toggle ${escapeHtml(t.text)}">
        <span>${escapeHtml(t.text)}</span>
        <button data-del="${t.id}" aria-label="Delete">×</button>
      </li>`).join('');
  }
  document.getElementById('add').addEventListener('submit', e => {
    e.preventDefault();
    const text = txt.value.trim();
    if (!text) return;
    todos.push({ id: Date.now(), text, done: false });
    txt.value = ''; save(); render();
  });
  list.addEventListener('click', e => {
    const del = e.target.closest('[data-del]');
    const cb = e.target.closest('input[type=checkbox]');
    if (del) todos = todos.filter(t => t.id !== Number(del.dataset.del));
    if (cb) { todos.find(t => t.id === Number(cb.dataset.id)).done = cb.checked; }
    save(); render();
  });
  document.querySelectorAll('.filters button').forEach(b => b.addEventListener('click', () => {
    filter = b.dataset.f;
    document.querySelectorAll('.filters button').forEach(x => x.classList.toggle('active', x === b));
    render();
  }));
  render();
</script>
</body>
</html>
```

Gotchas:
- `JSON.parse(localStorage.getItem(...))` throws on corrupted data and bricks the app — wrap in try/catch and fall back to `[]`.
- User text injected via `innerHTML` is XSS — the `escapeHtml` helper is mandatory when rendering todo text.
- `localStorage` is synchronous and blocks the main thread; fine for todos, wrong for big payloads (use IndexedDB).
- Storage is per-origin and quota-capped (~5MB) — persist the whole state once per change, not per keystroke.
- `Date.now()` ids collide if two items are added in the same millisecond — use `crypto.randomUUID()` or a counter.
- Persist and read the SAME key; a typo in the key string silently starts everyone at zero.
