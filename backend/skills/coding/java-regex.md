---
lang: java
keywords: regex, pattern, matcher, find, matches, group, replaceAll, Pattern.quote, validation
---

# Regex with Pattern & Matcher

Compile a `Pattern` once and reuse the `Matcher` for extracting groups, validating input, and doing group-aware replacement. `find()` scans for a match anywhere; `matches()` demands the whole input match. Always `Pattern.quote()` user-supplied regex text.

```java
import java.util.regex.*;

public class RegexDemo {
    public static void main(String[] args) {
        Pattern email = Pattern.compile("([\\w.+-]+)@([\\w-]+\\.[\\w.]+)");

        Matcher m = email.matcher("contact ada@example.com or grace@dev.io");
        while (m.find()) {
            System.out.println("user=" + m.group(1) + " domain=" + m.group(2));
        }

        // matches() = whole string; find() = substring
        System.out.println(Pattern.matches("\\d{3}-\\d{4}", "555-1234"));
        System.out.println("555-1234".matches("\\d{3}-\\d{4}")); // String.matches recompiles each call!

        // quote user input so regex metacharacters are literal
        String userInput = "a.b*c";
        Pattern literal = Pattern.compile(Pattern.quote(userInput));
        System.out.println("literal match: " + literal.matcher("xxa.b*cyy").find());

        // group backreferences in replacement
        String swapped = Pattern.compile("(\\w+)-(\\w+)")
            .matcher("first-last")
            .replaceAll("$2, $1");
        System.out.println(swapped);

        // named groups for readability
        Pattern named = Pattern.compile("(?<year>\\d{4})-(?<month>\\d{2})");
        Matcher nm = named.matcher("2026-08");
        if (nm.matches()) System.out.println(nm.group("year") + "/" + nm.group("month"));

        // flags: case-insensitive, multiline
        Pattern ci = Pattern.compile("^hello", Pattern.CASE_INSENSITIVE | Pattern.MULTILINE);
        System.out.println(ci.matcher("one\nHello\n").find());
    }
}
```

Gotchas:
- `String.matches()` recompiles the regex on every call — compile a `Pattern` and reuse it in loops and hot paths.
- `find()` vs `matches()`: `matches()` anchors to the whole input implicitly; forgetting this is the #1 "my regex doesn't match" bug.
- `group()` defaults to the entire match; `group(1)` is the first capture. Out-of-range group indexes throw `IndexOutOfBoundsException`.
- Quantifiers are greedy by default; add `?` for lazy, or `+` possessive — catastrophic backtracking (`(a+)+$` on long non-matching input) can hang the JVM.
- Metacharacters in user input (`.` `*` `(` etc.) silently change meaning — wrap with `Pattern.quote()`.
- Replacement strings treat `$1` specially — escape a literal `$` as `\$`. And never parse arbitrary HTML/JSON with regex; use a real parser.
