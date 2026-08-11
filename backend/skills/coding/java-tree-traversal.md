---
lang: java
keywords: tree, binary search tree, bst, inorder, preorder, traversal, recursion, insert
---

# Binary Trees, BSTs & Traversals

A BST keeps left < node < right, so in-order traversal yields sorted order. Implement insert/contains recursively for clarity, and know both the recursive and iterative traversal patterns — iterative matters when the tree is deep enough to overflow the call stack.

```java
import java.util.*;

public class TreeTraversal {
    record Node(int value, Node left, Node right) {}

    // functional-style insert: returns the (possibly new) root
    static Node insert(Node root, int value) {
        if (root == null) return new Node(value, null, null);
        if (value < root.value()) return new Node(root.value(), insert(root.left(), value), root.right());
        if (value > root.value()) return new Node(root.value(), root.left(), insert(root.right(), value));
        return root; // duplicate — no-op
    }

    static boolean contains(Node root, int value) {
        if (root == null) return false;
        if (root.value() == value) return true;
        return value < root.value()
            ? contains(root.left(), value)
            : contains(root.right(), value);
    }

    static List<Integer> inOrder(Node n, List<Integer> acc) {
        if (n != null) {
            inOrder(n.left(), acc);
            acc.add(n.value());
            inOrder(n.right(), acc);
        }
        return acc;
    }

    static List<Integer> inOrderIterative(Node root) {
        List<Integer> out = new ArrayList<>();
        ArrayDeque<Node> stack = new ArrayDeque<>();
        Node cur = root;
        while (cur != null || !stack.isEmpty()) {
            while (cur != null) {          // go left as far as possible
                stack.push(cur);
                cur = cur.left();
            }
            cur = stack.pop();
            out.add(cur.value());          // visit
            cur = cur.right();             // then right
        }
        return out;
    }

    static List<List<Integer>> levelOrder(Node root) {
        List<List<Integer>> out = new ArrayList<>();
        ArrayDeque<Node> queue = new ArrayDeque<>();
        if (root != null) queue.add(root);
        while (!queue.isEmpty()) {
            List<Integer> level = new ArrayList<>();
            int size = queue.size();       // snapshot: exactly one level per pass
            for (int i = 0; i < size; i++) {
                Node n = queue.poll();
                level.add(n.value());
                if (n.left() != null) queue.add(n.left());
                if (n.right() != null) queue.add(n.right());
            }
            out.add(level);
        }
        return out;
    }

    public static void main(String[] args) {
        Node root = null;
        for (int v : new int[]{8, 3, 10, 1, 6, 14}) root = insert(root, v);
        System.out.println("in-order:   " + inOrder(root, new ArrayList<>()));
        System.out.println("iterative:  " + inOrderIterative(root));
        System.out.println("level-order:" + levelOrder(root));
        System.out.println("contains 6: " + contains(root, 6));
    }
}
```

Gotchas:
- A BST built from sorted input degenerates into a linked list (O(n) lookups) — use a self-balancing tree (`TreeMap`, AVL, Red-Black) when input order is adversarial.
- The level-order BFS must snapshot `queue.size()` *before* draining the level; reading it inside the loop counts new children too.
- `null` handling: every traversal checks `n != null` before recursing — one missing guard is an instant NPE.
- In-order of a BST is sorted, but pre-order/post-order are not — use in-order unless the problem is about copy/serialization.
- Recursive traversals overflow on deep trees; the iterative stack version above avoids it but needs care with the "go left, visit, go right" order.
- Duplicate handling is a design decision: allow, reject, or store counts — pick one and document it (the code above rejects silently).
