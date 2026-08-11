---
lang: java
keywords: jdbc, sql, prepared statement, connection, resultset, sql injection, h2, sqlite, transaction
---

# JDBC with H2/SQLite

JDBC is the standard way to talk to relational databases. Always use `PreparedStatement` (never string-concatenated SQL) to prevent injection, and let try-with-resources close `Connection`, `Statement`, and `ResultSet`. The example uses in-memory H2 — add the dependency below.

```java
import java.sql.*;

public class JdbcDemo {
    public static void main(String[] args) throws Exception {
        String url = "jdbc:h2:mem:test;DB_CLOSE_DELAY=-1";
        try (Connection conn = DriverManager.getConnection(url, "sa", "")) {
            try (Statement st = conn.createStatement()) {
                st.execute("CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(50))");
                st.executeUpdate("INSERT INTO users VALUES (1, 'Ada'), (2, 'Grace')");
            }
            // parameterized query — the ? are bound, not concatenated
            try (PreparedStatement ps = conn.prepareStatement(
                    "SELECT id, name FROM users WHERE id = ?")) {
                ps.setInt(1, 2);
                try (ResultSet rs = ps.executeQuery()) {
                    if (rs.next()) {
                        System.out.println(rs.getInt("id") + " " + rs.getString("name"));
                    }
                }
            }
            // update returns affected row count
            try (PreparedStatement ps = conn.prepareStatement(
                    "UPDATE users SET name = ? WHERE id = ?")) {
                ps.setString(1, "Grace Hopper");
                ps.setInt(2, 2);
                System.out.println("updated rows: " + ps.executeUpdate());
            }
            // explicit transaction — auto-commit off, commit on success
            conn.setAutoCommit(false);
            try (PreparedStatement ps = conn.prepareStatement(
                    "INSERT INTO users VALUES (?, ?)")) {
                ps.setInt(1, 3);
                ps.setString(2, "Linus");
                ps.executeUpdate();
            }
            conn.commit();
        }
    }
}
```

Add this to `pom.xml` (or `implementation 'com.h2database:h2:2.2.224'` in Gradle):

```xml
<dependency>
  <groupId>com.h2database</groupId>
  <artifactId>h2</artifactId>
  <version>2.2.224</version>
  <scope>runtime</scope>
</dependency>
```

For SQLite use `org.xerial:sqlite-jdbc` and url `jdbc:sqlite:app.db`.

Gotchas:
- Never build SQL by string concatenation — that is SQL injection. Every value goes through `PreparedStatement.setX`.
- `DriverManager.getConnection` auto-loads drivers from the classpath (JDBC 4+), but a missing driver jar throws `ClassNotFoundException`/`SQLException` — add the dependency.
- `ResultSet` is cursor-like: call `next()` before every `getX()`, and columns are 1-based if you use indices instead of names.
- Resources close in reverse order automatically with try-with-resources; closing `Connection` also closes its statements.
- Long-running `SELECT` without paging or fetch-size tuning can balloon memory; use `setFetchSize` and `LIMIT`.
- With auto-commit off, an uncommitted transaction rolls back on close — always `commit()` explicitly. And `getString` on a NULL column returns `null`; for primitives use `getInt` and check `wasNull()`.
