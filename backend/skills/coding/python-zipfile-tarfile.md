---
lang: python
keywords: zipfile, tarfile, archive, extract, compress, zip, tar, gzip, infolist, packaging
---

# Zip and tar archives: read, write, safe extract

Bundling logs, distributing artifacts, or reading a downloaded dataset — `zipfile` and
`tarfile` are the stdlib answer. Read members without extracting, and guard extraction against
zip-slip path traversal.

```python
import zipfile
from pathlib import Path


def archive_folder(src: Path, out: Path) -> None:
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in src.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(src))   # store relative paths


def read_member(zip_path: Path, member: str) -> str:
    with zipfile.ZipFile(zip_path) as zf:
        return zf.read(member).decode("utf-8")


def safe_extract(zip_path: Path, dest: Path) -> None:
    dest = dest.resolve()
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            target = (dest / info.filename).resolve()
            if not target.is_relative_to(dest):
                raise ValueError(f"unsafe path in archive: {info.filename}")
        zf.extractall(dest)


src = Path("src_dir")
src.mkdir(exist_ok=True)
(src / "a.log").write_text("hello log")
archive_folder(src, Path("bundle.zip"))
print(read_member(Path("bundle.zip"), "a.log"))
```

Gotchas:
- Always extract from archives you don't fully trust with a path check: `../evil` or absolute
  members can escape the destination dir — the `is_relative_to` guard above blocks zip-slip.
- `zf.read(member)` loads the whole member into memory; for huge files iterate with
  `zf.open(member)` and read in chunks.
- `zipfile.ZipFile(path)` opens for reading automatically; `"w"` truncates an existing file —
  use `"a"` to append.
- Filenames in archives may be encoded oddly (cp437 vs utf-8); pass `metadata_encoding="utf-8"`
  on open when needed, and handle decode errors.
- `tarfile.extractall` has the same traversal risk — apply the same resolve + prefix check, or
  use `tarfile.data_filter()` in Python 3.12+.
- `tarfile.open(name, "w:gz")` gives gzip-compressed tar; don't confuse `"w"` (uncompressed)
  with `"w:gz"`.
