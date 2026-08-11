---
lang: python
keywords: linked list, stack, queue, deque, node, data structure, traversal, push, pop, LIFO, FIFO
---

# Linked list, stack, and queue in Python

Understand the classic containers on top of the language's built-ins: a singly linked list for
insert/delete-heavy sequences, `collections.deque` for O(1) stack and queue operations.
`deque` is the production answer; build the linked list to learn pointer discipline.

```python
from collections import deque
from dataclasses import dataclass
from typing import Optional


@dataclass
class Node:
    value: int
    next: Optional["Node"] = None


class LinkedList:
    def __init__(self):
        self.head: Optional[Node] = None

    def append(self, value: int) -> None:
        if self.head is None:
            self.head = Node(value)
            return
        node = self.head
        while node.next is not None:
            node = node.next
        node.next = Node(value)

    def values(self) -> list[int]:
        out = []
        node = self.head
        while node is not None:
            out.append(node.value)
            node = node.next
        return out


lst = LinkedList()
for v in (1, 2, 3):
    lst.append(v)
print(lst.values())

# Stack  (LIFO)
stack = deque()
stack.append("a")            # push
stack.append("b")
print(stack.pop())           # 'b'

# Queue (FIFO)
queue = deque()
queue.append("x")            # enqueue
queue.append("y")
print(queue.popleft())       # 'x'
```

Gotchas:
- `deque` is the right stack/queue in production: `append`/`pop` and `appendleft`/`popleft`
  are all O(1). A `list` used as a queue is O(n) on `pop(0)`.
- Traversal must stop *before* `None`: `while node.next is not None` reads one ahead; a typo
  like `while node.next:` with the last node still set can walk off the end.
- A `@dataclass` Node is mutable and recurses (`Node.next` points to `Node`) — fine here, but
  `==` on two lists compares node-by-node, not value equality, so implement `__eq__` if needed.
- Linked-list cycles (a node pointing back) make `values()` loop forever — add a visited set or
  a length cap when processing untrusted structures.
- `collections.deque` with `maxlen=N` auto-drops the oldest element at the other end — useful
  for rolling buffers of the last N events.
- When using `deque` as a queue across threads, prefer `queue.Queue` which blocks and is
  thread-safe by design.
