---
lang: javascript
keywords: template literal, backtick, string interpolation, tagged template, multiline string, escape, ${}, String.raw
---

# Template literals

Backtick strings interpolate `${expr}`, span multiple lines, and can be processed by tagged template functions. Reach for them for SQL/HTML builders, log formatting, and any string that mixes variables with static text.

```javascript
// Interpolation + multiline
const user = { name: "Ada", city: "London", visits: 3 };
const msg = `Hello ${user.name} from ${user.city} — visit #${user.visits}.`;
console.log(msg);

// Multiline without \n hacks
const sql = `
  SELECT name, city
  FROM users
  WHERE visits > ${2}
`;
console.log(sql.trim());

// Expressions, not just variables
const total = 19.99 * 3;
console.log(`Total: $${total.toFixed(2)} (${Math.round(total)} rounded)`);

// Tagged template: escape user input for HTML (XSS-safe)
function html(strings, ...values) {
  const esc = (v) => String(v)
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;").replaceAll('"', "&quot;");
  return strings.reduce(
    (out, s, i) => out + s + (i < values.length ? esc(values[i]) : ""),
    ""
  );
}
const input = "<script>alert('x')</script>";
console.log(html`<div>${input}</div>`);           // escaped, safe

// String.raw: no escape processing (regex, paths, Windows)
const path = String.raw`C:\Users\elsay\data\file.txt`;
console.log(path);                                // literal backslashes
```

Gotchas:
- A `${` must be a real interpolation — to print a literal dollar-brace you need `\${`.
- Template literals preserve indentation/whitespace including trailing blank lines — `.trim()` before logging or diffing.
- `undefined`/`null` interpolate as the strings "undefined"/"null" — use `?? ""` for optional fields.
- Tagged templates pass a frozen, cooked `strings` array; do NOT mutate it (spread it first).
- Raw newlines inside backticks are real newlines (LF), which changes line-counting tools — `String.raw` only stops backslash escapes, not real newlines.
- You can nest `` `${ `inner` }` `` but only inside an interpolation; a stray backtick elsewhere closes the string.
