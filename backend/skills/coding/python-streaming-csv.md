---
lang: python
keywords: csv, streaming, chunk, generator, DictReader, large file, parse, yield, memory
---

# Streaming a large CSV in chunks

Reading a multi-GB CSV all at once with `csv.reader` + a list blows up memory. A generator
yields rows in chunks, so you process, aggregate, and discard — constant memory regardless of
file size.

```python
import csv
from pathlib import Path


def iter_rows(path: Path, chunk: int = 1000):
    """Yield lists of up to `chunk` rows from a CSV with a header row."""
    buffer: list[dict] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            buffer.append(row)
            if len(buffer) >= chunk:
                yield buffer
                buffer = []
        if buffer:
            yield buffer


def total_value(path: Path) -> int:
    total = 0
    for rows in iter_rows(path):
        for r in rows:
            value = r["value"].strip()
            if value.isdigit():
                total += int(value)
    return total


def make_sample(path: Path, n: int = 2500) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "value"])
        writer.writeheader()
        for i in range(n):
            writer.writerow({"id": i, "value": i * 2})


p = Path("data.csv")
make_sample(p)
print("total:", total_value(p))
```

Gotchas:
- A bare `with open(...)` in a generator defers opening until first iteration — if the file is
  missing you get the error at consumption, not at call time; that's fine but be aware.
- `newline=""` is required when writing CSVs and recommended when reading, or `\r\n` artifacts
  appear on Windows.
- Rows from `DictReader` arrive as strings: "3" not 3. Convert explicitly (`int(r["value"])`)
  and validate — a header-less or mismatched file yields `KeyError`.
- Don't materialize the whole generator (`list(iter_rows(path))`) — that defeats streaming;
  aggregate as you go.
- `encoding="utf-8"` may hit `UnicodeDecodeError` on real-world files; use
  `encoding="utf-8-sig"` for a BOM, or `errors="replace"` to skip bad bytes.
- Keep a `fieldnames=` argument when writing, and match it to the reader's columns or the
  header row will be misaligned.
