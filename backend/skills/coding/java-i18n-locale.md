---
lang: java
keywords: i18n, locale, resourcebundle, messageformat, localization, internationalization, number format, currency
---

# Internationalization with Locale & ResourceBundle

Format numbers, currencies, and dates per `Locale`, and move user-facing strings into `ResourceBundle` properties files keyed by locale (`messages.properties`, `messages_de.properties`, ...). `MessageFormat` interpolates placeholders safely, including with locale-aware number formatting.

```java
import java.text.*;
import java.util.*;

public class I18nLocale {
    public static void main(String[] args) {
        double amount = 1_234.5;
        System.out.println("US: " + NumberFormat.getCurrencyInstance(Locale.US).format(amount));
        System.out.println("DE: " + NumberFormat.getCurrencyInstance(Locale.GERMANY).format(amount));

        Date now = new Date();
        System.out.println("FR date: " + DateFormat.getDateInstance(DateFormat.LONG, Locale.FRANCE).format(now));

        // pick the locale from a tag (e.g. "de") at runtime
        Locale de = Locale.forLanguageTag("de");

        // strings come from ResourceBundle — requires these on the classpath:
        //   messages.properties      greeting=Hello {0}!
        //   messages_de.properties   greeting=Hallo {0}!
        ResourceBundle bundle = ResourceBundle.getBundle("messages", de);
        MessageFormat mf = new MessageFormat(bundle.getString("greeting"), de);
        System.out.println(mf.format(new Object[]{"Ada"}));

        // number-sensitive pluralization example (English vs German)
        MessageFormat one = new MessageFormat("{0} item(s)", Locale.US);
        System.out.println(one.format(new Object[]{3}));
    }
}
```

Resource files (in `src/main/resources`):

```properties
# messages.properties
greeting=Hello {0}!
farewell=Goodbye
```

```properties
# messages_de.properties
greeting=Hallo {0}!
farewell=Auf Wiedersehen
```

Gotchas:
- `ResourceBundle.getBundle("messages", locale)` falls back up the locale chain (de_AT -> de -> default) and then to the base file — a missing base file throws `MissingResourceException`.
- `MessageFormat` treats `{0}` specially — to print a literal `{` escape it as `'{'`; single quotes are also special.
- `NumberFormat.getNumberInstance` vs `getIntegerInstance` vs `getCurrencyInstance` differ in rounding/grouping — pick the semantic one.
- `String.format("%.2f")` is NOT locale-aware by default — `%.2f` with `Locale.GERMANY` prints `1,23`; pass the locale explicitly or rely on `MessageFormat`'s `{0,number}` style.
- `Locale` equality matters for caches: `new Locale("de")` equals `Locale.GERMAN`, but `forLanguageTag("de-DE")` differs — standardize how you build locales.
- Default locale comes from the OS/JVM — don't assume `Locale.US`; set a default deliberately for tests (`Locale.setDefault`). And store/compare dates as `Instant`/`ZonedDateTime`; locale formatting is presentation-only and should never change stored values.
