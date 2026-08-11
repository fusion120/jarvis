---
lang: java
keywords: args, command line, stdin, scanner, parse, main arguments, system.getenv, cli
---

# CLI Args & stdin Parsing

`main(String[] args)` is a raw array of space-separated tokens; parse `--key value` and `-flag` forms yourself or use picocli/Commons CLI. For interactive input, `Scanner` over `System.in` reads lines or tokens; environment variables via `System.getenv` are the standard place for machine-specific config.

```java
import java.util.*;

public class CliArgs {
    public static void main(String[] args) {
        // minimal --key value / -flag parser
        Map<String, String> opts = new LinkedHashMap<>();
        List<String> positional = new ArrayList<>();
        for (int i = 0; i < args.length; i++) {
            String a = args[i];
            if (a.startsWith("--") && i + 1 < args.length) {
                opts.put(a.substring(2), args[++i]);   // --name value
            } else if (a.startsWith("-")) {
                opts.put(a.substring(1), "true");       // -verbose flag
            } else {
                positional.add(a);
            }
        }
        System.out.println("opts=" + opts);
        System.out.println("positional=" + positional);

        // environment variables as config fallback
        String home = System.getenv("HOME");
        System.out.println("HOME=" + home);

        // read stdin line by line (ctrl-Z on Windows / ctrl-D on Unix to end)
        Scanner sc = new Scanner(System.in);
        System.out.println("type lines; end with ctrl-z/ctrl-d:");
        int total = 0;
        while (sc.hasNextLine()) {
            String line = sc.nextLine();
            total += line.length();
            System.out.println("read " + line.length() + " chars");
        }
        System.out.println("total chars: " + total);
    }
}
```

Gotchas:
- `args` are strings — convert every numeric value yourself; `Integer.parseInt` throws `NumberFormatException` on junk input (catch and print usage).
- A `--flag` with no following value can't be distinguished from a flag plus next argument by the simple parser — decide your grammar (`--flag=true` vs `--flag value`) and document it.
- `Scanner.nextInt()` after `nextLine()` skips — `nextLine()` after any `nextX()` consumes the leftover newline; mix token and line reads carefully (or use only lines).
- `System.in` may be closed/redirected (piped input); `hasNextLine()` returning false is normal at EOF, not an error.
- Windows uses `\r\n` line endings — `nextLine()` strips them, but if you read raw bytes you must handle `\r`.
- Use `System.getProperty` for JVM flags (`-Dkey=value`) and `System.getenv` for OS variables — different namespaces, both common pitfalls. For serious CLIs, use picocli/JCommander/Commons CLI; hand-rolled parsing breaks on quoted args and `--`.
