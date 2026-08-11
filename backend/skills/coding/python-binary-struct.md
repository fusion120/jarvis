---
lang: python
keywords: struct, pack, unpack, binary, bytes, parse, little endian, header, file format, byte order
---

# Parsing binary files with struct

Binary formats (images, sensor logs, custom protocols) are just fields at byte offsets.
`struct` converts between Python values and packed bytes with explicit sizes and endianness.
Define each record layout once and reuse the compiled object.

```python
import struct

HEADER = struct.Struct("<4sI")      # 4-byte magic + uint32 count (little-endian)
RECORD = struct.Struct("<iif")      # int id, int x, float y


def write_file(path: str) -> None:
    rows = [(1, 10, 1.5), (2, 20, 2.5), (3, 30, 3.5)]
    with open(path, "wb") as f:
        f.write(HEADER.pack(b"DATA", len(rows)))
        for row in rows:
            f.write(RECORD.pack(*row))


def read_file(path: str) -> list[tuple]:
    records = []
    with open(path, "rb") as f:
        magic, count = HEADER.unpack(f.read(HEADER.size))
        if magic != b"DATA":
            raise ValueError("bad magic number")
        for _ in range(count):
            raw = f.read(RECORD.size)
            if len(raw) != RECORD.size:
                raise ValueError("truncated record")
            records.append(RECORD.unpack(raw))
    return records


write_file("data.bin")
print(read_file("data.bin"))
```

Gotchas:
- Prefix the format with a byte-order char: `<` (little-endian) or `>` (big-endian). Without
  it you get native order, which differs between ARM (ESP32) and x86 — your file becomes
  unportable.
- `I`/`L` are 4 bytes on most platforms, but plain `struct` uses native alignment; always pin
  exact widths with the prefix and `B/H/I/Q` types.
- `f.read(n)` can return fewer bytes than asked (rare on local files, common on sockets) —
  verify the length before unpacking, or you'll get `unpack requires a buffer of N bytes`.
- `pack` and `unpack` are strict: a wrong value range (`> 2**31` for `i`) or an extra value
  raises — match the field count exactly.
- Text is not free-form: encode strings with a length prefix (e.g. `H` count + `N s` bytes)
  and decode with an explicit encoding.
- `struct.calcsize` can save you from magic numbers — check the compiled `.size` instead of
  hardcoding byte counts.
