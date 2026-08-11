---
lang: java
keywords: tcp socket, server socket, client, connection, socket io, echo server, accept, printwriter, bufferedreader
---

# TCP Socket Server & Client

`ServerSocket.accept()` blocks until a client connects; each accepted `Socket` is a bidirectional byte stream. For text protocols, wrap streams in `BufferedReader`/`PrintWriter` with an explicit charset, and always close on both ends to unblock the peer's `read`.

```java
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;

public class TcpSocketDemo {
    public static void main(String[] args) throws Exception {
        int port = 9_999;

        Thread server = new Thread(() -> {
            try (ServerSocket ss = new ServerSocket(port)) {
                System.out.println("listening on " + port);
                // handle ONE client; loop accept() for many
                try (Socket sock = ss.accept();
                     BufferedReader in = new BufferedReader(new InputStreamReader(
                         sock.getInputStream(), StandardCharsets.UTF_8));
                     PrintWriter out = new PrintWriter(new OutputStreamWriter(
                         sock.getOutputStream(), StandardCharsets.UTF_8), true)) {
                    String line;
                    while ((line = in.readLine()) != null) {
                        out.println("echo: " + line); // autoFlush=true flushes each println
                    }
                    System.out.println("client disconnected");
                }
            } catch (IOException e) {
                System.err.println("server error: " + e.getMessage());
            }
        });
        server.start();
        Thread.sleep(300);

        // client side
        try (Socket sock = new Socket("localhost", port);
             PrintWriter out = new PrintWriter(new OutputStreamWriter(
                 sock.getOutputStream(), StandardCharsets.UTF_8), true);
             BufferedReader in = new BufferedReader(new InputStreamReader(
                 sock.getInputStream(), StandardCharsets.UTF_8))) {
            out.println("hello");
            System.out.println("server said: " + in.readLine());
            out.println("bye");
            System.out.println("server said: " + in.readLine());
        } // closing the socket ends the connection, server's readLine() returns null

        server.join();
    }
}
```

Gotchas:
- `accept()` returns one connection at a time — a single-threaded server stalls while it reads; spawn a thread or executor per connection for concurrency.
- Pick the charset explicitly (`UTF_8`); default charset differs across platforms and mangles text.
- `PrintWriter` swallows I/O errors silently (check `checkError()`), unlike `BufferedWriter` — for reliable protocols use `DataOutputStream`/raw `OutputStream`.
- `readLine()` returns `null` only at end-of-stream; the peer must close (or shutdownOutput) for the reader to unblock — a half-open connection hangs forever.
- TCP is a stream, not a message boundary: one `write` can arrive split or coalesced. Add framing (newline, length-prefix) to your protocol.
- `Socket.setSoTimeout` prevents a read from blocking forever; without it a dead peer stalls the thread indefinitely.
