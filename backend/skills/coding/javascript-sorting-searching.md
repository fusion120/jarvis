---
lang: javascript
keywords: sort, binary search, quicksort, merge sort, comparator, stable sort, search algorithm, toSorted, sorted array, algorithm
---

# Sorting & searching

JS `Array.prototype.sort` (and non-mutating `toSorted`) handles general sorting, but binary search needs implementing — and it's the difference between O(n) and O(log n) lookups on a sorted array. Reach for a custom comparator when sorting objects, and a custom binary search when you search repeatedly.

```javascript
// Sort with a stable comparator
const users = [
  { name: "ada", score: 90 },
  { name: "bob", score: 75 },
  { name: "cyd", score: 90 },
];
users.sort((a, b) => b.score - a.score);        // desc; stable: ada before cyd
console.log(users.map((u) => u.name));           // ["ada","cyd","bob"]

// Non-mutating copy (toSorted, ES2023)
const sorted = [...users].sort((a, b) => a.score - b.score);

// Binary search: returns index or -1
function binarySearch(arr, target) {
  let lo = 0, hi = arr.length - 1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;                  // safe floor midpoint
    const v = arr[mid];
    if (v === target) return mid;
    if (v < target) lo = mid + 1;
    else hi = mid - 1;
  }
  return -1;
}
const nums = [1, 3, 5, 7, 9];
console.log(binarySearch(nums, 5));              // 2
console.log(binarySearch(nums, 6));              // -1

// lowerBound: first index >= target (insertion points / ranges)
function lowerBound(arr, target) {
  let lo = 0, hi = arr.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (arr[mid] < target) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}
console.log(lowerBound(nums, 6));                // 3 (insert position)

// quickselect: kth smallest (0-indexed), average O(n)
function quickselect(arr, k) {
  const a = [...arr];
  let lo = 0, hi = a.length - 1;
  while (lo < hi) {
    const pivot = a[hi]; let i = lo;
    for (let j = lo; j < hi; j++) if (a[j] < pivot) [a[i++], a[j]] = [a[j], a[i]];
    [a[i], a[hi]] = [a[hi], a[i]];
    if (i === k) return a[k];
    if (i < k) lo = i + 1; else hi = i - 1;
  }
  return a[lo];
}
console.log(quickselect([7, 3, 9, 1, 5], 2));    // 5 (3rd smallest)
```

Gotchas:
- The default `sort()` compares elements as STRINGS — `[10, 9].sort()` → `[10, 9]`. Always pass `(a, b) => a - b` for numbers.
- Plain `<`/`>` string comparison is byte order — use `"ä".localeCompare("z")` for correct human ordering.
- `sort` mutates in place; use `toSorted` (ES2023) or copy for immutable style.
- `mid = (lo + hi) / 2` gives a float — use `>> 1` or `Math.floor((lo + hi) / 2)`.
- Binary search requires a SORTED array — on unsorted data it silently returns wrong results, not errors.
- Off-by-ones between `lo < hi` vs `lo <= hi` and `+1/-1` are the classic bugs — test on 1- and 2-element arrays.
- `sort` is stable in modern engines, so equal elements keep original order — handy for multi-key sorts (sort by name, then score).
