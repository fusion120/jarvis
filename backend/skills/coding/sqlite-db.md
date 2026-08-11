---
lang: python
keywords: sqlite, database, db, sql, table, query, insert, select, where
---
# SQLite CRUD in Python (no server needed)

SQLite is a single-file database built into Python — perfect for local tools.

```python
import sqlite3

con = sqlite3.connect("app.db")       # creates the file if missing
con.row_factory = sqlite3.Row         # access columns by name
cur = con.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL, done INTEGER DEFAULT 0)")

# insert (parameterized — never f-string your values)
cur.execute("INSERT INTO tasks (title) VALUES (?)", ("build mimo",))
con.commit()

# read
for row in cur.execute("SELECT id, title, done FROM tasks WHERE done = 0"):
    print(row["id"], row["title"])

# update / delete
cur.execute("UPDATE tasks SET done = 1 WHERE id = ?", (row["id"],))
cur.execute("DELETE FROM tasks WHERE done = 1")
con.commit()
con.close()
```

Gotchas:
- **Always use `?` placeholders** — string interpolation into SQL is an
  injection hole, even in local scripts.
- `con.commit()` after writes; reads don't need it.
- `sqlite3.Row` lets you use `row["name"]` — much nicer than tuples.
- `conn.execute` in a `with` block still needs an explicit commit to persist.
