---
lang: javascript
keywords: queue, stack, deque, FIFO, LIFO, circular buffer, linked list, array shift, enqueue dequeue, performance, data structure
---

# Queue & stack implementations

A stack is LIFO (push/pop at the end), a queue is FIFO (push at end, pop at front). Native arrays do stacks perfectly, but `array.shift()` makes naive queues O(n) — implement a head-index queue or a linked list for O(1) both ends.

```javascript
// Stack: array push/pop is already O(1)
class Stack {
  #items = [];
  push(v) { this.#items.push(v); }
  pop() { return this.#items.pop() ?? null; }
  peek() { return this.#items.at(-1) ?? null; }
  get size() { return this.#items.length; }
}
const stack = new Stack();
stack.push(1); stack.push(2);
console.log(stack.pop(), stack.pop(), stack.pop());  // 2 1 null

// Queue with head index: O(1) amortized dequeue
class Queue {
  #items = [];
  #head = 0;
  enqueue(v) { this.#items.push(v); }
  dequeue() {
    if (this.#head >= this.#items.length) return null;
    const v = this.#items[this.#head];
    this.#items[this.#head++] = undefined;          // release reference
    if (this.#head > 1024 && this.#head * 2 > this.#items.length) {
      this.#items = this.#items.slice(this.#head);  // compact periodically
      this.#head = 0;
    }
    return v;
  }
  get size() { return this.#items.length - this.#head; }
}
const q = new Queue();
q.enqueue("a"); q.enqueue("b");
console.log(q.dequeue(), q.dequeue(), q.dequeue()); // a b null

// Deque with a doubly linked list (constant time both ends)
class Node {
  constructor(value) { this.value = value; this.next = null; this.prev = null; }
}
class Deque {
  #head = null; #tail = null; #len = 0;
  pushFront(v) {
    const n = new Node(v);
    n.next = this.#head;
    if (this.#head) this.#head.prev = n; else this.#tail = n;
    this.#head = n;
    this.#len++;
  }
  popBack() {
    if (!this.#tail) return null;
    const v = this.#tail.value;
    this.#tail = this.#tail.prev;
    if (this.#tail) this.#tail.next = null; else this.#head = null;
    this.#len--;
    return v;
  }
  get size() { return this.#len; }
}
const d = new Deque();
d.pushFront(1); d.pushFront(2);
console.log(d.popBack());                            // 1 (FIFO order from pushFront)
```

Gotchas:
- `Array.prototype.shift` is O(n) — on large queues it makes BFS/queues quadratic. Use the head-index or linked-list approach.
- A bare object as a queue (`q[k]=v; delete q[k]`) leaves key gaps and can't dedupe keys.
- The head-index queue must compact (re-slice) occasionally or memory grows forever with stale slots.
- Private fields (`#items`) keep internals safe but break `for...of` — add `[Symbol.iterator]` if callers should loop.
- Pop/push on empty containers: decide null vs throw; `??`/`?.` make null natural, but callers must check.
- For "most recent N" (LRU), a plain array is wrong — combine a Map (order) with a cap, or a linked list + hashmap.
