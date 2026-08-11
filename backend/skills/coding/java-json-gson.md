---
lang: java
keywords: json, gson, jackson, serialize, deserialize, TypeToken, toJson, fromJson, api response
---

# JSON with Gson

Gson maps Java objects to/from JSON in one line. Use `TypeToken` for generic collections, a `GsonBuilder` for pretty output, and Gson 2.10+ for records. Add the dependency below; Jackson (`com.fasterxml.jackson.core:jackson-databind`) is the drop-in alternative.

```java
import com.google.gson.*;
import com.google.gson.reflect.TypeToken;
import java.util.*;

public class GsonDemo {
    record User(String name, int age, List<String> tags) {}

    public static void main(String[] args) {
        Gson gson = new GsonBuilder().setPrettyPrinting().create();

        // object -> JSON
        User ada = new User("Ada", 36, List.of("math", "compilers"));
        String json = gson.toJson(ada);
        System.out.println(json);

        // JSON -> object (Gson 2.10+ supports records natively)
        User back = gson.fromJson(json, User.class);
        System.out.println(back);

        // generic collections need a TypeToken to preserve the element type
        String listJson = "[{\"name\":\"A\",\"age\":1,\"tags\":[]},{\"name\":\"B\",\"age\":2,\"tags\":[\"x\"]}]";
        List<User> users = gson.fromJson(listJson, new TypeToken<List<User>>() {}.getType());
        System.out.println("count=" + users.size() + " last=" + users.get(1).name());

        // parse into a generic map — JSON numbers come back as Double
        Map<String, Object> any = gson.fromJson("{\"price\":9.99}",
            new TypeToken<Map<String, Object>>() {}.getType());
        System.out.println(any);
    }
}
```

Add to `pom.xml` (or `implementation 'com.google.code.gson:gson:2.11.0'` in Gradle):

```xml
<dependency>
  <groupId>com.google.code.gson</groupId>
  <artifactId>gson</artifactId>
  <version>2.11.0</version>
</dependency>
```

Gotchas:
- `gson.fromJson(json, List.class)` gives `List<LinkedHashMap>` — raw type erasure loses the element type; always pass a `TypeToken` for generics.
- Gson is lenient by default: it accepts malformed input quietly. Use `JsonParser.parseString` or `Strictness`/Jackson if you need strict validation.
- Records: `toJson`/`fromJson` work on Gson 2.10+; older Gson serializes records via reflection poorly (field-less!). Upgrade or use a Jackson `ObjectMapper`.
- Field names map 1:1 with JSON keys; rename with `@SerializedName("other_name")`.
- Dates default to a numeric epoch/ISO format you may not want — configure `setDateFormat` or a custom adapter.
- `Map<String, Object>` values come back as `Double` for JSON numbers and `LinkedHashMap` for objects — cast with care.
