---
lang: java
keywords: lambda, method reference, functional, effectively final, sort comparator, replaceAll, predicate, unary operator
---

# Lambdas & Method References

Lambdas let you pass behavior as a value; method references (`ClassName::method`, `instance::method`) are compact alternatives when a lambda body is just one call. Reach for them with `sort`, `map`, `filter`, `forEach`, and custom `@FunctionalInterface`s.

```java
import java.util.*;
import java.util.function.*;

public class LambdasMethodRefs {
    public static void main(String[] args) {
        List<String> names = new ArrayList<>(List.of("ada", "grace", "linus"));

        // lambda with explicit parameter types
        names.sort((String a, String b) -> Integer.compare(a.length(), b.length()));

        // static method reference
        names.forEach(System.out::println);

        // unbound instance method reference (element becomes the receiver)
        names.replaceAll(String::toUpperCase);

        // bound instance method reference (captures an object)
        Runnable printList = names::toString;
        System.out.println(printList);

        // composition of predicates
        Predicate<String> shortName = s -> s.length() < 5;
        Predicate<String> shortStartsWithA = shortName.and(s -> s.startsWith("A"));
        System.out.println("ADA short? " + shortStartsWithA.test("ADA"));
        System.out.println("LINUS short? " + shortStartsWithA.test("LINUS"));

        // lambda capturing an effectively-final local
        int maxLen = 6;
        names.removeIf(s -> s.length() > maxLen);
        System.out.println(names);
    }
}
```

Gotchas:
- A lambda can only capture `final`/effectively-final locals; reassigning the captured variable is a compile error.
- `Function<String,String> f = String::toUpperCase;` is an *unbound* reference (arg becomes receiver); `object::method` is *bound*. Confusing the two breaks compilation.
- `replaceAll` needs `UnaryOperator<T>` (same type in/out); `map` on a stream is more general.
- Method references and lambdas desugar to lambdas via `invokedynamic`; referencing `this` inside a lambda refers to the enclosing class, not the lambda.
- `Comparator.comparing(field)` with primitive accessors uses autoboxing-free comparators — prefer `comparingInt/comparingDouble` in hot paths.
