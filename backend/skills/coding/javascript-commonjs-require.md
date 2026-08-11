---
lang: javascript
keywords: commonjs, require, module.exports, exports, node require, module caching, circular dependency, __dirname, index.js resolution, package.json main
---

# CommonJS require

CommonJS is Node's original module system: `require()` loads and caches modules synchronously, `module.exports` defines what they expose. It's still the default for `.js` files without `"type": "module"` and for most npm packages.

```javascript
// utils.js
const path = require("node:path");

const util = {
  title(str) { return str.charAt(0).toUpperCase() + str.slice(1); },
  abs(p) { return path.resolve(p); },
};
module.exports = util;              // export an object
```

```javascript
// app.js  (npm install express if you run the node_modules line)
const util = require("./utils");    // relative path (./ required)
const fs = require("node:fs");      // built-in via node: prefix
const express = require("express"); // node_modules lookup

console.log(util.title("hello"));   // Hello
console.log(require.resolve("./utils"));  // absolute path Node resolves to

exports.extra = "still works";      // exports is module.exports initially

// __dirname / __filename are file-location globals
console.log(__dirname, __filename);
```

```json
// package.json
{ "name": "demo", "main": "src/index.js" }   // require("demo") resolves here
```

Gotchas:
- `require` is synchronous and cached by resolved path: the first call runs the file, later calls return the same object — mutation leaks across importers.
- `exports = something` silently does nothing (you rebound a local var); use `module.exports`.
- Don't mix `exports.foo` and `module.exports = {...}` in one file — the reassignment drops prior `exports.x` properties.
- Relative requires must start with `./` or `../`; bare names look up `node_modules` (walking up parent dirs).
- `require` of a directory loads its `index.js` or `package.json#main`.
- `__dirname`/`__filename` don't exist in ESM — use `import.meta.url` there.
- Circular requires give you a partially-initialized export — export what you need before requiring back.
