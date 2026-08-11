---
lang: java
keywords: reflection, class, getMethod, invoke, getDeclaredField, setAccessible, introspect, getDeclaredConstructor, method
---

# Reflection: Inspecting & Invoking Code at Runtime

Reflection lets you discover methods/fields and call them when the type is only known as a `Class<?>` — the basis of DI containers, mappers, and serializers. Use `getDeclaredX` for private members plus `setAccessible(true)`, and unwrap the real cause from `InvocationTargetException`.

```java
import java.lang.reflect.*;

public class ReflectionDemo {
    static class User {
        private final String name;
        public User(String name) { this.name = name; }
        private String secret() { return name.toUpperCase(); }
    }

    public static void main(String[] args) throws Exception {
        // binary name: nested class uses $, not .
        Class<?> cls = Class.forName("ReflectionDemo$User");

        // invoke a private constructor
        Constructor<?> ctor = cls.getDeclaredConstructor(String.class);
        ctor.setAccessible(true);
        Object u = ctor.newInstance("ada");

        // invoke a private method
        Method m = cls.getDeclaredMethod("secret");
        m.setAccessible(true);
        System.out.println("secret=" + m.invoke(u));

        // read a private field
        Field f = cls.getDeclaredField("name");
        f.setAccessible(true);
        System.out.println("field=" + f.get(u));

        // list public methods (includes inherited Object methods)
        for (Method pm : cls.getMethods()) {
            if (pm.getName().startsWith("secret")) System.out.println("found: " + pm);
        }
    }
}
```

Gotchas:
- `getMethod` only finds *public* members (including inherited); private ones need `getDeclaredMethod` + `setAccessible(true)`.
- `invoke` wraps any exception the target threw in `InvocationTargetException` — call `getCause()` or you'll chase the wrong stack.
- `setAccessible(true)` can throw `InaccessibleObjectException` for JDK-internal modules under the module system — don't poke into `java.*`.
- Nested class binary names use `$` (`Outer$Inner`), not `.`; `Class.forName("Outer.Inner")` fails.
- Reflection is slow and bypasses compile-time checks — cache `Method`/`Field` objects and reuse them instead of re-looking-up per call.
- `newInstance()` on a private constructor requires the matching public/declared constructor lookup; prefer `getDeclaredConstructor` over the deprecated `Class.newInstance()`.
