---
lang: html
keywords: pagination, pager, page numbers, prev next, aria-current, slice, paged list, paginated content
---

# Pagination

Splitting a long list into pages: prev/next + numbered links, one `render()` that redraws both the list and the pager from a single `page` state. `aria-current="page"` marks the active page for screen readers.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pagination</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 36rem; margin: 2rem auto; padding: 0 1rem; }
  nav[aria-label="Pagination"] { display: flex; gap: .25rem; margin-top: 1rem; }
  nav a { padding: .4rem .75rem; border: 1px solid #ddd; border-radius: 6px; text-decoration: none; color: #07c; }
  nav a[aria-current="page"] { background: #07c; color: #fff; }
  nav a.disabled { opacity: .4; pointer-events: none; }
  ul { padding-left: 1.2rem; }
</style>
</head>
<body>
<h1>Pagination</h1>
<ul id="list"></ul>
<nav aria-label="Pagination" id="pager"></nav>
<script>
  const ITEMS = [...Array(47).keys()].map(i => `Item ${i + 1}`);
  const PER = 10;
  let page = 1;
  const pages = Math.ceil(ITEMS.length / PER);

  function render() {
    const list = document.getElementById('list');
    const start = (page - 1) * PER;
    list.innerHTML = ITEMS.slice(start, start + PER).map(i => `<li>${i}</li>`).join('');
    const p = document.getElementById('pager');
    const mk = (label, target, cls, sr) => {
      const a = document.createElement('a');
      a.href = '#';
      a.textContent = label;
      if (cls) a.className = cls;
      if (sr) a.setAttribute('aria-label', sr);
      if (target === page) a.setAttribute('aria-current', 'page');
      a.addEventListener('click', e => {
        e.preventDefault();
        if (target < 1 || target > pages) return; // guard edge links
        page = target; render();
      });
      return a;
    };
    p.replaceChildren(
      mk('‹', page - 1, page === 1 ? 'disabled' : '', 'Previous page'),
      ...Array.from({ length: pages }, (_, i) => mk(String(i + 1), i + 1)),
      mk('›', page + 1, page === pages ? 'disabled' : '', 'Next page'),
    );
  }
  render();
</script>
</body>
</html>
```

Gotchas:
- Window the page numbers (1 … 4 5 6 … 20) once pages grow — 500 numbered links hurt DOM and usability.
- `aria-current="page"` marks the active page; prev/next need `aria-label="Previous page"`/`"Next page"` or SR users hear bare glyphs.
- Guard edge clicks: the prev/next links can target 0 or pages+1 — ignore out-of-range targets or `slice()` misbehaves.
- Use `replaceChildren` to swap the pager; reusing stale node references from an old render leaks behavior.
- Keep list and pager in ONE render function — two update paths drift apart.
- In production, make pager items real links (`?page=2`) so deep-linking and no-JS navigation work; JS is an enhancement.
