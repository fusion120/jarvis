---
lang: python
keywords: pathlib, path, os.path, filesystem, glob, mkdir, resolve, is_file, touch, walk
---

# Robust filesystem work with pathlib

`pathlib.Path` replaces the string-concatenating, `os.path.join`-style code with object
methods that work identically on Windows and POSIX. Reach for it for any file walking, globbing,
or create-or-fail logic.

```python
from pathlib import Path
import tempfile


def collect_logs(root: Path, out_dir: Path) -> list[Path]:
    """Copy every *.log under root into out_dir; create out_dir on demand."""
    out_dir.mkdir(parents=True, exist_ok=True)      # parents + idempotent
    copied: list[Path] = []
    for file in root.rglob("*.log"):                # recursive glob
        if not file.is_file():
            continue
        target = out_dir / file.name
        target.write_text(file.read_text(errors="replace"))
        copied.append(target)
    return copied


def main() -> None:
    base = Path(tempfile.mkdtemp())
    nested = base / "a" / "b"
    nested.mkdir(parents=True, exist_ok=True)
    (nested / "x.log").write_text("hello", encoding="utf-8")

    out = base / "output"
    for p in collect_logs(base, out):
        print(p.resolve(), p.stat().st_size)


if __name__ == "__main__":
    main()
```

Gotchas:
- `mkdir(exist_ok=True)` without `parents=True` still fails when an intermediate directory is
  missing — use both for nested create.
- `Path` with `/` joins cleanly: `root / "sub" / "file.txt"`, never string `+` or
  `os.path.join` fragments that assume a separator.
- `read_text()`/`write_text()` default to the platform encoding; pass `encoding="utf-8"`
  explicitly for cross-platform files.
- `exists()` returns `False` for a broken symlink; if symlinks matter, test `is_symlink()` too.
- `Path.glob`/`rglob` return paths relative to the base; `resolve()`/`absolute()` when you need
  an absolute path or to normalize `..`.
- Comparing paths: use `==` (Path objects), and `relative_to`/`is_relative_to` for containment
  checks instead of string `startswith` (which breaks on prefix boundary bugs).
