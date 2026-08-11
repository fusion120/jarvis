---
lang: javascript
keywords: javascript, node, js, async, fetch, await, npm
---
# JavaScript / Node basics

Modern JS is `async`/`await` for anything I/O — never use blocking patterns.

```js
// async/await + fetch (Node 18+)
async function main() {
  const res = await fetch("https://api.example.com/items", {
    headers: { "Authorization": "Bearer TOKEN" },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  console.log(data.length);
}

main().catch((err) => { console.error(err); process.exit(1); });
```

Gotchas:
- `fetch` is built into Node 18+/browsers — no axios needed.
- Always `await` promises or `.catch` them; an unhandled rejection crashes
  Node.
- `npm install` adds deps to `package.json`; don't commit `node_modules`
  (it's gitignored).
- `const`/`let`, never `var`. Arrow functions for callbacks.
- String templates with backticks: `` `hello ${name}` ``.

A tiny Node script pattern:
```js
const fs = require("node:fs/promises");
async function read() {
  const text = await fs.readFile("data.txt", "utf-8");
  console.log(text.trim());
}
read();
```
