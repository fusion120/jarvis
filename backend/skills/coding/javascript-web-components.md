---
lang: javascript
keywords: custom element, web component, customElements.define, connectedCallback, attributeChangedCallback, observedAttributes, lifecycle, reusable component
---

# Web Components / custom elements

Custom elements are framework-free reusable components: `customElements.define` registers a class-backed tag, lifecycle callbacks hook into mount/attribute/removal, and `observedAttributes` drives attribute reactivity. Use them for self-contained widgets that work in any app.

```javascript
// browser
// <user-card first="Ada" last="Lovelace"></user-card>
class UserCard extends HTMLElement {
  static get observedAttributes() { return ["first", "last"]; }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });   // isolated DOM + styles
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; border: 1px solid #ccc; border-radius: 8px; padding: 8px; }
        .name { font-weight: 700; }
      </style>
      <div class="name"></div>
      <button>Edit</button>
    `;
  }

  // Called when the element is inserted into the document
  connectedCallback() {
    this.render();
    this.shadowRoot.querySelector("button")
      .addEventListener("click", () => this.dispatchEvent(new CustomEvent("edit", {
        bubbles: true,
        composed: true,
        detail: { first: this.first, last: this.last },
      })));
  }

  // Called when an observed attribute changes
  attributeChangedCallback(name, _oldVal, newVal) {
    if (this.isConnected) this.render();
  }

  get first() { return this.getAttribute("first") ?? ""; }
  get last() { return this.getAttribute("last") ?? ""; }

  render() {
    this.shadowRoot.querySelector(".name").textContent =
      `${this.first} ${this.last}`.trim();
  }
}

customElements.define("user-card", UserCard);

// Use it anywhere, set attributes later:
// const card = document.createElement("user-card");
// card.setAttribute("first", "Grace");
// document.body.append(card);
```

Gotchas:
- Custom element tag names MUST contain a hyphen — `customElements.define("userCard", …)` throws.
- `constructor` runs at `createElement` time, BEFORE attributes/children exist — do all DOM in `connectedCallback`, not the constructor.
- Moving an element fires `disconnectedCallback` then `connectedCallback` again — guard against double-registered listeners.
- `attributeChangedCallback` only fires for attributes listed in `observedAttributes`.
- `innerHTML` on the host (light DOM) vs `shadowRoot`: styles don't leak OUT of shadow DOM, and host styles don't apply inside unless via `:host`/CSS parts.
- Attributes are strings — parse numbers/booleans yourself (`attr === "true"`, `Number(attr)`).
- Custom events need `composed: true` to cross the shadow boundary; `bubbles: true` alone isn't enough.
