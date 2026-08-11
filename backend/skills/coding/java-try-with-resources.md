---
lang: java
keywords: try with resources, AutoCloseable, close, suppressed exception, resource management, resource leak, finally close, try
---

# try-with-resources

`try (Resource r = ...)` closes every resource automatically in reverse order, and if both body and `close()` throw, the body's exception wins with the close failure attached as a *suppressed* exception. This eliminates the manual `finally`-close boilerplate and its error paths.

```java
import java.io.*;

public class TryWithResources {
    static final class Tail implements Closeable {
        private final String name;
        Tail(String name) { this.name = name; }
        public void close() { System.out.println("closing " + name); }
    }

    static final class ThrowingTail implements Closeable {
        public void close() throws IOException { throw new IOException("close failed"); }
    }

    public static void main(String[] args) throws IOException {
        // multiple resources close in reverse declaration order
        try (Tail a = new Tail("a"); Tail b = new Tail("b")) {
            System.out.println("body");
        }

        // writing a file without a finally
        File f = File.createTempFile("twr", ".txt");
        try (BufferedWriter w = new BufferedWriter(
                new OutputStreamWriter(new FileOutputStream(f), java.nio.charset.StandardCharsets.UTF_8))) {
            w.write("hello\n");
            w.write("world\n");
        }
        System.out.println("wrote " + f.length() + " bytes");

        // suppressed exceptions: close() failure doesn't mask the body failure
        try (ThrowingTail t = new ThrowingTail()) {
            throw new RuntimeException("main failure");
        } catch (RuntimeException e) {
            System.out.println("main: " + e.getMessage());
            System.out.println("suppressed count=" + e.getSuppressed().length);
        }
    }
}
```

Gotchas:
- Only variables declared *inside* the `try (...)` parens are auto-closed; a resource created earlier and reused is not (and re-closing is a bug).
- The resource's static type must be `AutoCloseable` or `Closeable`; wrapping streams (e.g., `BufferedWriter` over `FileOutputStream`) closes the underlying stream too — do NOT close both.
- If `close()` throws and the body also threw, the close exception is appended to `getSuppressed()` — logging only `e.getMessage()` hides it.
- `close()` throwing after a successful body masks the *operation* as failed — make your `close()` idempotent and exception-free where possible.
- Auto-closing happens at the *end of the try block*, so a `return` inside the body still triggers close (unlike a `finally` that must be written manually).
- On Java 9+, variables declared *outside* can be used if they are effectively final: `try (r)` — but then `r` is closed, which may surprise reuse.
