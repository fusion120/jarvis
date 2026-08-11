---
lang: java
keywords: http client, http, rest api, sendAsync, HttpResponse, BodyHandlers, web request, http request, timeout
---

# java.net.http.HttpClient

The JDK's built-in `HttpClient` sends HTTP/1.1 and HTTP/2 requests with sync or async APIs, timeouts, redirects, and custom headers — no third-party dependency needed. Pair `sendAsync` with `CompletableFuture` for non-blocking REST calls.

```java
import java.net.URI;
import java.net.http.*;
import java.time.Duration;
import java.util.concurrent.*;

public class HttpClientDemo {
    public static void main(String[] args) throws Exception {
        HttpClient client = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5))
            .followRedirects(HttpClient.Redirect.NORMAL) // follow 3xx only
            .version(HttpClient.Version.HTTP_2)
            .build();

        HttpRequest req = HttpRequest.newBuilder(URI.create("https://api.github.com/zen"))
            .timeout(Duration.ofSeconds(10))
            .header("Accept", "application/json")
            .header("User-Agent", "java-http-demo")
            .GET()
            .build();

        // synchronous — blocks the calling thread
        HttpResponse<String> resp = client.send(req, HttpResponse.BodyHandlers.ofString());
        System.out.println("status=" + resp.statusCode());
        System.out.println("headers: " + resp.headers().firstValue("content-type").orElse("?"));
        System.out.println("body: " + resp.body());

        // asynchronous — returns immediately, callback on completion
        CompletableFuture<HttpResponse<String>> future =
            client.sendAsync(req, HttpResponse.BodyHandlers.ofString());
        future.thenApply(HttpResponse::body)
              .thenAccept(System.out::println)
              .join(); // wait for the pipeline

        // JSON POST with a request body
        HttpRequest post = HttpRequest.newBuilder(URI.create("https://httpbin.org/post"))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString("{\"q\":\"jarvis\"}"))
            .build();
        HttpResponse<String> postResp = client.send(post, HttpResponse.BodyHandlers.ofString());
        System.out.println("POST status=" + postResp.statusCode());
    }
}
```

Gotchas:
- `HttpClient` is immutable and thread-safe — build one and reuse it; do not construct per request.
- `send` blocks the thread; `sendAsync` runs on the common pool — use a dedicated executor for many concurrent calls.
- Timeouts are on connect and on the whole request; without them a dead server hangs your thread indefinitely.
- `BodyHandlers.ofString()` assumes UTF-8 for text; binary payloads need `ofByteArray()`/`ofInputStream()`.
- A non-2xx status is NOT an exception — always check `statusCode()`; use a custom handler or `BodyHandlers.ofString()` + manual error mapping.
- HTTP/2 is negotiated per connection; some servers fall back to HTTP/1.1, but `HTTP_2` with a failing TLS handshake throws. Proxy/TLS config lives on the client builder (`proxy(...)`, `sslContext(...)`), not on the request.
