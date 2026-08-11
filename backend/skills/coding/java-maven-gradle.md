---
lang: java
keywords: maven, gradle, pom.xml, build.gradle, dependency, build tool, mvn, gradlew
---

# Maven & Gradle Basics

Maven and Gradle are build tools that compile, run tests, package, and pull dependencies from repositories. Maven uses a declarative `pom.xml`; Gradle uses a Groovy/Kotlin DSL. The standard layout both expect is `src/main/java`, `src/main/resources`, `src/test/java`.

```java
package com.example;

public class Main {
    public static void main(String[] args) {
        System.out.println("Built by Maven/Gradle");
    }
}
```

Maven `pom.xml` (the `<dependencies>` section is where Gson/JUnit/etc. get added):

```xml
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>demo</artifactId>
  <version>1.0-SNAPSHOT</version>
  <properties>
    <maven.compiler.release>17</maven.compiler.release>
  </properties>
  <dependencies>
    <dependency>
      <groupId>com.google.code.gson</groupId>
      <artifactId>gson</artifactId>
      <version>2.10.1</version>
    </dependency>
  </dependencies>
</project>
```

Gradle `build.gradle`:

```gradle
plugins {
    id 'application'
}
repositories { mavenCentral() }
dependencies { implementation 'com.google.code.gson:gson:2.10.1' }
java {
    toolchain { languageVersion = JavaLanguageVersion.of(17) }
}
application { mainClass = 'com.example.Main' }
```

Commands: `mvn compile`, `mvn test`, `mvn package`, `mvn exec:java`; or `gradle build`, `gradle run`.

Gotchas:
- The `pom.xml` `<dependency>` **must** be inside `<dependencies>`, and the `groupId:artifactId:version` must match the published coordinates exactly (e.g., it's `junit-jupiter`, not `junit`).
- Keep source in `src/main/java` and tests in `src/test/java` — a file in the wrong directory compiles but tests never run (or vice versa).
- `mvn package` runs tests by default; `-DskipTests` skips *running* but still compiles, `-Dmaven.test.skip=true` skips compiling too.
- Gradle's `implementation` vs `api`: only `api` leaks the dependency to consumers; using `implementation` for a library's public types breaks downstream compile.
- Never commit `target/`, `build/`, or `.gradle/` — they're regenerated; add them to `.gitignore`.
- `mvn compile` only compiles; `mvn package` also runs tests and jars (class files land in `target/classes`). And use the wrapper (`mvnw`/`gradlew`) to pin the build tool version — it avoids "works on my machine".
