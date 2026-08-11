---
lang: javascript
keywords: event delegation, event.target, closest, addEventListener, bubbling, click handler, dynamic elements, data attribute, stopPropagation
---

# Event delegation

Event delegation attaches ONE listener to a parent and catches events bubbling up from children — perfect for lists, tables, and dynamically added elements. Use `e.target.closest(selector)` to find the interactive element and `dataset` for payloads.

```javascript
// browser
// One listener for the whole list, works for items added later
const list = document.getElementById("todo-list");

list.addEventListener("click", (e) => {
  const item = e.target.closest("[data-action]"); // walk up to the action
  if (!item) return;                              // ignore clicks elsewhere
  const action = item.dataset.action;             // "done" | "remove"
  if (action === "remove") {
    item.remove();
  } else if (action === "done") {
    item.classList.toggle("done");
    updateCount();
  }
});

// Add items dynamically — no new listeners needed
function addTodo(text) {
  const li = document.createElement("li");
  const span = document.createElement("span");
  span.textContent = text;                        // safe, no HTML parsing
  const btnDone = document.createElement("button");
  btnDone.textContent = "done";
  btnDone.dataset.action = "done";
  const btnRemove = document.createElement("button");
  btnRemove.textContent = "remove";
  btnRemove.dataset.action = "remove";
  li.append(span, btnDone, btnRemove);
  list.appendChild(li);
}

function updateCount() {
  const open = list.querySelectorAll("li:not(.done)").length;
  document.getElementById("count").textContent = String(open);
}

addTodo("buy milk");
addTodo("deploy app");

// Keyboard access: same handler works if you also listen for keys
list.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && e.target.matches("[data-action]")) {
    e.target.click();
  }
});
```

Gotchas:
- `e.target` is the innermost element clicked; use `closest('[data-action]')` (or `matches`) instead of assuming it IS the button.
- `closest()` returns `null` when nothing matches — guard before using `.dataset`.
- Event delegation relies on bubbling; it breaks for `pointerenter`, `focus`, `blur`, `scroll`, and `load`, which don't bubble (use `focusin`/`focusout`).
- `e.target` is always an Element (text nodes are skipped), but clicks on a nested span still resolve via `closest`.
- Don't `stopPropagation` on the delegated target or other delegated listeners higher up never see it.
- Building items with `innerHTML` and user text is an XSS hole — use `textContent` for data, or build DOM nodes.
