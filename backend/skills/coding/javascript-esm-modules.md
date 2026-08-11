---
lang: javascript
keywords: esm, import, export, named export, default export, dynamic import, import.meta, node modules, package.json type module, tree shaking
---

# ESM modules

ECMAScript modules (`import`/`export`) are the standard module system for modern JS — static, analyzable, and live. Reach for ESM in new Node projects (`"type": "module"`) and browsers via `<script type="module">`, and use dynamic `import()` for lazy loading.

```javascript
// math.js
export const TAU = Math.PI * 2;
export function double(n) { return n * 2; }
export default function add(a, b) { return a + b; }
```

```javascript
// app.js — run with `node app.js` in a package with "type":"module"
import add, { TAU, double as twice } from "./math.js";   // default + named + alias

console.log(add(2, 3));        // 5
console.log(twice(TAU));       // 4π

// Dynamic import for lazy/code-split loading
async function loadMath() {
  const mod = await import("./math.js");
  return mod.double(21);
}

// import.meta — the module's own URL
console.log(import.meta.url);  // file:///…/app.js
```

```json
// package.json
{ "name": "demo", "type": "module" }
```

```javascript
// browser — index.html
// <script type="module" src="./app.js"></script>
// Module scripts are deferred by default, always strict mode,
// and require http(s):// — they fail over file:// due to CORS.
```

Gotchas:
- `.js` files are CJS unless `"type": "module"` is set (or use `.mjs`); mixing `require` and `import` in one file throws SyntaxError.
- Only one `export default` per module; `export { x as y }` renames named exports.
- Imports are hoisted and live bindings: importing a `let` sees later mutations, and circular imports can see `undefined` before initialization — avoid cycles.
- Dynamic `import()` returns a Promise and works from CJS too; static import doesn't.
- Browsers block module scripts over `file://` (CORS) — serve via `http://localhost` for tests.
- Top-level await is allowed in ESM but not CJS — great for `await import()` at module scope.
- `import.meta.url` replaces CJS `__dirname`; build paths with `new URL("./data.txt", import.meta.url)`.
