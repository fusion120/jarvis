---
lang: javascript
keywords: regex, regular expression, replace, test, exec, capture group, named group, lookahead, flags, matchAll, escape
---

# Regex in JavaScript

RegExp literals and `match/replace/test/exec` power pattern matching in JS. Use them for validation, extraction, and rewriting — but escape user input before building patterns and prefer named groups for readable code.

```javascript
// Flags: g (global), i (ignore case), m (multiline), s (dotall), u (unicode), y (sticky)
const email = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
console.log(email.test("ada@example.com"));    // true

// Named capture groups
const logLine = /^(?<level>INFO|WARN|ERROR)\s+(?<msg>.*)$/;
const m = logLine.exec("ERROR disk full");
if (m) {
  console.log(m.groups.level, m.groups.msg);   // ERROR disk full
}

// matchAll with global flag
const text = "IDs: A-12, B-34, C-56";
const ids = [...text.matchAll(/([A-Z])-(\d+)/g)].map((mm) => mm[0]);
console.log(ids);                              // ["A-12","B-34","C-56"]

// replace with a function + named groups
const swap = "2026-08-07".replace(
  /^(?<y>\d{4})-(?<mo>\d{2})-(?<d>\d{2})$/,
  (...args) => {
    const { y, mo, d } = args.at(-1);          // groups object is the last arg
    return `${d}/${mo}/${y}`;
  }
);
console.log(swap);                             // 07/08/2026

// Lookahead: at least one digit and one uppercase, 8+ chars
const strong = /^(?=.*\d)(?=.*[A-Z]).{8,}$/;
console.log(strong.test("passWord1"));         // true

// Escaping user input when building a pattern
const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const search = new RegExp(`\\b${escapeRe("c++")}\\b`, "i");
```

Gotchas:
- `.test`/`.exec` with the `g` flag are STATEFUL — `lastIndex` advances, so reuse in a loop can skip matches or return `null` intermittently. Reset `lastIndex = 0` or use `matchAll`.
- `\d` matches only ASCII digits (even with `u`) — use `\p{N}` with the `u` flag for full Unicode.
- Backslashes in `new RegExp("\\d")` must be double-escaped; literal `/.../` avoids this.
- In the replace string, `$&`, `$1`, `$<name>` are special — a literal `$` needs `$$`.
- Catastrophic backtracking: nested quantifiers like `(a+)+$` can hang on near-misses; keep patterns linear.
- `match` without `g` returns full match + groups; with `g` it returns only full matches — use `matchAll` when you need both.
