---
lang: java
keywords: jar, javac, classpath, manifest, main class, packaging, class file, executable jar
---

# JAR Packaging with javac & jar

Compile `.java` files to `.class`, then package into a JAR. An *executable* JAR needs the `Main-Class` in its manifest (or the `-e` flag) plus a valid classpath. This is the manual flow Maven/Gradle automate; knowing it demystifies build errors.

```java
import java.util.*;

public class HelloJar {
    public static void main(String[] args) {
        System.out.println("Hello from a JAR! args=" + Arrays.toString(args));
    }
}
```

Build and run (classic two-step):

```bash
javac HelloJar.java
echo "Main-Class: HelloJar" > MANIFEST.MF
jar cfm hello.jar MANIFEST.MF HelloJar.class
java -jar hello.jar one two
```

Same thing, one command with `-e` (no manual manifest):

```bash
javac HelloJar.java
jar cfe hello.jar HelloJar HelloJar.class
java -jar hello.jar one two
```

Running against external libraries:

```bash
javac -cp "libs\gson-2.10.1.jar;." App.java
jar cfe app.jar App -C classes . App.class
java -cp "app.jar;libs\gson-2.10.1.jar" App
```

Gotchas:
- The manifest's `Main-Class` must be the fully qualified class name *without* `.class`; the line needs a trailing newline, or the JAR isn't recognized as executable.
- `java -jar` ignores the `-cp` flag entirely — dependencies must be listed in the manifest's `Class-Path:` (relative URLs) or bundled, or you get `ClassNotFoundException`/`NoClassDefFoundError`.
- The class file for a `public class Foo` must be in a directory matching its package (`com/example/Foo.class`); `jar -C` lets you stage the root.
- `javac` doesn't create directories for `-d` — use `javac -d build/classes` with `build` pre-created; `-d` takes the existing root.
- A JAR is a ZIP: `jar tf hello.jar` lists contents — `java -jar` on a JAR whose manifest lacks `Main-Class` prints "no main manifest attribute".
- Rebuild stale classes explicitly: `javac` only recompiles what it's given — clean builds avoid phantom stale-class bugs. Java 9+ modules (multi-release JARs, `module-info.class`) change these commands; stick to the classpath form for simple apps.
