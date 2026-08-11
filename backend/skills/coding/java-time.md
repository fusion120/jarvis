---
lang: java
keywords: java.time, LocalDate, LocalDateTime, ZonedDateTime, Duration, Period, DateTimeFormatter, timezone
---

# Date & Time with java.time

The `java.time` API (Java 8+) replaces the flawed `Date`/`Calendar`. `LocalDate`/`LocalTime` are calendar-agnostic wall times; `ZonedDateTime` carries a time zone; `Duration` measures seconds/nanos, `Period` measures calendar days. Formatters are immutable and thread-safe.

```java
import java.time.*;
import java.time.format.*;
import java.time.temporal.ChronoUnit;

public class JavaTimeDemo {
    public static void main(String[] args) {
        LocalDate today = LocalDate.now();
        LocalDate deadline = today.plusWeeks(2).withDayOfMonth(1);
        System.out.println("days until deadline: " + ChronoUnit.DAYS.between(today, deadline));

        // Duration for sub-day spans, Period for calendar spans
        Duration d = Duration.ofMinutes(90);
        System.out.println(d.toHours() + "h " + d.toMinutesPart() + "m");
        Period p = Period.between(LocalDate.of(2020, 1, 1), today);
        System.out.println("years=" + p.getYears() + " months=" + p.getMonths());

        // formatting with a fixed pattern
        LocalDateTime event = LocalDateTime.of(2026, 8, 7, 14, 30);
        DateTimeFormatter fmt = DateTimeFormatter.ofPattern("EEE, d MMM yyyy HH:mm");
        System.out.println(event.format(fmt));

        // converting across time zones — the SAME instant
        ZonedDateTime ny = event.atZone(ZoneId.of("America/New_York"));
        ZonedDateTime london = ny.withZoneSameInstant(ZoneId.of("Europe/London"));
        System.out.println("NY: " + ny + " -> London: " + london);

        // parsing ISO-8601 by default
        LocalDate parsed = LocalDate.parse("2026-08-07");
        System.out.println(parsed.plusDays(1));

        // monotonic measurement — not wall-clock
        Instant start = Instant.now();
        double x = 0;
        for (int i = 0; i < 1_000_000; i++) x += Math.sqrt(i);
        System.out.println("elapsed ms: " + Duration.between(start, Instant.now()).toMillis());
    }
}
```

Gotchas:
- `Date` is mutable and timezone-hiding; never store or pass it in new code — `Instant`/`ZonedDateTime` are the correct carriers.
- `LocalDate`/`LocalDateTime` have NO zone concept — you cannot convert them to an instant without supplying a `ZoneId` first.
- `Duration` is seconds/nanos (for `Instant` math); `Period` is years/months/days (for `LocalDate` math). Mixing them up silently does the wrong thing.
- `plus(1, ChronoUnit.MONTHS)` on Jan 31 throws `DateTimeException` — the last day of the month doesn't exist; use `withDayOfMonth` or `lastDayOfMonth` adjusters.
- `DateTimeFormatter.ofPattern` uses a fixed locale-dependent set — use `.withLocale(...)` or `DateTimeFormatter.ofPattern(pattern, locale)`.
- `ZonedDateTime` (DST rules) vs `OffsetDateTime` (fixed offset): prefer `ZonedDateTime` for human schedules. And `System.currentTimeMillis()` is wall-clock and can jump with NTP; use `System.nanoTime()`/`Instant` for intervals.
