---
lang: python
keywords: argparse, subcommand, command line, cli, parser, arguments, add_subparsers, flags, --help
---

# argparse with subcommands

Tools like `git commit` and `pip install` are one program with subcommands. `add_subparsers`
gives each subcommand its own flags, and `set_defaults(func=...)` dispatches cleanly to a
handler function.

```python
import argparse


def cmd_add(args) -> None:
    print(args.a + args.b)


def cmd_list(args) -> None:
    pattern = args.pattern or "*"
    print(f"listing {pattern}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tool", description="demo subcommands")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="add two numbers")
    p_add.add_argument("a", type=int)
    p_add.add_argument("b", type=int)
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="list files")
    p_list.add_argument("-p", "--pattern", default=None)
    p_list.set_defaults(func=cmd_list)

    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.func(args)                     # dispatch to cmd_add / cmd_list
# try:  python python-argparse-subcommands.py add 1 2
```

Gotchas:
- `required=True` on `add_subparsers` (Python 3.7+) turns a no-command run into an error;
  without it, a bare invocation silently does nothing.
- `dest="command"` lets you inspect `args.command` for help text or logging; dispatch via
  `args.func` avoids a chain of `if args.command == ...`.
- `type=int` performs the conversion *and* produces a clean error for non-numbers — don't
  convert manually afterwards.
- Options and positional order: `tool list --pattern x` and `tool add 1 2` both work; but
  options defined on the top parser must come before the subcommand name.
- Store flags as `default=None` when optional, then branch, instead of baking a magic default
  that hides "not provided".
- `choices=[...]` on an argument validates enums at parse time — prefer it to a later `if`.
