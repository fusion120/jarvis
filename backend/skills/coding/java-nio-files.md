---
lang: java
keywords: nio, Files, Path, read all lines, Files.walk, move, copy, attributes, file io
---

# NIO File I/O

`java.nio.file.Files` replaces most `java.io.File` boilerplate: read/write whole files in one call, stream lines lazily for big files, walk directory trees, and query attributes — all with cleaner error handling than `File`.

```java
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.Comparator;
import java.io.IOException;

public class NioFilesDemo {
    public static void main(String[] args) throws IOException {
        Path dir = Files.createTempDirectory("nio-demo");
        Path file = dir.resolve("data.txt");

        // write a list of lines
        Files.write(file, List.of("alpha", "beta", "gamma"), StandardCharsets.UTF_8);

        // read whole small file
        System.out.println(Files.readAllLines(file));

        // stream lines lazily for large files (always close the stream)
        try (var stream = Files.lines(file)) {
            stream.filter(s -> s.startsWith("b")).forEach(System.out::println);
        }

        // create nested dirs + walk the tree
        Path nested = Files.createDirectories(dir.resolve("a/b/c"));
        Files.writeString(nested.resolve("deep.txt"), "deep");
        Files.walk(dir)
             .map(p -> dir.relativize(p).toString())
             .sorted(Comparator.reverseOrder()) // deepest first
             .forEach(System.out::println);

        // read attributes without a stat syscall per field
        var attrs = Files.readAttributes(file, "size,lastModifiedTime");
        System.out.println("size=" + attrs.get("size") + " modified=" + attrs.get("lastModifiedTime"));

        // atomic-ish move and delete
        Files.move(file, dir.resolve("renamed.txt"), StandardCopyOption.REPLACE_EXISTING);
        Files.deleteIfExists(dir.resolve("renamed.txt"));

        // cleanup the whole temp tree
        Files.walk(dir)
             .sorted(Comparator.reverseOrder())
             .forEach(p -> { try { Files.deleteIfExists(p); } catch (IOException e) {} });
    }
}
```

Gotchas:
- `readAllLines` loads everything into memory — for gigabyte files stream with `Files.lines` instead.
- `Files.lines` returns a `Stream<Path>` backed by an open file handle; always close it (try-with-resources) or you leak file descriptors on Windows.
- `Files.write` silently truncates; use `APPEND`/`CREATE`/`TRUNCATE_EXISTING` `StandardOpenOption`s explicitly for other behaviors.
- `Files.createTempDirectory` vs `createTempFile` return different types; both default to the system temp dir unless you pass a `Path`.
- `Files.walk` includes the root — relative paths and reverse-order deletion are common workarounds, as shown above.
- Paths are just names; `exists()`/`isDirectory()` do stat calls and can be stale — for atomic checks use `readAttributes`. And on Windows a file held open (reader/writer) can't be deleted or moved until closed — close streams first.
