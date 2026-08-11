---
lang: java
keywords: weakreference, softreference, referencequeue, weakhashmap, garbage collection, caching, memory pressure, ephemeron
---

# Weak & Soft References

Garbage collection normally keeps every reachable object alive; `WeakReference` lets GC reclaim an object even while the reference exists (great for caches keyed by identity), `SoftReference` keeps it until memory pressure (great for big caches), and `ReferenceQueue` tells you when an object was collected. `WeakHashMap` applies the weak-key idea to a map.

```java
import java.lang.ref.*;
import java.util.*;

public class ReferenceDemo {
    public static void main(String[] args) throws Exception {
        // WeakHashMap: entry evaporates once the KEY is only weakly reachable
        WeakHashMap<Object, String> cache = new WeakHashMap<>();
        Object key = new Object();
        cache.put(key, "expensive-value");
        System.out.println("before gc: size=" + cache.size());
        key = null; // drop the strong reference
        gc();
        System.out.println("after gc:  size=" + cache.size()); // usually 0

        // SoftReference: cleared only under memory pressure
        SoftReference<byte[]> soft = new SoftReference<>(new byte[1024]);
        System.out.println("soft present: " + (soft.get() != null));
        soft.clear(); // or leave it; GC reclaims under pressure

        // ReferenceQueue reports collected objects
        ReferenceQueue<Object> queue = new ReferenceQueue<>();
        Object target = new Object();
        WeakReference<Object> wr = new WeakReference<>(target, queue);
        target = null;
        gc();
        Reference<?> reaped = queue.poll(); // non-null once collected
        System.out.println("reaped via queue: " + (reaped != null));
        System.out.println("referent cleared: " + (wr.get() == null));
    }

    static void gc() throws InterruptedException {
        for (int i = 0; i < 3; i++) { System.gc(); Thread.sleep(50); }
    }
}
```

Gotchas:
- `System.gc()` is only a *hint* — the JVM may ignore it; never write logic that depends on a specific GC timing (tests must tolerate both outcomes).
- `WeakReference.get()` can return null at any time between reads — check the result before using it, or you'll NPE on a reclaimed object.
- `WeakHashMap` is not thread-safe and its values hold strong refs to their keys' keys? No — values don't keep keys alive, but a value referencing its own key does keep it alive (ephemeron subtlety); design values to avoid back-references.
- Soft references linger until memory pressure, so "cache size" is unpredictable — combine with `ReferenceQueue` + explicit eviction for predictable caches.
- Strong references to a referent from elsewhere defeat weak collection entirely — the referent stays alive while any strong ref exists.
- `ReferenceQueue.poll()` is non-blocking — use `remove()` to wait in a background reaper thread. And call `clear()` explicitly when done with a big buffer so the referent is eligible immediately.
