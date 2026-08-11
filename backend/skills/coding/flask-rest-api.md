---
lang: python
keywords: flask, rest, api, server, endpoint, cors, gunicorn, json
---
# Build a small REST API with Flask

The same shape as this repo's backend (`backend/app11.py`).

```python
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)                              # let the browser dashboard call it

@app.route("/api/ping", methods=["GET"])
def ping():
    return jsonify({"ok": True})

@app.route("/api/items", methods=["POST"])
def create_item():
    d = request.json or {}
    name = (d.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    return jsonify({"created": name}), 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

Gotchas:
- Return the right status codes: 200 ok, 201 created, 400 bad input,
  401/403 auth, 404 not found, 500 internal.
- `request.json` is `None` when the body isn't JSON — guard with `or {}`.
- For production run `gunicorn app:app` (which is what Render uses here) —
  never expose Flask's dev server.
- Keep routes `/api/...` namespaced so the dashboard can call them.
- Read secrets from `os.environ`, never commit them.
