---
lang: java
keywords: graph, bfs, dfs, dijkstra, adjacency list, shortest path, breadth first, depth first
---

# Graph Algorithms: BFS, DFS, Dijkstra

Model graphs as an adjacency list (`Map<node, List<neighbor>>`) and pick the search by the question: BFS for shortest paths on unweighted graphs, DFS for connectivity/cycles/topological order, and Dijkstra (with a priority queue) for non-negative weighted shortest paths. Mark nodes visited *on enqueue* to avoid duplicates.

```java
import java.util.*;

public class GraphAlgorithms {
    record Edge(String to, int weight) {}

    static Map<String, List<Edge>> buildGraph() {
        Map<String, List<Edge>> g = new HashMap<>();
        addUndirected(g, "A", "B", 4);
        addUndirected(g, "A", "C", 1);
        addUndirected(g, "C", "B", 2);
        addUndirected(g, "B", "D", 1);
        addUndirected(g, "C", "D", 5);
        addUndirected(g, "D", "E", 3);
        return g;
    }

    static void addUndirected(Map<String, List<Edge>> g, String from, String to, int w) {
        g.computeIfAbsent(from, k -> new ArrayList<>()).add(new Edge(to, w));
        g.computeIfAbsent(to, k -> new ArrayList<>()).add(new Edge(from, w));
    }

    static List<String> bfs(Map<String, List<Edge>> g, String start) {
        List<String> order = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        ArrayDeque<String> queue = new ArrayDeque<>();
        queue.add(start);
        seen.add(start); // mark ON ENQUEUE, or a node is processed twice
        while (!queue.isEmpty()) {
            String cur = queue.poll();
            order.add(cur);
            for (Edge e : g.getOrDefault(cur, List.of())) {
                if (seen.add(e.to())) queue.add(e.to());
            }
        }
        return order;
    }

    static void dfs(Map<String, List<Edge>> g, String node, Set<String> seen, List<String> out) {
        seen.add(node);
        out.add(node);
        for (Edge e : g.getOrDefault(node, List.of())) {
            if (!seen.contains(e.to())) dfs(g, e.to(), seen, out);
        }
    }

    static Map<String, Integer> dijkstra(Map<String, List<Edge>> g, String start) {
        Map<String, Integer> dist = new HashMap<>();
        for (String v : g.keySet()) dist.put(v, Integer.MAX_VALUE);
        dist.put(start, 0);
        PriorityQueue<Edge> pq = new PriorityQueue<>(Comparator.comparingInt(Edge::weight));
        pq.add(new Edge(start, 0));
        while (!pq.isEmpty()) {
            Edge cur = pq.poll();
            if (cur.weight() > dist.get(cur.to())) continue; // stale entry
            for (Edge e : g.getOrDefault(cur.to(), List.of())) {
                int nd = dist.get(cur.to()) + e.weight();
                if (nd < dist.get(e.to())) {
                    dist.put(e.to(), nd);
                    pq.add(new Edge(e.to(), nd)); // may enqueue duplicates — that's fine
                }
            }
        }
        return dist;
    }

    public static void main(String[] args) {
        Map<String, List<Edge>> g = buildGraph();
        System.out.println("BFS: " + bfs(g, "A"));
        List<String> dfsOrder = new ArrayList<>();
        dfs(g, "A", new HashSet<>(), dfsOrder);
        System.out.println("DFS: " + dfsOrder);
        System.out.println("Dijkstra from A: " + dijkstra(g, "A"));
    }
}
```

Gotchas:
- Mark visited when you *enqueue* in BFS, not when you *dequeue* — dequeue-marking can push a node into the queue twice.
- Dijkstra only works with non-negative edge weights; negative edges need Bellman-Ford.
- Skipping stale priority-queue entries (`if (cur.weight() > dist.get(...)) continue`) is required or the algorithm is wrong/slow.
- Recursive DFS overflows the stack on deep graphs — convert to an explicit stack (or an iterative `ArrayDeque`).
- A disconnected graph: BFS/DFS from one start won't reach everything — loop over all nodes to find components.
- `Map.get` on a missing node returns null — use `getOrDefault(node, List.of())` so a graph with no outgoing edges doesn't NPE.
