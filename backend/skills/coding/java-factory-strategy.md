---
lang: java
keywords: factory, strategy, design pattern, dependency injection, interface, switch expression, polymorphism, strategy pattern, factory method
---

# Factory & Strategy Patterns

The **strategy** pattern isolates an algorithm behind an interface so callers can swap behavior at runtime; the **factory** pattern centralizes which strategy to build. Together they replace if/else chains over "type" strings with polymorphism — adding a new strategy means a new class, not a new branch.

```java
import java.util.*;

public class FactoryStrategy {
    // strategy interface
    interface Pricer {
        double price(double base);
    }

    static final class StandardPricer implements Pricer {
        public double price(double base) { return base; }
    }

    static final class DiscountPricer implements Pricer {
        private final double rate;
        DiscountPricer(double rate) { this.rate = rate; }
        public double price(double base) { return base * rate; }
    }

    // factory: the only place that knows how tiers map to strategies
    static Pricer forTier(String tier) {
        return switch (tier.toLowerCase(Locale.ROOT)) {
            case "vip" -> new DiscountPricer(0.8);
            case "member" -> new DiscountPricer(0.9);
            case "guest" -> new StandardPricer();
            default -> throw new IllegalArgumentException("unknown tier: " + tier);
        };
    }

    public static void main(String[] args) {
        double base = 100.0;
        for (String tier : List.of("vip", "member", "guest")) {
            Pricer pricer = forTier(tier);
            System.out.println(tier + " pays " + pricer.price(base));
        }
    }
}
```

Gotchas:
- Strategy objects that carry *no* state can be singletons — reusing one instance per strategy avoids per-call allocation.
- The factory's switch must stay exhaustive and fail loudly on unknown inputs (`IllegalArgumentException`), or an unseen tier silently gets wrong behavior.
- Strategies that need different construction args (like `DiscountPricer(0.8)`) can't be plain singletons — the factory is where that variance belongs.
- Expose strategies behind the *interface* type; leaking the concrete class into callers defeats the swap-ability.
- Don't over-apply: one algorithm with a boolean flag is simpler than two strategies; add the pattern when behavior genuinely varies.
- A registry-based factory (a `Map<String, Supplier<Pricer>>`) avoids modifying the factory when adding strategies, at the cost of startup registration. And make strategies stateless or thread-safe if shared across threads.
