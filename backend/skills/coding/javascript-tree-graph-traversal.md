---
lang: javascript
keywords: tree traversal, graph, BFS, DFS, depth first, breadth first, recursion, visited set, adjacency list, binary tree, cycle detection
---

# Tree & graph traversal

BFS and DFS walk nodes in breadth- or depth-first order. Use BFS for shortest paths / level order (it explores in layers), DFS for path existence, serialization, and topological problems. Track `visited` for graphs, not just trees.

```javascript
// Adjacency list graph
const graph = {
  A: ["B", "C"],
  B: ["A", "D", "E"],
  C: ["A", "F"],
  D: ["B"],
  E: ["B", "F"],
  F: ["C", "E"],
};

// BFS: shortest path (in edges) using a queue
function bfs(start, target) {
  const queue = [[start, 0]];
  const visited = new Set([start]);
  while (queue.length) {
    const [node, depth] = queue.shift();          // O(n) — see queue/stack file
    if (node === target) return depth;
    for (const next of graph[node] ?? []) {
      if (!visited.has(next)) {
        visited.add(next);
        queue.push([next, depth + 1]);
      }
    }
  }
  return -1;
}
console.log(bfs("A", "F"));                        // 2 (A -> C -> F)

// DFS recursive (path existence)
function dfs(node, target, seen = new Set()) {
  if (node === target) return true;
  if (seen.has(node)) return false;
  seen.add(node);
  return (graph[node] ?? []).some((n) => dfs(n, target, seen));
}
console.log(dfs("A", "F"));                        // true

// Binary tree: in-order traversal (BST property)
const tree = {
  value: 10,
  left: { value: 5, left: { value: 2 }, right: { value: 7 } },
  right: { value: 15, right: { value: 20 } },
};
function inOrder(node, out = []) {
  if (!node) return out;
  inOrder(node.left, out);
  out.push(node.value);
  inOrder(node.right, out);
  return out;
}
console.log(inOrder(tree));                        // [2,5,7,10,15,20] — sorted

// Cycle detection in a directed graph (3-state coloring)
function hasCycle(nodes, edges) {
  const adj = new Map(nodes.map((n) => [n, []]));
  for (const [a, b] of edges) adj.get(a).push(b);
  const state = new Map();                          // 1 = visiting, 2 = done
  const visit = (n) => {
    if (state.get(n) === 1) return true;            // back-edge -> cycle
    if (state.get(n) === 2) return false;
    state.set(n, 1);
    for (const next of adj.get(n) ?? []) if (visit(next)) return true;
    state.set(n, 2);
    return false;
  };
  return nodes.some(visit);
}
console.log(hasCycle(["A", "B"], [["A", "B"], ["B", "A"]])); // true
```

Gotchas:
- BFS with `array.shift()` is O(n) per dequeue — for big graphs use a real queue (head index or linked list) or BFS degrades.
- DFS recursion hits call-stack limits on deep graphs (~10k+ frames); switch to an explicit stack for huge trees.
- Graphs need a `visited`/`state` set or you loop forever — trees don't, which is why tree code omits it.
- In directed graphs, a single visited set can miss cycles reachable via a back-edge — use the 3-state coloring above.
- `graph[node]` on missing keys is `undefined` and `.some` throws — default to `graph[node] ?? []`.
- BFS gives shortest paths only on unweighted graphs; with weights you need Dijkstra.
- Mutating the tree while traversing (deleting nodes) can skip subtrees — collect deletions and apply after.
