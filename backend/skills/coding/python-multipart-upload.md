---
lang: python
keywords: multipart, upload, file, requests, files, form data, post, stream, attach, upload file
---

# Multipart file upload with requests

Uploading a file to a REST API means sending a `multipart/form-data` body with a file part and
optional extra form fields. Pass the files dict with a *name* + *tuple* of (filename, fileobj,
content-type), and stream a real file instead of reading it all into memory.

```python
# pip install requests
import io

import requests


def upload_bytes(url: str, field: str, filename: str, data: bytes,
                 extra: dict | None = None) -> requests.Response:
    files = {field: (filename, io.BytesIO(data), "application/octet-stream")}
    resp = requests.post(url, files=files, data=extra or {}, timeout=60)
    resp.raise_for_status()
    return resp


def upload_file(url: str, field: str, path: str,
                extra: dict | None = None) -> requests.Response:
    with open(path, "rb") as f:                    # streamed, not slurped
        files = {field: (path.rsplit("/", 1)[-1], f)}
        resp = requests.post(url, files=files, data=extra or {}, timeout=60)
        resp.raise_for_status()
        return resp


resp = upload_bytes(
    "https://httpbin.org/post",
    "file",
    "hello.txt",
    b"hello world",
    {"note": "from python"},
)
print(resp.json()["files"], resp.json()["form"])
```

Gotchas:
- The files value must be a tuple `(filename, fileobj, content_type)` or a `(filename, fileobj)`
  pair — passing the file object alone makes the API reject or misparse the part.
- `data=extra` adds ordinary form fields alongside the file part; without `data=`, servers
  expecting them get `MultiValueDictKeyError` / `400`.
- Requests figures out Content-Length from the file object; when streaming a real file, keep
  the `with open` *inside* the request call so the handle lives for the whole send.
- Multipart boundaries are generated automatically; never set `Content-Type` yourself or the
  boundary is lost and the server can't split the body.
- For huge files raise `timeout=` (default 60s may be too short) and consider
  `stream=True`/resumable chunked uploads if your endpoint supports them.
- Field name must match what the API expects (commonly `file`, `upload`, `image`) — wrong name
  returns 400 with "required" errors, not a clearer message.
