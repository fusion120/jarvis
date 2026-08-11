---
lang: python
keywords: heap, heapq, priority queue, top k, largest, merge, push, pop, heapify, nlargest
---

# Heaps with heapq: top-k and sorted merge

A heap is a binary tree that keeps the *smallest* element at the root — O(log n) push/pop,
O(1) peek. `heapq` is Python's min-heap. Two classic uses: streaming "top K" of a large
sequence and merging several sorted lists.

```python
import heapq


def top_k(numbers: list[int], k: int) -> list[int]:
    """Largest k values in one pass, O(n log k) memory O(k)."""
    heap: list[int] = []
    for n in numbers:
        if len(heap) < k:
            heapq.heappush(heap, n)
        elif n > heap[0]:                    # beat the current k-th largest
            heapq.heapreplace(heap, n)       # pop smallest, push n — one op
    return sorted(heap, reverse=True)


def merge_sorted(*lists: list[int]) -> list[int]:
    """Merge k sorted lists into one sorted list."""
    result: list[int] = []
    heap = [(lst[0], i, 0) for i, lst in enumerate(lists) if lst]
    heapq.heapify(heap)
    while heap:
        value, list_idx, item_idx = heapq.heappop(heap)
        result.append(value)
        nxt = item_idx + 1
        if nxt < len(lists[list_idx]):
            heapq.heappush(heap, (lists[list_idx][nxt], list_idx, nxt))
    return result


print(top_k([5, 1, 9, 3, 7, 2, 8], 3))
print(merge_sorted([1, 4, 7], [2, 5, 8], [3, 6, 9]))
```

Gotchas:
- `heapq` is a **min-heap**: `heappop` returns the smallest. For a max-heap push negatives or
  wrap elements in a reverse-key class — there is no `max_heap` mode.
- `heapreplace(heap, item)` returns the *popped* value; it's one operation but don't use it on
  an empty heap (raises `IndexError`).
- Tuple ordering in a heap compares element-by-element — tie-breakers must be comparable.
  Two items with the same first value need a unique second value or `TypeError` on comparison.
- `heapify` is O(n) and only needed once to convert an existing list; `heappush`/`heappop`
  per element is the normal pattern.
- Top-k with a *min-heap of size k* keeps the k largest (smallest at root, evicted when beaten).
  Using `max` heap of size k instead needs different bookkeeping and is easy to get wrong.
- For one-off top-k on a materialized list, `heapq.nlargest(k, items)` is simpler and faster;
  hand-roll the heap only when the data streams or k is dynamic.
