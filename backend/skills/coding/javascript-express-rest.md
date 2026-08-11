---
lang: javascript
keywords: express, rest api, router, middleware, app.get, app.post, express.json, error handling middleware, params, query, npm express
---

# Express REST API

Express layers routing, middleware, and JSON parsing on `node:http`. Reach for it when an API grows beyond a couple of routes — it gives you path params, `express.json()`, and an error-middleware chain.

```javascript
// npm install express
const express = require("express");

const app = express();
app.use(express.json());                    // parse JSON bodies

// In-memory store (use a real DB in production)
const todos = new Map();
let nextId = 1;

// GET /todos?done=true
app.get("/todos", (req, res) => {
  const want = req.query.done;              // undefined if not sent
  const done = want === undefined ? undefined : want === "true";
  const items = [...todos.values()].filter(
    (t) => done === undefined || t.done === done
  );
  res.json(items);
});

// POST /todos  {text}
app.post("/todos", (req, res) => {
  const { text } = req.body ?? {};
  if (typeof text !== "string" || !text.trim()) {
    return res.status(422).json({ error: "text is required" });
  }
  const todo = { id: nextId++, text, done: false };
  todos.set(todo.id, todo);
  res.status(201).json(todo);
});

// GET/PUT/DELETE /todos/:id
app.put("/todos/:id", (req, res) => {
  const todo = todos.get(Number(req.params.id));
  if (!todo) return res.status(404).json({ error: "not found" });
  Object.assign(todo, req.body ?? {}, { id: todo.id });
  res.json(todo);
});

app.delete("/todos/:id", (req, res) => {
  if (!todos.delete(Number(req.params.id))) {
    return res.status(404).json({ error: "not found" });
  }
  res.status(204).end();
});

// Error-handling middleware: 4 args => errors land here
app.use((err, req, res, next) => {
  console.error(err);
  res.status(err.status ?? 500).json({ error: err.message });
});

app.listen(3000, () => console.log("API on :3000"));
```

Gotchas:
- `express.json()` must be registered before any route that reads `req.body`, or body stays `{}`.
- `req.params` values are strings — coerce with `Number()` before using as a Map key.
- One response per request: if you `res.json()` in a route, don't also call `next()`.
- Error middleware MUST have exactly 4 args `(err, req, res, next)` or Express treats it as normal middleware and errors bypass it.
- For async handlers, wrap with try/catch (or use Express 5's built-in handling); an uncaught async throw becomes an unhandled rejection.
- `res.status(204).end()` — sending a body with 204 strips it per spec; use `end()`.
- Guard `req.body` with `?? {}` because malformed JSON already errored earlier in the chain.
