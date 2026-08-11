---
lang: javascript
keywords: string algorithms, palindrome, anagram, substring search, longest common prefix, KMP, edit distance, levenshtein, word frequency, text processing
---

# String algorithms

Strings are sequences — the same two-pointer, sliding-window, and DP ideas that work on arrays apply. Reach for these when processing text: normalization (lowercase/strip) is usually step one, then choose the right scan.

```javascript
// Palindrome check (normalized)
const isPalindrome = (s) => {
  const clean = s.toLowerCase().replace(/[^a-z0-9]/g, "");
  return clean === [...clean].reverse().join("");
};
console.log(isPalindrome("A man, a plan, a canal: Panama")); // true

// Anagram check
const isAnagram = (a, b) => {
  const norm = (s) => s.toLowerCase().replace(/\s+/g, "").split("").sort().join("");
  return norm(a) === norm(b);
};
console.log(isAnagram("listen", "silent"));        // true

// Longest common prefix
function longestCommonPrefix(words) {
  if (!words.length) return "";
  let prefix = words[0];
  for (const w of words.slice(1)) {
    while (!w.startsWith(prefix)) prefix = prefix.slice(0, -1);
    if (!prefix) return "";
  }
  return prefix;
}
console.log(longestCommonPrefix(["flower", "flow", "flight"])); // "fl"

// Word frequency (top k, deterministic tie-break)
function topWords(text, k) {
  const counts = new Map();
  for (const w of text.toLowerCase().match(/[a-z']+/g) ?? []) {
    counts.set(w, (counts.get(w) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, k)
    .map(([w]) => w);
}
console.log(topWords("the quick brown fox jumps over the lazy dog the", 2)); // ["the","brown"]

// Sliding window: longest substring without repeating chars
function longestUnique(s) {
  const seen = new Map();
  let best = 0, start = 0;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (seen.has(c) && seen.get(c) >= start) start = seen.get(c) + 1;
    seen.set(c, i);
    best = Math.max(best, i - start + 1);
  }
  return best;
}
console.log(longestUnique("abcabcbb"));            // 3 ("abc")
```

Gotchas:
- Normalize BEFORE comparing: case-folding and removing punctuation changes every algorithm's input contract.
- `[...s]` handles code points (emoji, surrogate pairs) while `s[i]`/`s.split("")` split surrogate pairs — decide which semantics you need.
- Unicode normalization (`s.normalize("NFD")`) merges composed vs decomposed accents ("é" vs "é") before comparison.
- `String.prototype.replace` with a string replaces only the FIRST occurrence — use `replaceAll` or regex with `g` for global.
- Regex matches return arrays of matched strings, not positions; use `matchAll`/`exec` with `index` when you need offsets.
- Word frequency tie-break: `b[1] - a[1] || a[0].localeCompare(b[0])` keeps deterministic order for equal counts.
- Sliding-window `start` must not move backward — the `>= start` guard above is the subtle part; dropping it breaks correctness.
