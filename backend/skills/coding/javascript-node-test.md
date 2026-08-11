---
lang: javascript
keywords: node test, node:test, unit test, assert, describe, it, mock, test runner, coverage, mock.fn, node --test
---

# node:test unit tests

Node's built-in `node:test` runner (Node 18+) needs no dependencies: `test()`/`describe()`/`it()`, `assert`, and `mock` are all standard library. Run with `node --test`. Use `mock.fn`/`mock.method` to isolate units from I/O and `beforeEach` for fresh fixtures.

```javascript
// math.js — code under test
function add(a, b) { return a + b; }
function parseCsv(text) {
  const lines = text.trim().split("\n").filter(Boolean);
  if (lines.length === 0) throw new Error("empty CSV");
  return lines.map((l) => l.split(","));
}
module.exports = { add, parseCsv };
```

```javascript
// math.test.js — run with: node --test
const { test, describe, it, beforeEach, mock } = require("node:test");
const assert = require("node:assert/strict");
const { add, parseCsv } = require("./math.js");

test("add returns the sum", () => {
  assert.equal(add(2, 3), 5);
});

// Grouped with hooks
describe("parseCsv", () => {
  beforeEach(() => { /* fresh fixture per test */ });

  it("parses rows into arrays", () => {
    assert.deepEqual(parseCsv("a,b\nc,d"), [["a", "b"], ["c", "d"]]);
  });

  it("handles trailing newline", () => {
    assert.deepEqual(parseCsv("1\n"), [["1"]]);
  });

  it("fails on empty input", () => {
    assert.throws(() => parseCsv(""), /empty CSV/);
  });
});

// Async tests + mocking
test("awaits async work", async () => {
  const result = await Promise.resolve(42);
  assert.equal(result, 42);
});

test("mock.fn replaces a function", () => {
  const fn = mock.fn((x) => x * 2);
  assert.equal(fn(4), 8);
  assert.equal(fn.mock.calls.length, 1);
  assert.deepEqual(fn.mock.calls[0].arguments, [4]);
});

// Subtests + skip
test("suite with subtests", async (t) => {
  await t.test("case a", () => assert.ok(true));
  await t.test("case b", { skip: "not implemented yet" }, () => assert.ok(false));
});
```

Gotchas:
- Run with `node --test` (discovers `*.test.js`/`test/*.js`); a plain `node math.test.js` also works since it's just a script.
- `node:assert/strict` is the modern default; plain `assert` uses loose equality unless strict.
- `assert.deepEqual` from the strict module checks prototypes + own props — `{a:1}` vs an object instance with the same shape differ.
- Hooks: `beforeEach` re-runs per test but shares module-level state if you mutate it — return fresh fixtures, don't accumulate.
- `mock.method(obj, "name", impl)` patches and auto-restores; call `mock.restoreAll()` in `afterEach` if you mock in loops.
- Async tests must return the promise (or be `async`): forgetting the `await`/return makes the test pass while the work fails later.
- A hung promise hangs the run — pass `{ timeout: 5000 }` on long tests.
