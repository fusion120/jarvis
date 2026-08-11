---
lang: java
keywords: merge sort, quick sort, sort algorithm, divide and conquer, recursion sort, partitioning, in-place, stable sort
---

# Merge Sort & Quick Sort

Understand both classics: merge sort is O(n log n) worst-case with O(n) extra memory and is *stable*; quicksort is in-place with O(log n) stack depth but degrades to O(n^2) on already-sorted input without good pivot selection. Reach for these when you must implement sorting yourself (e.g., custom data layouts); otherwise `Arrays.sort`/`List.sort` win.

```java
import java.util.*;

public class SortingAlgorithms {
    static void mergeSort(int[] a) {
        if (a.length < 2) return;
        int mid = a.length / 2;
        int[] left = Arrays.copyOfRange(a, 0, mid);
        int[] right = Arrays.copyOfRange(a, mid, a.length);
        mergeSort(left);
        mergeSort(right);
        merge(a, left, right);
    }

    static void merge(int[] a, int[] l, int[] r) {
        int i = 0, j = 0, k = 0;
        while (i < l.length && j < r.length) a[k++] = (l[i] <= r[j]) ? l[i++] : r[j++];
        while (i < l.length) a[k++] = l[i++];
        while (j < r.length) a[k++] = r[j++];
    }

    static void quickSort(int[] a) { quickSort(a, 0, a.length - 1); }

    static void quickSort(int[] a, int lo, int hi) {
        if (lo >= hi) return;
        int p = partition(a, lo, hi); // Lomuto partition, last element pivot
        quickSort(a, lo, p - 1);
        quickSort(a, p + 1, hi);
    }

    static int partition(int[] a, int lo, int hi) {
        int pivot = a[hi];
        int i = lo;
        for (int j = lo; j < hi; j++) {
            if (a[j] < pivot) {
                int t = a[i]; a[i] = a[j]; a[j] = t;
                i++;
            }
        }
        int t = a[i]; a[i] = a[hi]; a[hi] = t;
        return i;
    }

    public static void main(String[] args) {
        int[] x = {5, 2, 8, 1, 9, 3, 7};
        int[] y = x.clone();
        mergeSort(x);
        quickSort(y);
        System.out.println("merge=" + Arrays.toString(x));
        System.out.println("quick=" + Arrays.toString(y));
    }
}
```

Gotchas:
- Recursive sorts on large arrays risk `StackOverflowError` — quicksort recursion depth is O(log n) with good pivots but O(n) worst case; cap or fall back to insertion sort for small slices.
- Lomuto partition with the last element as pivot degrades to O(n^2) on sorted input — pick a random or median-of-three pivot for adversarial data.
- Merge sort's O(n) auxiliary arrays make it unsuitable for constrained-memory embedded targets; in-place merges are far more complex.
- `<=` in the merge makes merge sort stable (equal elements keep order); strict `<` destroys stability.
- Off-by-one on the split index is the classic bug — make the halves `[0, mid)` and `[mid, n)` so they tile exactly.
- For production code use `Arrays.sort` (dual-pivot quicksort for primitives, TimSort for objects) — custom sorts are for learning or exotic comparators.
