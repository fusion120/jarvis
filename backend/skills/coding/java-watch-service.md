---
lang: java
keywords: watchservice, file watcher, watch directory, entry create, poll events, hot reload, file system events, register
---

# WatchService: Watching File Changes

`WatchService` notifies you of file create/modify/delete events in a directory — the foundation of hot-reload, log tailers, and build triggers. Register the directory, block on `take()`/`poll()`, inspect `kind` and `context`, and always `reset()` the key or watching stops.

```java
import java.nio.file.*;
import java.util.concurrent.TimeUnit;
import static java.nio.file.StandardWatchEventKinds.*;

public class WatchServiceDemo {
    public static void main(String[] args) throws Exception {
        Path dir = Files.createTempDirectory("watch-me");
        try (WatchService watcher = FileSystems.getDefault().newWatchService()) {
            // register for create/modify/delete — not recursive by default
            dir.register(watcher, ENTRY_CREATE, ENTRY_MODIFY, ENTRY_DELETE);

            // a writer thread producing the events
            Thread writer = new Thread(() -> {
                try {
                    for (int i = 1; i <= 3; i++) {
                        Path p = dir.resolve("file-" + i + ".txt");
                        Files.writeString(p, "data " + i);
                        Thread.sleep(120);
                    }
                    Files.deleteIfExists(dir.resolve("file-2.txt"));
                } catch (Exception e) {
                    e.printStackTrace();
                }
            });
            writer.start();

            int expected = 4; // 3 creates + 1 delete
            int seen = 0;
            while (seen < expected) {
                WatchKey key = watcher.poll(3, TimeUnit.SECONDS); // null on timeout
                if (key == null) break;
                for (WatchEvent<?> event : key.pollEvents()) {
                    WatchEvent.Kind<?> kind = event.kind();
                    if (kind == OVERFLOW) continue; // events were dropped
                    Path changed = (Path) event.context(); // relative file name
                    System.out.println(kind.name() + ": " + changed);
                    seen++;
                }
                if (!key.reset()) break; // re-arm; false means the directory vanished
            }
            writer.join();
            System.out.println("events seen: " + seen);
        }
    }
}
```

Gotchas:
- WatchService is NOT recursive — subdirectory events require registering each subdirectory separately (walk the tree at startup).
- You must call `key.reset()` after draining a key or the directory stops being watched. `reset()` returns false if the path was deleted.
- `context()` is a relative `Path` (just the filename), not an absolute path — resolve against the registered directory.
- `OVERFLOW` means events were dropped (slow consumer, buffer full); skip it, never treat it as a file event.
- Events are delivered asynchronously — there's a delay between the FS change and your handler; don't race a read against a just-created file.
- `take()` blocks forever; use `poll(timeout)` if you also need to exit or do periodic work. And writing to a watched directory triggers your own `ENTRY_MODIFY` — guard against self-observer loops.
