---
lang: java
keywords: sealed class, sealed interface, permits, pattern switch, exhaustive, restricted hierarchy, non-sealed, closed hierarchy
---

# Sealed Classes & Exhaustive Switches

`sealed` restricts who may extend an interface/class to an explicit list in `permits`, giving the compiler a closed set of subtypes. Combine sealed types with pattern-matching `switch` (Java 21+) to get exhaustive, checked dispatch — the compiler errors if a new subtype is added but not handled.

```java
// Requires Java 17+ for sealed, Java 21+ for the pattern switch below
public class SealedShapes {
    sealed interface Shape permits Circle, Rectangle {}

    record Circle(double radius) implements Shape {
        double area() { return Math.PI * radius * radius; }
    }

    record Rectangle(double width, double height) implements Shape {
        double area() { return width * height; }
    }

    // exhaustive switch: no default needed, compiler verifies all permits
    static String describe(Shape s) {
        return switch (s) {
            case Circle c -> "circle r=" + c.radius() + " area=" + c.area();
            case Rectangle r -> "rect " + r.width() + "x" + r.height();
        };
    }

    static double area(Shape s) {
        return switch (s) {
            case Circle c -> c.area();
            case Rectangle r -> r.area();
        };
    }

    public static void main(String[] args) {
        Shape s = new Circle(2);
        System.out.println(describe(s));
        System.out.println("area=" + area(s));
    }
}
```

Gotchas:
- Every permitted subtype must be declared in the same module (or package for unnamed modules) and must directly extend the sealed parent.
- Permitted subclasses must themselves be `final`, `sealed`, or `non-sealed` — an ordinary class cannot extend a sealed type.
- Omitting `default` in a switch over a sealed type is only legal if the switch is exhaustive over the permits and is a statement/expression with pattern labels.
- A `sealed` type that permits nested records must list them by simple name in `permits`; the nested types must be declared inside the same enclosing class.
- Sealed hierarchies don't stop reflection — `setAccessible` can still construct/override; they are a design tool, not a security boundary.
- `switch` pattern guards (`case Circle c && c.radius() > 0 -> ...`) are allowed, but guards cannot make a switch non-exhaustive.
