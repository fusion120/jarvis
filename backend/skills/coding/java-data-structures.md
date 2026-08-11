---
lang: java
keywords: linkedlist, stack, priority queue, heap, hashmap, deque, arraydeque, data structure
---

# Core Data Structures: LinkedList, Stack, PriorityQueue, HashMap

Pick the structure by its contract: `ArrayDeque` for stack/queue (faster than legacy `Stack`), `PriorityQueue` as a heap for "smallest/largest next", `HashMap` for key lookup — but never mutate a key after insertion. Each has sharp performance edges worth knowing.

```java
import java.util.*;

public class DataStructures {
    public static void main(String[] args) {
        // Deque as a double-ended queue (recent-items list)
        Deque<String> recent = new ArrayDeque<>();
        recent.addFirst("view1");
        recent.addFirst("view2");
        recent.addFirst("view3");
        System.out.println("most recent: " + recent.peekFirst());
        System.out.println("popped: " + recent.pollFirst());

        // Stack semantics — ArrayDeque, not the legacy Stack class
        Deque<Integer> stack = new ArrayDeque<>();
        stack.push(1); stack.push(2); stack.push(3);
        System.out.println("pop: " + stack.pop() + ", peek: " + stack.peek());

        // PriorityQueue = heap; head is always least per comparator
        PriorityQueue<Integer> maxHeap = new PriorityQueue<>(Comparator.reverseOrder());
        maxHeap.addAll(List.of(4, 1, 9, 2));
        System.out.println("max=" + maxHeap.peek() + " then " + maxHeap.poll());

        // HashMap: NEVER mutate a key's hash after insertion
        Map<MutableKey, String> map = new HashMap<>();
        MutableKey k = new MutableKey(1);
        map.put(k, "one");
        k.value = 2; // hash changes -> bucket changes -> entry becomes unreachable
        System.out.println("still present? " + map.containsKey(k) + " (entry is lost)");
    }

    static class MutableKey {
        int value;
        MutableKey(int v) { value = v; }
        public int hashCode() { return value; }
        public boolean equals(Object o) {
            return o instanceof MutableKey mk && mk.value == value;
        }
    }
}
```

Gotchas:
- `LinkedList` is a `List` AND a `Deque`; random access `get(i)` is O(n) — use `ArrayList` for index reads, `LinkedList`/`ArrayDeque` only for end operations.
- The legacy `Stack` class synchronizes every method; `ArrayDeque` doesn't and is the documented replacement.
- `PriorityQueue` is NOT sorted — only the head is guaranteed least; iterating it gives arbitrary order. Heapify with a bulk `addAll` is O(n), inserting one-by-one is O(n log n).
- `HashMap` resize is O(n) and buckets degrade to trees past a threshold — a terrible `hashCode` (constant, or mutable as above) turns it into O(n) lookups.
- `TreeMap`/`TreeSet` (sorted) need either `Comparable` or a comparator and log-n ops — don't use them when plain `HashMap` order doesn't matter.
- `EnumMap`/`EnumSet` are array-backed and far faster than `HashMap`/`HashSet` for enum keys. And `null` keys: `HashMap` allows one; `TreeMap` and `Hashtable` reject it.
