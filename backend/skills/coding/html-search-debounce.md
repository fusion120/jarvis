---
lang: html
keywords: search as you type, debounce, autocomplete, typeahead, setTimeout, stale response, encodeURIComponent, live search
---

# Search-as-You-Type with Debounce

Filtering a list while typing is two problems: debounce the keystrokes (250ms), AND guard against stale responses — a slow request resolving after a newer one. Both are shown here against an in-page dataset; the `search()` is where a real `fetch` would go.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Search as you type</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 36rem; margin: 2rem auto; padding: 0 1rem; }
  input { width: 100%; padding: .5rem; font: inherit; }
  ul { list-style: none; padding: 0; }
  li { padding: .5rem; border-bottom: 1px solid #eee; }
  #status { color: #666; font-size: .875rem; min-height: 1.2em; }
</style>
</head>
<body>
<h1>Search-as-you-type</h1>
<label for="q">Search cities</label>
<input id="q" type="search" autocomplete="off" placeholder="e.g. san">
<p id="status"></p>
<ul id="results"></ul>
<script>
  const CITIES = ['San Francisco', 'San Jose', 'Santa Cruz', 'Los Angeles', 'London', 'Paris', 'Berlin', 'Austin', 'Seattle', 'New York', 'Boston', 'Chicago'];
  const q = document.getElementById('q');
  const results = document.getElementById('results');
  const status = document.getElementById('status');
  let timer, seq = 0;

  async function search(term) {
    // Simulated latency; replace with fetch('/api/search?q=' + encodeURIComponent(term)).
    await new Promise(r => setTimeout(r, 120 + Math.random() * 180));
    return CITIES.filter(c => c.toLowerCase().includes(term.toLowerCase()));
  }

  q.addEventListener('input', () => {
    const term = q.value.trim();
    status.textContent = term ? 'Searching...' : '';
    clearTimeout(timer);
    if (!term) { results.innerHTML = ''; return; }
    timer = setTimeout(async () => {
      const my = ++seq;
      const hits = await search(term);
      if (my !== seq) return; // a newer keystroke won — drop this result
      status.textContent = `${hits.length} result${hits.length === 1 ? '' : 's'}`;
      results.innerHTML = hits.map(c => `<li>${c}</li>`).join('');
    }, 250);
  });
</script>
</body>
</html>
```

Gotchas:
- Debouncing keystrokes is NOT enough — out-of-order responses need the `seq` counter guard, or a slow "san" result can overwrite a newer "san fr" one.
- Always `clearTimeout` before scheduling a new one; skipping it queues duplicate searches.
- Empty input should clear immediately, without the debounce delay.
- `encodeURIComponent(term)` is mandatory when interpolating into a URL — a space or `&` in the query silently changes the API call.
- 250ms is the common sweet spot; 0ms fires on every keystroke (janky), 500ms feels laggy.
- Debounce `input`/`scroll`/`resize` only — never debounce form `submit` or button clicks.
