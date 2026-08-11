---
lang: java
keywords: annotation, annotation processing, retention, target, reflect annotation, metadata, custom annotation, interface
---

# Custom Annotations & Runtime Processing

Define your own `@interface` with `@Retention(RUNTIME)` so the annotation survives to runtime, `@Target` to restrict where it applies, then read it with reflection to drive behavior — e.g., a retry policy attached to methods.

```java
import java.lang.annotation.*;
import java.lang.reflect.*;

public class CustomAnnotations {
    @Retention(RetentionPolicy.RUNTIME)
    @Target(ElementType.METHOD)
    public @interface Retry {
        int times() default 3;
        long backoffMillis() default 100;
    }

    static class Service {
        private static int calls = 0;

        @Retry(times = 5, backoffMillis = 10)
        public String flaky() {
            calls++;
            if (calls < 4) throw new IllegalStateException("boom " + calls);
            return "ok after " + calls + " attempts";
        }
    }

    public static void main(String[] args) throws Throwable {
        Method m = Service.class.getMethod("flaky");
        Retry retry = m.getAnnotation(Retry.class);

        Object svc = new Service();
        int attempt = 0;
        while (true) {
            try {
                Object result = m.invoke(svc);
                System.out.println(result);
                break;
            } catch (InvocationTargetException e) {
                attempt++;
                if (attempt >= retry.times()) throw e.getCause();
                Thread.sleep(retry.backoffMillis());
            }
        }
    }
}
```

Gotchas:
- Without `@Retention(RUNTIME)` the annotation is invisible to reflection (default is `CLASS`, dropped at runtime) — `getAnnotation` returns null.
- `@Target` restricts placement; a misplaced annotation is a compile error (e.g., METHOD on a class).
- Annotation elements are fixed at compile time: no nulls, no `Class<?>` wildcards, primitives/strings/enums/classes/arrays only; defaults must be compile-time constants.
- The array-typed element `int[] value()` is written `@A(value = {1, 2})` and read as `int[]` — single-element shorthand `@A(1)` only works for the element named `value`.
- `getDeclaredAnnotation` vs `getAnnotation`: the latter also surfaces `@Inherited` superclass annotations, the former only the exact element.
- Retrying via reflection as above must unwrap `InvocationTargetException` — rethrowing the wrapper without `getCause()` loses the original stack and type.
