# MIMO Coding Playbooks

MIMO's on-demand coding knowledge library. Each `.md` file is one real
scenario with a working example. When Mohamed asks for code, the backend
detects the task's language, matches keywords against each playbook, and
injects the best 2-3 into the coding prompt — only on coding tasks, never
on normal chat.

With 200+ playbooks across **Python, Java, JavaScript, HTML**, plus
hardware (Arduino/ESP32/Pi) and general topics, MIMO has a working complex
pattern for nearly every task you hand it. The library grows by adding
files — the matcher and prompt cost stay flat because only a handful are
injected per task.

## Frontmatter format

Every file starts with a `---` block with two fields:

```
---
lang: python
keywords: parse json, api client, requests, timeout, retry
---
```

- **`lang`** — one of `python`, `java`, `javascript`, `html`, `cpp`,
  `sql`, `bash`, or `general`. When Mohamed's task names a language, only
  playbooks for that language (plus `general`) compete for injection.
  Use `general` for cross-language topics (git, regex, serial ports).
- **`keywords`** — comma-separated words and short phrases Mohamed is
  likely to type (lowercase). Multi-word phrases are split and matched
  word-by-word. Keywords that appear in the filename score double.

Then the body: a short scenario description, a **REAL working code
snippet**, and a `Gotchas:` list of pitfalls. Keep each file focused —
one scenario per file. Prefer stdlib; if you use a third-party library,
include the install command in the file.

## How to add your own
1. Copy any file here, rename it `python-my-scenario.md` (or the
   matching language prefix).
2. Fill in `lang:` and `keywords:` exactly as above.
3. Write the scenario: explanation + working code + gotchas.

The loader reads this folder at startup — restart the backend after adding
files. MIMO then picks the file up automatically, no code changes.
