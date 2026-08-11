---
lang: java
keywords: functional interface, predicate, function, supplier, consumer, unaryoperator, compose, method reference, andThen
---

# Functional Interfaces: Function, Predicate, Supplier, Consumer

`java.util.function` gives you the standard shapes: `Function<T,R>` (transform), `Predicate<T>` (test), `Supplier<T>` (produce), `Consumer<T>` (consume), plus `UnaryOperator`/`BinaryOperator` specializations. Write your own `@FunctionalInterface` when the shape is domain-specific, and compose with `andThen`/`compose`/`and`/`or`.

```java
import java.util.function.*;

public class FunctionalInterfaces {
    // custom functional interface with a default composition helper
    @FunctionalInterface
    interface Discount {
        double apply(double price);

        default Discount andThen(Discount next) {
            return price -> next.apply(apply(price));
        }
    }

    public static void main(String[] args) {
        // the four built-in shapes
        Function<String, Integer> length = String::length;
        Predicate<String> isLong = s -> s.length() > 5;
        Supplier<Double> random = Math::random;
        Consumer<String> log = System.out::println;

        System.out.println("length: " + length.apply("hello"));
        System.out.println("isLong: " + isLong.test("hello world"));
        log.accept("random=" + random.get());

        // primitives avoid boxing
        IntPredicate positive = n -> n > 0;
        System.out.println("positive: " + positive.test(-3));

        // composition
        Function<Integer, Integer> doubleIt = n -> n * 2;
        Function<Integer, Integer> plusOne = n -> n + 1;
        System.out.println("(x*2)+1: " + doubleIt.andThen(plusOne).apply(5)); // 11
        System.out.println("(x+1)*2: " + doubleIt.compose(plusOne).apply(5)); // 12

        // custom interface chaining
        Discount tenPercent = p -> p * 0.9;
        Discount fiveOff = p -> p - 5;
        Discount total = tenPercent.andThen(fiveOff);
        System.out.println("final price: " + total.apply(100.0)); // 85.0
    }
}
```

Gotchas:
- A `@FunctionalInterface` must have exactly one abstract method; a second abstract method breaks compilation (the annotation enforces it).
- `andThen` vs `compose`: `f.andThen(g)` is `g(f(x))`; `f.compose(g)` is `f(g(x))` — the two are mirror images and easy to mix up.
- Predicate has `and`/`or`/`negate`; Function has `compose`/`andThen`; neither has `andThen`-style chaining across different types without type gymnastics.
- The `Function.identity()` and `Predicate.not(x)` helpers exist — prefer them over hand-rolled no-ops.
- Using `Integer`/`Double` (boxed) generics in hot paths costs allocations — use the primitive `IntFunction`/`DoublePredicate` variants.
- Lambdas capturing non-final locals won't compile — capture effectively-final copies. Method references are *bound* (`obj::m`) or *unbound* (`Type::m`); an unbound ref expects the receiver as the first argument.
