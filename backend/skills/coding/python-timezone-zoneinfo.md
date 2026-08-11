---
lang: python
keywords: timezone, zoneinfo, datetime, tz, utc, aware, localize, dst, timestamp, isoformat, pytz
---

# Timezone-safe datetimes with zoneinfo

"Local time" is ambiguous across DST and machines. The rule: always store/compute in UTC, and
convert to a local zone only at the display boundary. `zoneinfo.ZoneInfo` (Python 3.9+,
stdlib) reads the OS timezone database — no pytz needed.

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

utc_now = datetime.now(timezone.utc)
cairo = ZoneInfo("Africa/Cairo")
tokyo = ZoneInfo("Asia/Tokyo")
ny = ZoneInfo("America/New_York")

print("utc:  ", utc_now.isoformat(timespec="seconds"))
print("cairo:", utc_now.astimezone(cairo).isoformat(timespec="seconds"))
print("tokyo:", utc_now.astimezone(tokyo).strftime("%Y-%m-%d %H:%M %Z"))
print("ny:   ", utc_now.astimezone(ny).strftime("%Y-%m-%d %H:%M %Z"))


def is_dst(when: datetime, tz_name: str) -> bool:
    aware = when.astimezone(ZoneInfo(tz_name))
    return bool(aware.dst())


print("NY in DST now:", is_dst(utc_now, "America/New_York"))


def from_local(dt: datetime, tz_name: str) -> datetime:
    """Attach a zone to a naive wall-clock time (localize, don't convert)."""
    if dt.tzinfo is not None:
        raise ValueError("input must be naive")
    return dt.replace(tzinfo=ZoneInfo(tz_name))
```

Gotchas:
- `datetime.now()` (naive) and a `ZoneInfo`-aware datetime are not comparable — mixing them
  raises `TypeError: can't compare offset-naive and offset-aware datetimes`.
- Always attach UTC with `datetime.now(timezone.utc)`, never `datetime.utcnow()` which returns
  a *naive* UTC — converting that to a zone applies the zone incorrectly.
- `astimezone(tz)` converts an aware datetime; `replace(tzinfo=tz)` just labels it. Using the
  wrong one shifts the clock by the zone offset (the classic "twice the offset" bug).
- DST transitions make local times ambiguous or nonexistent for an hour — `replace(tzinfo=...)`
  will pick *a* valid offset; validate if you care.
- `ZoneInfo` raises `ZoneInfoNotFoundError` for unknown names — catch it and validate input
  zone names, especially from user config.
- Windows ships no IANA timezone database, so `ZoneInfo("Africa/Cairo")` raises
  `ZoneInfoNotFoundError` unless you `pip install tzdata` (pure-Python IANA data). Linux and
  macOS include it already.
- For arithmetic across DST, add with `datetime` `timedelta` on *aware* datetimes in UTC to get
  true elapsed time, not wall-clock shifts.
