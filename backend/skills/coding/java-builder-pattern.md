---
lang: java
keywords: builder, fluent, immutable, constructor, chaining, design pattern, defensive copy, builder pattern, fluent api
---

# Builder Pattern

A builder solves the problem of constructors with many optional parameters and makes objects immutable (all fields `final`, set once in `build()`). The fluent API reads like named arguments and validates in one place. Use it for config objects, HTTP requests, and DTOs with optional fields.

```java
import java.util.*;

public class BuilderPattern {
    public static final class HttpRequest {
        private final String url;
        private final String method;
        private final Map<String, String> headers; // immutable snapshot
        private final byte[] body;

        private HttpRequest(Builder b) {
            url = b.url;
            method = b.method;
            headers = Map.copyOf(b.headers);   // defensive copy at build time
            body = Arrays.copyOf(b.body, b.body.length);
        }

        public static Builder builder(String url) {
            return new Builder(url);
        }

        @Override
        public String toString() {
            return method + " " + url + " " + headers + " body=" + body.length + "B";
        }
    }

    public static final class Builder {
        private final String url;                       // required, set in factory
        private String method = "GET";                   // defaulted
        private final Map<String, String> headers = new LinkedHashMap<>();
        private byte[] body = new byte[0];

        private Builder(String url) { this.url = Objects.requireNonNull(url); }

        public Builder method(String m) { this.method = m; return this; }
        public Builder header(String k, String v) { headers.put(k, v); return this; }
        public Builder body(byte[] b) { this.body = Arrays.copyOf(b, b.length); return this; }

        public HttpRequest build() {
            if (url.isBlank()) throw new IllegalStateException("url is required");
            return new HttpRequest(this);
        }
    }

    public static void main(String[] args) {
        HttpRequest req = HttpRequest.builder("https://api.example.com/users")
            .method("POST")
            .header("Content-Type", "application/json")
            .header("Authorization", "Bearer abc")
            .body("{\"name\":\"Ada\"}".getBytes())
            .build();
        System.out.println(req);
    }
}
```

Gotchas:
- The builder can be *reused* to make several objects, but shared mutable collections must be copied in `build()` (as above) or all instances alias the same map/array.
- Validate in `build()`, not per setter — otherwise an invalid object can be partially built and the error surfaces in a confusing place.
- Required fields belong in the `builder()` factory's parameters so they can't be forgotten; optional ones are setters.
- Returning `this` from every setter is what makes chaining work; forgetting `return this` silently produces null in a chain.
- Builders add code — for 2-3 fields a builder is over-engineering; use a record/constructor with overloads instead.
- The built object's constructor should be `private` so clients can't bypass validation, and immutability is only as strong as the defensive copies (`Map.copyOf`/`Arrays.copyOf`) made at build time.
