---
lang: java
keywords: generics, wildcard, bounded type, PECS, extends, super, type parameter, generic method, type safety
---

# Generics: Bounded Types & Wildcards

Bounded type parameters (`<T extends Comparable<? super T>>`) constrain what a type variable can be; wildcards (`? extends T` producer / `? super T` consumer) make generic APIs flexible. Use PECS: `? extends` when you only read, `? super` when you only write.

```java
import java.util.*;

public class GenericsWildcards {
    // producer wildcard: we read Numbers out of the collection
    static double sum(Collection<? extends Number> nums) {
        double total = 0;
        for (Number n : nums) total += n.doubleValue();
        return total;
    }

    // consumer wildcard: we put Integers into the collection
    static void addAll(Collection<? super Integer> dst, Integer... vals) {
        for (Integer v : vals) dst.add(v);
    }

    // bounded type parameter with recursive bound
    static <T extends Comparable<? super T>> T max(List<? extends T> list) {
        Iterator<? extends T> it = list.iterator();
        T max = it.next();
        while (it.hasNext()) {
            T cur = it.next();
            if (cur.compareTo(max) > 0) max = cur;
        }
        return max;
    }

    public static void main(String[] args) {
        System.out.println("sum=" + sum(List.of(1, 2.5, 3L)));

        List<Number> nums = new ArrayList<>();
        addAll(nums, 1, 2, 3); // Integer goes into Collection<? super Integer>
        System.out.println(nums);

        System.out.println("max=" + max(List.of("apple", "banana", "cherry")));
    }
}
```

Gotchas:
- `List<Object>` is NOT a supertype of `List<String>`; `List<?>` is their common supertype — wildcards exist exactly to bridge this.
- With `? extends`, the collection is read-only in practice (`add` won't compile); with `? super`, you can write but reads come back as `Object`.
- `? extends Number` accepts `Integer` and `Double`, but the element type is `Number` — you can't add an `Integer` to a `List<? extends Number>`.
- Raw types (`List` without type args) silently break type safety; never use them in new code.
- Two type arguments must be unrelated if they use the same variable: `<T> void f(List<T>, List<T>)` requires both lists to share the exact type.
- Arrays and generics don't mix: `new T[10]` and `List<String>[]` don't compile — use `List<T>` or `(T[]) new Object[n]`.
