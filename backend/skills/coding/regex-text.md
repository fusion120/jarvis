---
lang: general
keywords: regex, replace, search, extract, match, text, string
---
# Work with text and regex in Python

Use raw strings (`r"..."`) so backslashes aren't double-escaped.

```python
import re

text = "orders: #A-123, #B-456"

# extract all matches
ids = re.findall(r"#([A-Z]-\d+)", text)      # -> ['A-123', 'B-456']

# replace
fixed = re.sub(r"#([A-Z])-", r"ID-\1-", text)

# test
m = re.search(r"\b(fail|error)\b", text.lower())
print(bool(m))
```

Gotchas:
- **Always use raw strings** `r"..."` for patterns.
- `.` matches any char; escape it as `\.` for a literal dot.
- `\b` = word boundary, `\d` = digit, `\s` = whitespace, `+`/`*`/`?` = one
  or more / zero or more / optional.
- Capturing groups `(...)` are what `findall` returns; use `(?:...)` for a
  non-capturing group.
- For parsing HTML use BeautifulSoup, NOT regex — regex on HTML is a trap.
- Test the pattern on the exact real text before trusting it; real-world text
  almost always has edge cases (case, punctuation).
