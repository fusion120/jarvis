---
lang: javascript
keywords: node fs, readFile, writeFile, readdir, promises api, mkdir, watch, stream large file, fs/promises, stat, rename, copy
---

# Node fs read/write

Node's `fs/promises` API is async and returns promises — never the callback or sync (`readFileSync`) variants in a server. Reach for it for config loading, log rotation, file watching, and atomic writes.

```javascript
// Prefer fs/promises everywhere
const fs = require("node:fs/promises");
const path = require("node:path");

async function run() {
  const dir = path.join(process.cwd(), "data");
  await fs.mkdir(dir, { recursive: true });     // no error if exists

  const file = path.join(dir, "notes.txt");

  // Write then read back
  await fs.writeFile(file, "hello, jarvis\n", "utf-8");
  await fs.appendFile(file, "second line\n", "utf-8");
  const content = await fs.readFile(file, "utf-8");
  console.log(content.trim());                  // "hello, jarvis\nsecond line"

  // Atomic write: write to tmp then rename (no partial reads by others)
  const tmp = `${file}.${process.pid}.tmp`;
  await fs.writeFile(tmp, content.toUpperCase());
  await fs.rename(tmp, file);

  // List and stat
  const entries = await fs.readdir(dir, { withFileTypes: true });
  for (const e of entries) {
    const st = await fs.stat(path.join(dir, e.name));
    console.log(e.name, st.size, e.isDirectory() ? "dir" : "file");
  }

  // Watch for changes (abort after 100ms)
  const ac = new AbortController();
  const watcher = fs.watch(dir, { signal: ac.signal });
  setTimeout(() => ac.abort(), 100);
  try {
    for await (const ev of watcher) {
      console.log("changed:", ev.filename, ev.eventType);
      break;
    }
  } catch { /* aborted by the timer */ }

  await fs.rm(file, { force: true });
}

run().catch((err) => { console.error(err); process.exit(1); });
```

Gotchas:
- Always pass `"utf-8"` or you get a `Buffer` back (fine for binary, surprising for text).
- Prefer `fs/promises` over callbacks and NEVER `readFileSync` in a request handler — it blocks the event loop.
- `fs.watch` is OS-dependent: `rename` vs `change` events differ across platforms; don't rely on precise granularity.
- `writeFile` truncates existing content; use `appendFile` (or `open` with `"a"` flag) to add.
- Missing files throw `ENOENT` — check-then-read races; prefer catching `ENOENT`.
- Writing big files: use streams (`createWriteStream`) so you don't buffer the whole file in memory.
