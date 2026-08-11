---
lang: java
keywords: exception, custom exception, exception hierarchy, throw, catch, checked, runtime, rethrow, error handling
---

# Custom Exception Hierarchy

Model failure modes with a typed exception hierarchy: one base `RuntimeException` for the whole domain, with specific subclasses per condition. Callers can then catch narrowly (retry a `MissingSettingException`) or broadly (any `ConfigException`) without string-matching messages.

```java
public class CustomExceptions {
    // base exception for the whole config domain
    static class ConfigException extends RuntimeException {
        public ConfigException(String message) { super(message); }
        public ConfigException(String message, Throwable cause) { super(message, cause); }
    }

    static class MissingSettingException extends ConfigException {
        public MissingSettingException(String key) {
            super("Missing required setting: " + key);
        }
    }

    static class InvalidSettingException extends ConfigException {
        public InvalidSettingException(String key, String value) {
            super("Invalid value '" + value + "' for setting: " + key);
        }
    }

    static String loadSetting(String key, String value) {
        if (value == null) throw new MissingSettingException(key);
        if (value.isBlank()) throw new InvalidSettingException(key, value);
        return value;
    }

    public static void main(String[] args) {
        try {
            loadSetting("db.host", null);
        } catch (MissingSettingException e) {
            System.out.println("caught specific: " + e.getMessage());
        }

        try {
            loadSetting("db.port", "   ");
        } catch (ConfigException e) {
            System.out.println("caught base: " + e.getMessage());
        }

        // the base type is still catchable at the top boundary
        try {
            loadSetting("db.port", "   ");
        } catch (RuntimeException e) {
            System.out.println("bubbled as: " + e.getClass().getSimpleName());
        }
    }
}
```

Gotchas:
- Extend `RuntimeException` for programming/config errors so callers aren't forced to declare them; extend `Exception` only for recoverable checked conditions like I/O.
- Include the failing *key/field/value* in the message — a bare "failed" message is useless in logs.
- Always offer a `(String, Throwable)` constructor and pass the cause, or the root cause vanishes from the stack trace.
- Don't catch `Exception`/`Throwable` at the top unless you rethrow; swallowing `OutOfMemoryError` or `InterruptedException` breaks the app.
- Throwing inside `try`/`finally`: if `finally` also throws, it replaces the original exception — close resources with try-with-resources to avoid this.
- `catch` ordering matters: catch the most specific subclass first, or the narrower catch is unreachable.
