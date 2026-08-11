---
lang: javascript
keywords: document, querySelector, createElement, appendChild, innerHTML, classList, dataset, DocumentFragment, textContent, event listener
---

# DOM manipulation

The DOM API is the browser's document tree: `querySelector`/`createElement`/`append` build and place nodes, `classList` toggles state, and `textContent` writes data safely. Prefer building nodes over `innerHTML` when data is involved.

```javascript
// browser
// Build a list of items efficiently with a DocumentFragment
const list = document.getElementById("items");
const frag = document.createDocumentFragment();

for (const [label, url] of Object.entries({
  "Node docs": "https://nodejs.org",
  "MDN": "https://developer.mozilla.org",
})) {
  const li = document.createElement("li");
  const a = document.createElement("a");
  a.href = url;
  a.textContent = label;              // safe: no HTML parsing
  li.append(a);
  li.dataset.source = "bookmarks";
  frag.append(li);
}
list.append(frag);                    // one reflow, not N

// Toggle state and read back
const btn = document.getElementById("toggle");
btn.addEventListener("click", () => {
  btn.classList.toggle("active");
  const on = btn.classList.contains("active");
  btn.setAttribute("aria-pressed", String(on));
});

// Replace content safely
const out = document.getElementById("status");
out.textContent = "Loading…";                       // escapes HTML
out.replaceChildren();                              // clear all children fast

// closest / matches for navigation
document.addEventListener("click", (e) => {
  const card = e.target.closest(".card");
  if (card) console.log(card.dataset.id);
});
```

Gotchas:
- `innerHTML` reparses and can execute injected `<script>`/event-handler HTML — use `textContent` for data and `createElement` for markup.
- `append` accepts nodes AND strings; `appendChild` only nodes — passing a string to `appendChild` throws TypeError.
- `querySelectorAll` returns a STATIC NodeList — re-query after adding nodes or you'll miss them (getElementsBy* are live).
- Inserting a node that already exists MOVES it — appending the same element twice just relocates it.
- Batching many appends into a `DocumentFragment` (or `replaceChildren`) avoids layout thrash.
- `dataset` maps camelCase (`data-my-key` → `dataset.myKey`); keys with dashes need bracket access.
