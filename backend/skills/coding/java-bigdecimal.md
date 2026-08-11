---
lang: java
keywords: bigdecimal, currency, money, rounding, scale, RoundingMode, compareTo, arithmetic
---

# BigDecimal & Money

Binary floating point (`double`) can't represent decimal fractions exactly — `0.1 + 0.2 != 0.3`. For money and exact decimal math use `BigDecimal` constructed from *strings*, always specify `scale` and `RoundingMode`, and compare with `compareTo` (not `equals`, which also compares scale).

```java
import java.math.*;
import java.text.NumberFormat;
import java.util.Locale;

public class BigDecimalDemo {
    public static void main(String[] args) {
        // the classic double trap
        System.out.println("double: " + (0.1 + 0.2)); // 0.30000000000000004

        // from STRINGS, never from double
        BigDecimal x = new BigDecimal("0.10");
        BigDecimal y = new BigDecimal("0.20");
        System.out.println("decimal: " + x.add(y)); // 0.30

        // scale + RoundingMode must be explicit
        BigDecimal price = new BigDecimal("19.995");
        System.out.println("half-up:   " + price.setScale(2, RoundingMode.HALF_UP));
        System.out.println("half-even: " + price.setScale(2, RoundingMode.HALF_EVEN));

        BigDecimal twoFive = new BigDecimal("2.5");
        System.out.println("2.5 half-up -> " + twoFive.setScale(0, RoundingMode.HALF_UP));   // 3
        System.out.println("2.5 half-even -> " + twoFive.setScale(0, RoundingMode.HALF_EVEN)); // 2

        // equals vs compareTo — scale matters to equals
        BigDecimal a = new BigDecimal("1.0");
        BigDecimal b = new BigDecimal("1.00");
        System.out.println("equals: " + a.equals(b) + " compareTo: " + a.compareTo(b));

        // divide of a non-terminating result REQUIRES scale+mode
        BigDecimal ten = new BigDecimal("10");
        System.out.println("10/3 = " + ten.divide(new BigDecimal("3"), 4, RoundingMode.HALF_UP));

        // totals for display
        BigDecimal total = x.add(y);
        System.out.println(NumberFormat.getCurrencyInstance(Locale.US).format(total));
    }
}
```

Gotchas:
- Never `new BigDecimal(0.1)` — that constructs the exact binary value `0.1000000000000000055511151231257827...`; always parse a `String`.
- `equals` compares scale too (`1.0` != `1.00`); for numeric comparison use `compareTo`, and for maps/sets decide which semantics you want.
- `divide` on non-terminating division (e.g., 10/3) throws `ArithmeticException` unless you pass a scale and `RoundingMode`.
- `setScale` can *increase* scale (padding zeros) or round — both are legal, but increasing scale silently is usually not what you wanted.
- `HALF_EVEN` (banker's rounding) vs `HALF_UP`: the difference only shows on exact `.5` values — pick one policy and apply it everywhere.
- Tax/currency rounding should happen ONCE at the end, not per operation, or intermediate rounding compounds error. And keep money as integer cents *or* `BigDecimal` — mixing with `double` re-introduces the precision loss.
