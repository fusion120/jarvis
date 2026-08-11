---
lang: javascript
keywords: node http, createServer, http server, request response, routing, json body, listen, status code, headers, http module
---

# Node http server

`node:http`'s `createServer` handles raw HTTP with zero dependencies — enough for health checks, webhooks, and small APIs. The request callback receives a readable `req` stream and a `res` writer; you collect the body by reading it.

```javascript
const http = require("node:http");
const { URL } = require("node:url");

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);

  // CORS for browser clients
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") { res.writeHead(204); return res.end(); }

  const send = (status, body) => {
    res.writeHead(status, { "Content-Type": "application/json" });
    res.end(JSON.stringify(body));
  };

  try {
    if (req.method === "GET" && url.pathname === "/health") {
      return send(200, { ok: true, uptime: process.uptime() });
    }

    if (req.method === "POST" && url.pathname === "/echo") {
      // Read the whole request body (respect content-length)
      let raw = "";
      for await (const chunk of req) raw += chunk;
      const body = raw ? JSON.parse(raw) : {};
      return send(200, { received: body, when: new Date().toISOString() });
    }

    send(404, { error: "not found", path: url.pathname });
  } catch (err) {
    send(400, { error: "bad request", detail: err.message });
  }
});

server.listen(3000, () => console.log("listening on http://localhost:3000"));
```

Gotchas:
- `req` is a stream: if you never read it (or don't call `res.end`), the socket hangs and clients time out. Always end responses.
- Reading `req` with `for await` buffers the body in memory — cap size (check `req.headers["content-length"]`) or a client can OOM you.
- `JSON.parse` on empty/bad bodies throws — wrap parse in try/catch and send 400.
- `new URL(req.url, base)` needs an absolute base; parsing `req.url` alone breaks on query strings.
- `res.writeHead` must come before any `res.write`; setting headers after data starts throws.
- HTTP keeps alive by default — a response that never ends holds the socket; always end, or set `Connection: close`.
- One server handles all routes; grow into a router (or Express) when paths multiply.
