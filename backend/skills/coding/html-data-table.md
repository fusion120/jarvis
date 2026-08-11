---
lang: html
keywords: sortable table, filter table, data table, aria-sort, table sort, table filter, caption, thead, tbody
---

# Sortable / Filterable Data Table

A real `<table>` (caption, `scope`, `thead`) whose rows come from one JS data array. Click a header to sort asc/desc with `aria-sort`; type in the filter box to subset. Keeping render, sort, and filter in ONE function is the whole trick.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sortable table</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 52rem; margin: 2rem auto; padding: 0 1rem; }
  input { padding: .4rem; margin-bottom: 1rem; width: 14rem; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: .5rem; border-bottom: 1px solid #ddd; }
  th { cursor: pointer; user-select: none; background: #f4f4f4; }
  th:hover { background: #e8e8e8; }
  th[aria-sort="ascending"]::after { content: ' \25B2'; }
  th[aria-sort="descending"]::after { content: ' \25BC'; }
</style>
</head>
<body>
<h1>Sortable, filterable table</h1>
<label for="q">Filter:</label>
<input id="q" type="search" placeholder="name or role..." aria-label="Filter rows">
<table>
  <caption>Team members</caption>
  <thead>
    <tr><th scope="col" data-k="name">Name</th><th scope="col" data-k="role">Role</th><th scope="col" data-k="age">Age</th></tr>
  </thead>
  <tbody id="tbody"></tbody>
</table>
<script>
  const rows = [
    { name: 'Ada', role: 'Engineer', age: 36 },
    { name: 'Grace', role: 'Admiral', age: 45 },
    { name: 'Katherine', role: 'Scientist', age: 41 },
    { name: 'Margaret', role: 'Engineer', age: 33 },
  ];
  const tbody = document.getElementById('tbody');
  const q = document.getElementById('q');
  let sortKey = 'name', sortDir = 1;

  function render() {
    const f = q.value.toLowerCase();
    const list = rows
      .filter(r => (r.name + ' ' + r.role).toLowerCase().includes(f))
      .sort((a, b) => {
        const va = a[sortKey], vb = b[sortKey];
        return typeof va === 'number' ? (va - vb) * sortDir : String(va).localeCompare(String(vb)) * sortDir;
      });
    tbody.innerHTML = list.map(r => `<tr><td>${r.name}</td><td>${r.role}</td><td>${r.age}</td></tr>`).join('');
  }

  document.querySelectorAll('th').forEach(th => th.addEventListener('click', () => {
    const k = th.dataset.k;
    if (sortKey === k) sortDir *= -1;
    else { sortKey = k; sortDir = 1; }
    document.querySelectorAll('th').forEach(t => t.removeAttribute('aria-sort'));
    th.setAttribute('aria-sort', sortDir === 1 ? 'ascending' : 'descending');
    render();
  }));
  q.addEventListener('input', render);
  render();
</script>
</body>
</html>
```

Gotchas:
- `aria-sort` on the active header is the screen-reader signal; without it SR users hear nothing while sighted users see arrows.
- Strings sort wrong for numbers (`'10' < '2'`) — branch on type: compare numbers with subtraction, strings with `localeCompare`.
- Use `localeCompare` for names with accents — plain `<` sorts them by UTF-16 code units, not alphabetically.
- Building rows with `innerHTML` from user data is XSS — escape `& < > " '` if rows come from a server or user input.
- Keep `caption` and `scope="col"` on the header row — a naked `<table>` is almost unusable to assistive tech.
- Re-rendering every row on each keystroke is fine for hundreds; for thousands use a `DocumentFragment` or virtualize.
