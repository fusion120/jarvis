---
lang: java
keywords: dynamic programming, knapsack, longest common subsequence, memoization, dp table, optimization, lcs, 0/1 knapsack, recurrence
---

# Dynamic Programming: Knapsack & LCS

DP solves problems with overlapping subproblems by storing answers instead of recomputing. The 0/1 knapsack and longest-common-subsequence are the canonical patterns: build a table iteratively, or memoize a recursive function. The 1D knapsack loop must iterate capacity *downward* so each item is used at most once.

```java
import java.util.*;

public class DynamicProgramming {
    // 0/1 knapsack: max value you can carry with `capacity` weight
    static int knapsack(int[] weights, int[] values, int capacity) {
        int n = values.length;
        int[] dp = new int[capacity + 1];
        for (int i = 0; i < n; i++) {
            for (int w = capacity; w >= weights[i]; w--) { // downward!
                dp[w] = Math.max(dp[w], dp[w - weights[i]] + values[i]);
            }
        }
        return dp[capacity];
    }

    // longest common subsequence length
    static int lcs(String a, String b) {
        int m = a.length(), n = b.length();
        int[][] dp = new int[m + 1][n + 1];
        for (int i = 1; i <= m; i++) {
            for (int j = 1; j <= n; j++) {
                dp[i][j] = (a.charAt(i - 1) == b.charAt(j - 1))
                    ? dp[i - 1][j - 1] + 1
                    : Math.max(dp[i - 1][j], dp[i][j - 1]);
            }
        }
        return dp[m][n];
    }

    // memoized version of the same recurrence
    static int lcsMemo(String a, String b) {
        int[][] memo = new int[a.length() + 1][b.length() + 1];
        for (int[] row : memo) Arrays.fill(row, -1);
        return lcsRec(a, a.length(), b, b.length(), memo);
    }

    static int lcsRec(String a, int i, String b, int j, int[][] memo) {
        if (i == 0 || j == 0) return 0;
        if (memo[i][j] != -1) return memo[i][j];
        int res;
        if (a.charAt(i - 1) == b.charAt(j - 1)) res = 1 + lcsRec(a, i - 1, b, j - 1, memo);
        else res = Math.max(lcsRec(a, i - 1, b, j, memo), lcsRec(a, i, b, j - 1, memo));
        return memo[i][j] = res;
    }

    public static void main(String[] args) {
        int[] w = {2, 3, 4, 5};
        int[] v = {3, 4, 5, 6};
        System.out.println("knapsack(5) = " + knapsack(w, v, 5)); // {3,2} -> 7
        System.out.println("lcs = " + lcs("ABCBDAB", "BDCABA"));  // "BCBA" -> 4
        System.out.println("lcs memo = " + lcsMemo("ABCBDAB", "BDCABA"));
    }
}
```

Gotchas:
- The 0/1 knapsack inner loop MUST run capacity downward; running it upward turns it into the *unbounded* knapsack where items repeat.
- Base cases: dp[0] = 0 and dp[i][0] = dp[0][j] = 0 — forget them and indexes go negative.
- Memoization tables must have a "not computed" sentinel; `0` is ambiguous if 0 is a valid answer — use `-1`.
- Order of the two LCS strings doesn't change the answer, but `m`/`n` indexing must be consistent or you get off-by-one.
- DP gives the *value*; reconstructing the actual subset/subsequence needs a back-pointer/decision table.
- Integer overflow: sums of weights/values can exceed `int` — size `dp` with `long` when ranges are large.
