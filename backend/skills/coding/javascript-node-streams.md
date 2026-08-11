---
lang: javascript
keywords: node streams, pipe, pipeline, Transform, Readable, Writable, createReadStream, createWriteStream, backpressure, gzip, buffer
---

# Node streams: pipe & Transform

Streams process data piece-by-piece with constant memory instead of loading whole files into RAM. `pipe` (or the safer `pipeline`) connects sources to destinations; a `Transform` sits in the middle to modify each chunk.

```javascript
const fs = require("node:fs");
const zlib = require("node:zlib");
const { pipeline, Transform } = require("node:stream");
const { promisify } = require("node:util");

const pipe = promisify(pipeline);

// Transform: prefix each line of a chunk (keep state between chunks)
const annotate = new Transform({
  transform(chunk, _enc, cb) {
    const lines = chunk.toString().split("\n").filter(Boolean);
    for (const line of lines) this.push(`> ${line.toUpperCase()}\n`);
    cb();
  },
});

// Compress a file to a .gz
async function gzipFile(src, dest) {
  await pipe(
    fs.createReadStream(src),          // Readable
    zlib.createGzip(),                 // Transform
    fs.createWriteStream(dest)         // Writable
  );
  console.log("done", dest);
}

// Read, annotate, write — memory stays flat no matter the file size
async function annotateFile(src, dest) {
  await pipe(fs.createReadStream(src), annotate, fs.createWriteStream(dest));
}

// Self-contained demo: gzip THIS file, annotate a copy of it
const src = __filename;
gzipFile(src, "self.txt.gz")
  .then(() => annotateFile(src, "annotated.txt"))
  .catch((err) => { console.error(err); process.exit(1); });
```

Gotchas:
- `stream.pipe()` does NOT forward errors and doesn't clean up on failure — use `pipeline` (or `stream/promises` `pipeline`) so errors propagate and streams are destroyed.
- `Transform` chunks are `Buffer`s; call `.toString()` with an encoding and remember state can span chunks (a line split across chunks needs buffering).
- `push()` must receive a string/Buffer; pushing `null` ends the stream (never push null unless truly done).
- Backpressure is automatic through `pipe`/`pipeline`; manual `write()` loops must respect `write()`'s boolean return and wait for `drain`.
- Don't `for await` a stream without try/catch — stream errors surface as an unhandled rejection.
- Reading a whole file with `readFile` in a server negates the point — use streams for large payloads.
