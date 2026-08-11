---
lang: java
keywords: stringbuilder, string format, formatted, printf, padding, concatenation, append, formatter, locale
---

# StringBuilder & String Formatting

`String` is immutable — building strings with `+=` in a loop is O(n^2). Use `StringBuilder.append` for accumulation and `String.format`/`formatted()` for printf-style layouts (width, padding, precision). `StringBuilder` is also the right tool to assemble CSV, logs, and protocol payloads.

```java
import java.util.*;

public class StringFormatting {
    public static void main(String[] args) {
        // StringBuilder: the loop-safe accumulator
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < 5; i++) {
            sb.append("item").append(i).append(", ");
        }
        if (sb.length() > 0) sb.setLength(sb.length() - 2); // strip trailing ", "
        System.out.println(sb);

        // printf-style formatting
        String msg = String.format("id=%04d price=%.2f rate=%d%%", 42, 9.5, 7);
        System.out.println(msg);

        // formatted() — Java 15+, the modern inline form
        System.out.println("%s has %d apples".formatted("Ada", 3));

        // width, alignment, and grouping
        System.out.println(String.format("[%-10s][%10s]", "left", "right"));
        System.out.println(String.format(Locale.US, "%,.2f", 1_234_567.891));

        // numbers in other radices
        System.out.println(String.format("255=%X binary=%s", 255, Integer.toBinaryString(255)));

        // measure the loop difference
        long t = System.nanoTime();
        String s = "";
        for (int i = 0; i < 20_000; i++) s += "x";  // O(n^2), okay for demo only
        System.out.println("+= build ms: " + (System.nanoTime() - t) / 1_000_000);
    }
}
```

Gotchas:
- `s += x` in a loop creates a new `String` per iteration (O(n^2)); pre-size the `StringBuilder` (`new StringBuilder(expected)`) when you know the size.
- `String.format` is locale-sensitive for numbers — pass a `Locale` explicitly or comma-grouping and decimal separators surprise you (`Locale.US`).
- `%d` fails on `double`, `%f` on `int` — mismatched specifiers throw `IllegalFormatConversionException`.
- `String.format` uses `Formatter` under the hood and is slow-ish — in hot loops concatenate or use `StringBuilder`.
- `setLength(0)` clears a `StringBuilder`; there is no `clear()` — forgetting this reuses stale content.
- `toString()` of a large `StringBuilder` copies the buffer — design around it for repeated big builds. And `%n` produces `\r\n` on Windows, breaking line-based protocols expecting `\n`.
