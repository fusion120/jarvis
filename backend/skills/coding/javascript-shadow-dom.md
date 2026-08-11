---
lang: javascript
keywords: shadow dom, attachShadow, shadowRoot, closed shadow, encapsulation, slot, :host, composedPath, event retargeting, style isolation
---

# Shadow DOM encapsulation

Shadow DOM attaches a hidden DOM tree to an element: its styles can't leak out and the page's styles can't leak in. Slots project light-DOM children into the shadow tree. Reach for it when building components that must not fight the host page's CSS.

```javascript
// browser
const host = document.getElementById("tooltip-host");

const root = host.attachShadow({ mode: "open" });   // "closed" blocks host.shadowRoot

root.innerHTML = `
  <style>
    :host { position: relative; display: inline-block; }
    .tip {
      position: absolute; bottom: 120%; left: 0;
      background: #333; color: #fff; padding: 6px 10px;
      border-radius: 4px; font-size: 12px;
      display: none;
    }
    slot[name="trigger"] { cursor: help; }
  </style>
  <slot name="trigger">hover me</slot>
  <div class="tip"><slot></slot></div>
`;

// Show/hide the tooltip on the HOST element (events bubble out)
host.addEventListener("pointerenter", () => {
  root.querySelector(".tip").style.display = "block";
});
host.addEventListener("pointerleave", () => {
  root.querySelector(".tip").style.display = "none";
});

// event.composedPath() shows the real path across the boundary
document.addEventListener("click", (e) => {
  const path = e.composedPath();
  console.log(path[0]);                       // innermost element
  console.log(path.includes(host));           // true
});
```

```html
<!-- browser -->
<!--
  <div id="tooltip-host">
    <button slot="trigger">hover</button>
    <span>Tooltip content from light DOM</span>
  </div>
-->
```

Gotchas:
- `mode: "closed"` is mostly theater: it blocks `host.shadowRoot` but is bypassable and hurts debugging — prefer `"open"` unless you have a reason.
- Document-level styles don't reach inside (that's the point), but the shadow tree also can't style light-DOM children — use `::slotted()` for projected content.
- `:host` styles the host element from inside; `:host-context`/CSS parts (`part="..."`) are the escape hatches for theming.
- Light-DOM children go into `<slot>`s; un-slotted content is hidden — you must decide where each slot renders.
- Events bubbling out of shadow DOM are RETARGETED to look like they came from the host — `e.target` will be the host, use `composedPath()` for the real origin.
- `focus`/`blur` don't bubble across the boundary — listen inside the shadow root or use `focusin`.
- You can't use `document.querySelector` to find shadow-internal elements — query the `shadowRoot` itself.
