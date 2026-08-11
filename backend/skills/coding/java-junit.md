---
lang: java
keywords: junit, test, assertEquals, assertThrows, parameterized test, @Test, unit test, @BeforeEach
---

# JUnit 5 Tests

JUnit 5 (`org.junit.jupiter`) is the standard test framework: `@Test` methods, `@BeforeEach`/`@AfterEach` setup, `assertThrows` for exception contracts, `@Timeout` for hang guards, and `@ParameterizedTest` with `@CsvSource` to run one test over many inputs. Add the dependency below (test scope).

```java
import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.*;

class CalculatorTest {
    Calculator calc;

    @BeforeEach
    void setUp() {
        calc = new Calculator();
    }

    @Test
    void addWorks() {
        assertEquals(5, calc.add(2, 3));
    }

    @Test
    @Timeout(value = 1, unit = TimeUnit.SECONDS) // fails the test if it hangs
    void quickTest() {
        assertEquals(6, calc.add(3, 3));
    }

    @ParameterizedTest
    @CsvSource({"1,2,3", "10,20,30", "-1,1,0"})
    void addParameters(int a, int b, int expected) {
        assertEquals(expected, calc.add(a, b));
    }

    @Test
    void divideByZeroThrows() {
        ArithmeticException ex = assertThrows(ArithmeticException.class,
            () -> calc.divide(1, 0));
        assertNotNull(ex.getMessage());
    }
}

class Calculator {
    int add(int a, int b) { return a + b; }
    int divide(int a, int b) { return a / b; }
}
```

Add to `pom.xml` (or `testImplementation 'org.junit.jupiter:junit-jupiter:5.11.0'` in Gradle):

```xml
<dependency>
  <groupId>org.junit.jupiter</groupId>
  <artifactId>junit-jupiter</artifactId>
  <version>5.11.0</version>
  <scope>test</scope>
</dependency>
```

Gotchas:
- Test classes/methods can be package-private; `public` is not required by JUnit 5 (unlike JUnit 4).
- A test *passes when it throws nothing* — assert something, or a "green" test is testing nothing.
- `assertThrows` asserts the exception *type* and returns it for further checks; a method that returns normally fails the assertion.
- Floating-point equality needs a delta: `assertEquals(0.3, 0.1 + 0.2, 1e-9)` — plain `assertEquals` on doubles is flaky.
- `@BeforeEach` runs before EVERY test, including each parameterized invocation — don't put expensive setup there if you can help it.
- Tests must be independent and order-agnostic; shared mutable static state makes runs pass/fail by order. Use `assertAll` to collect every broken assertion into one report instead of stopping at the first.
