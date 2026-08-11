---
lang: java
keywords: recursion, recursive, backtracking, memoization, base case, divide and conquer, subsets, recursion depth, stack overflow
---

# Recursion Patterns

Recursion shines for divide-and-conquer (binary search), backtracking (subsets/permutations), and self-similar structures (trees). Three disciplines make it safe: a base case that terminates, a strictly-smaller subproblem, and memoization when subproblems repeat — otherwise exponential blowup.

```java
import java.util.*;

public class RecursionPatterns {
    // memoized Fibonacci: O(n) instead of exponential
    static long fib(int n, long[] memo) {
        if (n <= 1) return n;
        if (memo[n] != 0) return memo[n];
        return memo[n] = fib(n - 1, memo) + fib(n - 2, memo);
    }

    // backtracking: all subsets of a list
    static void subsets(List<Integer> set, int i, List<Integer> acc, List<List<Integer>> out) {
        if (i == set.size()) {
            out.add(new ArrayList<>(acc)); // copy! acc is mutated afterwards
            return;
        }
        acc.add(set.get(i));          // take it
        subsets(set, i + 1, acc, out);
        acc.remove(acc.size() - 1);   // undo (backtrack)
        subsets(set, i + 1, acc, out); // skip it
    }

    // divide & conquer: binary search
    static int binarySearch(int[] a, int lo, int hi, int target) {
        if (lo > hi) return -1;
        int mid = lo + (hi - lo) / 2; // avoids lo+hi overflow
        if (a[mid] == target) return mid;
        if (target < a[mid]) return binarySearch(a, lo, mid - 1, target);
        return binarySearch(a, mid + 1, hi, target);
    }

    public static void main(String[] args) {
        System.out.println("fib(30) = " + fib(30, new long[31]));

        List<List<Integer>> out = new ArrayList<>();
        subsets(List.of(1, 2, 3), 0, new ArrayList<>(), out);
        System.out.println("subset count = " + out.size()); // 2^3 = 8

        int[] sorted = {1, 3, 5, 7, 9};
        System.out.println("index of 5 = " + binarySearch(sorted, 0, sorted.length - 1, 5));
    }
}
```

Gotchas:
- Every recursive path must reach a base case; a missing/incomplete base case = infinite recursion -> `StackOverflowError`.
- Each call must shrink the problem (smaller `n`, larger index, halved range); recursion that doesn't shrink is a bug.
- Backtracking needs a *copy* when storing results (`new ArrayList<>(acc)`) because the accumulator is reused and mutated.
- Plain recursion on overlapping subproblems (Fibonacci, grid paths) is exponential — memoize, or use bottom-up DP.
- `(lo + hi) / 2` can overflow for huge `hi`; `lo + (hi - lo) / 2` can't.
- Deep recursion (say >5k-10k frames) overflows the default stack — switch to an iterative loop or bump `-Xss` only as a last resort. And recursion buys clarity, not speed; the JVM JITs loops well.
