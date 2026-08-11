---
lang: java
keywords: logging, logger, java.util.logging, slf4j, log level, log record, file handler, log4j
---

# Logging with java.util.logging

`java.util.logging` (JUL) is built in: get a `Logger` per class, log at levels (SEVERE..FINE), attach handlers (console, file), and log exceptions with stack traces via `log(Level, msg, throwable)`. For library code, prefer slf4j so the host app can choose the backend.

```java
import java.util.logging.*;

public class LoggingDemo {
    private static final Logger LOG = Logger.getLogger(LoggingDemo.class.getName());

    public static void main(String[] args) {
        // simple leveled messages
        LOG.info("starting up");
        LOG.warning("disk nearly full");
        LOG.fine("this is hidden unless level is lowered");

        // log exceptions WITH stack traces — never just the message
        try {
            throw new IllegalStateException("boom");
        } catch (IllegalStateException e) {
            LOG.log(Level.SEVERE, "operation failed", e);
        }

        // add a file handler writing plain text
        try {
            FileHandler fh = new FileHandler("app.log", true); // append mode
            fh.setFormatter(new SimpleFormatter());
            Logger root = Logger.getLogger(""); // root logger
            root.addHandler(fh);
            LOG.info("file handler attached");
        } catch (java.io.IOException e) {
            LOG.log(Level.SEVERE, "could not create log file", e);
        }
    }
}
```

For slf4j-based code, the imports change to `org.slf4j.Logger` / `LoggerFactory`, and you add the dependency below (plus a backend such as logback-classic):

```xml
<dependency>
  <groupId>org.slf4j</groupId>
  <artifactId>slf4j-api</artifactId>
  <version>2.0.13</version>
</dependency>
```

Gotchas:
- Default root level is INFO — `FINE`/`FINER`/`FINEST` logs are dropped until you lower the level (`logger.setLevel(Level.FINE)` and the handler's level).
- String-concatenating log arguments computes the message even when the level is disabled — use `LOG.log(Level.FINE, "x={0}", value)` or slf4j `{}` placeholders.
- `System.out.println` for debugging doesn't give timestamps, levels, or thread names, and pollutes stdout — route through a logger.
- JUL `Logger.getLogger(String)` takes a name — the common convention is the class name, which yields a hierarchical namespace (`com.example.app`).
- Adding the same handler repeatedly (e.g., per-request) duplicates output — install handlers once at startup.
- `Logger.getLogger("")` is the root logger: raising its handler level affects *all* loggers below it, which can silently mute your app. And `FileHandler` doesn't rotate by default — use `FileHandler(pattern, limit, count)`.
