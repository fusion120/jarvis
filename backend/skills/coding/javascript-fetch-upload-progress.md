---
lang: javascript
keywords: fetch upload progress, upload progress bar, FormData, Blob, XMLHttpRequest upload, ReadableStream, progress event, file upload, chunked upload
---

# Fetch upload progress

`fetch` can't report upload progress directly — the standard answer is `XMLHttpRequest`'s `upload.onprogress` event, or building a `ReadableStream` body and tracking bytes you've written. For simple files, XHR is the least code; for streams, count bytes pushed into the request body.

```javascript
// browser
// Option 1: XMLHttpRequest gives upload progress out of the box
function uploadXHR(file, url, { onProgress } = {}) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress((e.loaded / e.total) * 100);
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try { resolve(JSON.parse(xhr.responseText)); }
        catch { resolve(xhr.responseText); }
      } else {
        reject(new Error(`HTTP ${xhr.status}`));
      }
    };
    xhr.onerror = () => reject(new Error("network error"));
    const fd = new FormData();
    fd.append("file", file, file.name);
    xhr.send(fd);
  });
}

// Option 2: fetch + ReadableStream, track bytes as we enqueue
function uploadFetchStream(file, url, { onProgress, chunkSize = 64 * 1024 } = {}) {
  const total = file.size;
  let sent = 0;
  const stream = new ReadableStream({
    start(controller) {
      let offset = 0;
      function pump() {
        const slice = file.slice(offset, offset + chunkSize);
        if (!slice.size) { controller.close(); return; }
        slice.arrayBuffer().then((buf) => {
          controller.enqueue(new Uint8Array(buf));
          offset += slice.size;
          sent = offset;
          onProgress?.((sent / total) * 100);
          pump();                              // continue draining the file
        });
      }
      pump();
    },
  });
  return fetch(url, {
    method: "POST",
    body: stream,
    headers: { "Content-Type": "application/octet-stream" },
  });
}

// Usage:
// const input = document.querySelector('input[type="file"]');
// input.addEventListener("change", () => {
//   uploadXHR(input.files[0], "/upload",
//     { onProgress: (p) => console.log(p.toFixed(0) + "%") });
// });
```

Gotchas:
- `fetch` bodies have NO progress events — if you need a progress bar, use XHR or hand-roll the stream count above.
- `ReadableStream` upload requires the server to accept chunked/streamed bodies; some proxies and HTTP/1.0 servers can't handle it.
- FormData sets `multipart/form-data` + boundary automatically; don't set `Content-Type` manually or the boundary is dropped.
- XHR `upload.onprogress` fires only when `e.lengthComputable` is true (server sent Content-Length) — guard it.
- `res.ok` check still required with the stream approach (fetch doesn't reject on HTTP errors).
- Large files: a plain `fetch(file)` body uploads without progress but lets the browser stream from disk.
- Cancelling: XHR has `.abort()`; the ReadableStream approach needs an `AbortController` passed to `fetch`.
