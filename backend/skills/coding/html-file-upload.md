---
lang: html
keywords: file upload, image preview, drag drop upload, createObjectURL, revokeObjectURL, accept attribute, multiple files, input file
---

# File Upload with Image Preview

A drop zone + hidden file input that validates type and size, then shows thumbnails built with `URL.createObjectURL`. Covers the drag-over highlight, per-file remove, and the blob-memory cleanup people forget.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>File upload preview</title>
<style>
  body { font: 16px/1.6 system-ui; max-width: 36rem; margin: 2rem auto; padding: 0 1rem; }
  #drop { border: 2px dashed #aaa; border-radius: 10px; padding: 2rem; text-align: center; color: #666; }
  #drop.drag { border-color: #07c; background: #f0f7ff; }
  #thumbs { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1rem; }
  .thumb { position: relative; border: 1px solid #ddd; border-radius: 8px; padding: .5rem; width: 6rem; }
  .thumb img { width: 100%; height: 4rem; object-fit: cover; border-radius: 4px; }
  .thumb button { position: absolute; top: .25rem; right: .25rem; border: 0; background: rgb(0 0 0 / .6); color: #fff; border-radius: 50%; cursor: pointer; }
  .thumb span { font-size: .75rem; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
</head>
<body>
<h1>Upload with preview</h1>
<label id="drop" for="file">
  Drop images here or <u>browse</u>
  <input id="file" type="file" accept="image/*" multiple hidden>
</label>
<div id="thumbs" aria-live="polite"></div>
<script>
  const input = document.getElementById('file');
  const thumbs = document.getElementById('thumbs');
  const drop = document.getElementById('drop');
  const MAX = 2 * 1024 * 1024; // 2 MB

  function addFile(file) {
    if (!file.type.startsWith('image/')) return alert(file.name + ' is not an image');
    if (file.size > MAX) return alert(file.name + ' is larger than 2 MB');
    const div = document.createElement('div');
    div.className = 'thumb';
    const img = document.createElement('img');
    img.alt = 'Preview of ' + file.name;
    img.src = URL.createObjectURL(file); // revoke when removed
    const span = document.createElement('span');
    span.textContent = file.name;
    const rm = document.createElement('button');
    rm.textContent = '×';
    rm.setAttribute('aria-label', 'Remove ' + file.name);
    rm.addEventListener('click', () => { URL.revokeObjectURL(img.src); div.remove(); });
    div.append(img, span, rm);
    thumbs.append(div);
  }
  input.addEventListener('change', () => { [...input.files].forEach(addFile); input.value = ''; });
  ['dragenter', 'dragover'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add('drag'); }));
  ['dragleave', 'drop'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove('drag'); }));
  drop.addEventListener('drop', e => { [...e.dataTransfer.files].forEach(addFile); });
</script>
</body>
</html>
```

Gotchas:
- `URL.revokeObjectURL(img.src)` on removal is required or blob memory leaks until the page unloads.
- `accept="image/*"` only filters the picker — drag-dropped files bypass it entirely, so validate `file.type` and `file.size` in JS.
- Reset `input.value = ''` after handling, or selecting the same file again won't fire `change`.
- `preventDefault` is needed on BOTH `dragover` and `drop` or dropping a file navigates away from the page.
- `FileReader.readAsDataURL` works but is heavier than `createObjectURL` for previews — use the URL, keep FileReader for other transforms.
- Files dropped from another browser have an empty `type` (`''`) — if security matters, sniff magic bytes, don't trust the MIME string.
