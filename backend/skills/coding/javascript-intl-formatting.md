---
lang: javascript
keywords: intl, Intl.DateTimeFormat, Intl.NumberFormat, locale, toLocaleDateString, toLocaleString, currency, timezone, formatToParts, ICU
---

# Intl date & number formatting

`Intl` gives locale-aware date, number, currency, and list formatting without a library. Reach for `Intl.DateTimeFormat`/`Intl.NumberFormat` instead of manual padding — it handles languages, timezones, and pluralization correctly.

```javascript
// Numbers: grouping, decimals, currency
const price = new Intl.NumberFormat("de-DE", {
  style: "currency",
  currency: "EUR",
}).format(1234.5);
console.log(price);                          // "1.234,50 €"

const pct = new Intl.NumberFormat("en-US", {
  style: "percent", maximumFractionDigits: 1,
}).format(0.234);
console.log(pct);                            // "23.4%"

// Dates: locale + timezone
const d = new Date("2026-08-07T10:30:00Z");
const en = new Intl.DateTimeFormat("en-GB", {
  dateStyle: "full", timeStyle: "short", timeZone: "Europe/London",
}).format(d);
console.log(en);                             // "Friday, 7 August 2026 at 11:30"

const jp = new Intl.DateTimeFormat("ja-JP", {
  year: "numeric", month: "short", day: "numeric",
}).format(d);
console.log(jp);                             // "2026年8月7日"

// Relative time (Intl.RelativeTimeFormat)
const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
console.log(rtf.format(-3, "day"));          // "3 days ago"

// Format long lists with correct conjunctions
const list = new Intl.ListFormat("en-GB", { style: "long", type: "conjunction" });
console.log(list.format(["js", "node", "sql"])); // "js, node and sql"

// formatToParts for fully custom output
const parts = new Intl.NumberFormat("en-US").formatToParts(1234.5);
console.log(parts.map((p) => `${p.type}:${p.value}`).join(" "));
```

Gotchas:
- Locale codes must match CLDR (`en-GB`, not `EN_gb`) or Intl throws `RangeError`.
- Always pass `timeZone` for dates or results depend on the host machine's zone — tests will be flaky otherwise.
- `toLocaleString(locale, opts)` re-creates the formatter each call — cache the `Intl` instance in loops.
- `style:"currency"` REQUIRES `currency` too, or it throws; `currencyDisplay:"narrowSymbol"` shrinks to `$`/`€`.
- Old Node without full-icu only renders `en-US`-ish output — Node 14+ ships full ICU by default.
- Relative time needs `Intl.RelativeTimeFormat` (ES2020); don't build "ago" strings by hand.
