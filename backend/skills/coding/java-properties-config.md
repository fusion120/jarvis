---
lang: java
keywords: properties, config, .properties, load, store, getProperty, defaults, environment
---

# Config with java.util.Properties

`Properties` is the JDK's built-in key/value config store: `load` from a file or stream, `store` back, and layer *defaults* so missing keys fall back gracefully. Reach for it for simple non-secret config; keep secrets out of files entirely.

```java
import java.io.*;
import java.nio.file.*;
import java.util.*;

public class PropertiesConfig {
    public static void main(String[] args) throws IOException {
        Path f = Files.createTempFile("app", ".properties");

        // write config out
        Properties out = new Properties();
        out.setProperty("db.url", "jdbc:h2:mem:prod");
        out.setProperty("db.user", "sa");
        out.setProperty("retry.max", "3");
        try (OutputStream os = Files.newOutputStream(f)) {
            out.store(os, "app configuration"); // timestamp comment header
        }

        // load with a defaults layer — missing keys fall back
        Properties defaults = new Properties();
        defaults.setProperty("retry.max", "1");
        defaults.setProperty("log.level", "INFO");
        Properties cfg = new Properties(defaults);
        try (InputStream is = Files.newInputStream(f)) {
            cfg.load(is); // ISO-8859-1 unless you use load(Reader) with UTF-8
        }

        System.out.println("db.url=" + cfg.getProperty("db.url"));
        System.out.println("retry.max (from file)=" + cfg.getProperty("retry.max"));
        System.out.println("log.level (default)=" + cfg.getProperty("log.level"));
        System.out.println("missing with inline fallback=" + cfg.getProperty("nope", "fallback"));

        // numeric settings come back as strings — parse explicitly
        int retries = Integer.parseInt(cfg.getProperty("retry.max"));
        System.out.println("parsed retries=" + retries);
    }
}
```

Gotchas:
- `Properties` is effectively a `Hashtable<Object,Object>` — a non-String key/value compiles silently and then breaks `store`/`getProperty`; keep it string-typed.
- `load(InputStream)` reads ISO-8859-1 only; UTF-8 content needs `load(new InputStreamReader(is, StandardCharsets.UTF_8))`.
- `store` writes a timestamp comment by default — non-deterministic output that churns VCS diffs; the comment is optional if you want clean diffs.
- All values are strings — parse `int`/`boolean` yourself; an unparsable value throws `NumberFormatException` at runtime, not load time.
- Defaults live in the *second* `Properties` you pass — missing keys consult it, but `keys()`/`entrySet()` won't show defaulted keys.
- Never put passwords/API keys in `.properties` — use environment variables or a secret manager, and don't commit the file. And `getProperty` returns `null` for missing keys; decide the default/fallback behavior before using it.
