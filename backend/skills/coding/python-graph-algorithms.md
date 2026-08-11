---
lang: python
keywords: graph, bfs, dfs, dijkstra, shortest path, adjacency, traversal, heap, queue, algorithm
---

# Graph traversal and shortest paths: BFS, DFS, Dijkstra

For networks, mazes, and dependency graphs: BFS finds shortest paths in unweighted graphs,
DFS explores/serializes structure, and Dijkstra handles weighted graphs. All three are ~15
lines once you model the graph as an adjacency dict.

```python
import heapq
from collections import deque

graph = {
    "A": {"B": 4, "C": 1},
    "B": {"A": 4, "D": 1},
    "C": {"A": 1, "B": 2, "D": 5},
    "D": {"B": 1, "C": 5},
}

def bfs(start: str, goal: str) -> list[str] | None:
    """Unweighted shortest path (fewest edges)."""
    queue = deque([start])
    prev = {start: None}
    while queue:
        node = queue.popleft()
        if node == goal:
            path = []
            while node is not None:
                path.append(node)
                node = prev[node]
            return path[::-1]
        for nxt in graph[node]:
            if nxt not in prev:
                prev[nxt] = node
                queue.append(nxt)
    return None

def dfs(start: str) -> list[str]:
    seen = set()
    def visit(node: str) -> None:
        if node in seen:
            return
        seen.add(node)
        for nxt in graph[node]:
            visit(nxt)
    visit(start)
    return list(seen)

def dijkstra(start: str, goal: str) -> tuple[int, list[str]]:
    dist = {node: float("inf") for node in graph}
    prev: dict[str, str | None] = {start: None}
    dist[start] = 0
    pq = [(0, start)]
    while pq:
        d, node = heapq.heappop(pq)
        if node == goal:
            path = []
            while node is not None:
                path.append(node)
                node = prev[node]
            return d, path[::-1]
        if d > dist[node]:                   # stale heap entry
            continue
        for nxt, weight in graph[node].items():
            nd = d + weight
            if nd < dist[nxt]:
                dist[nxt] = nd
                prev[nxt] = node
                heapq.heappush(pq, (nd, nxt))
    return -1, []

print("bfs:", bfs("A", "D"))
print("dfs:", dfs("A"))
print("dijkstra:", dijkstra("A", "D"))
```

Gotchas:
- Use `deque` + `popleft` for BFS and `list.pop()` for DFS — using the wrong one turns the
  algorithm into the other and gives wrong shortest paths.
- BFS must mark a node visited when it's *enqueued*, not when dequeued, or a node enters the
  queue twice and the path reconstruction breaks.
- Dijkstra's `if d > dist[node]: continue` skips stale heap entries; without it, outdated
  distances reprocess neighbors and the algorithm degrades or corrupts.
- Dijkstra fails with negative edge weights — reach for Bellman-Ford or SPFA there.
- A `heapq` entry can't be updated in place; push a new `(dist, node)` and let the stale one get skipped.
- Represent missing edges as absent dict keys, not `inf` values, or `graph[node]` iterates edges that don't exist.
