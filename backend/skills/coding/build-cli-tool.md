---
lang: python
keywords: cli, command line, argparse, tool, terminal, flags
---
# Build a small CLI tool in Python

Use `argparse` (stdlib) so flags are free and errors are friendly.

```python
import argparse

def main():
    p = argparse.ArgumentParser(description="Rename files in a folder")
    p.add_argument("folder", help="path to the folder")
    p.add_argument("--prefix", default="file_", help="new name prefix")
    p.add_argument("-n", "--dry-run", action="store_true", help="just print, don't rename")
    args = p.parse_args()

    if args.dry_run:
        print(f"would rename in {args.folder} with prefix {args.prefix!r}")
    else:
        print(f"renaming in {args.folder}...")

if __name__ == "__main__":
    main()
```

Gotchas:
- Positional args for the main input, `--flag` for options, `-x` short forms
  for the common ones.
- `action="store_true"` for boolean flags (they're `False` unless passed).
- Always print a clear message about what you're about to do; a `--dry-run`
  flag is cheap insurance for anything that mutates files.
- Return a non-zero exit code on failure: `sys.exit("something broke")`.
