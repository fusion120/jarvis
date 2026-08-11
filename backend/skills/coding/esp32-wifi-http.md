---
lang: cpp
keywords: esp32, wifi, http, api, json, get, post, server
---
# ESP32: connect to WiFi and talk HTTP

The pattern this repo's robot uses — poll a backend, run a command, POST back.

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

const char* SSID = "your_wifi";
const char* PASS = "your_password";

void setup() {
    Serial.begin(115200);
    WiFi.begin(SSID, PASS);
    int tries = 0;
    while (WiFi.status() != WL_CONNECTED && tries++ < 40) {
        delay(500); Serial.print(".");
    }
    Serial.println(WiFi.localIP().toString());
}

void loop() {
    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        http.begin("https://api.example.com/ping");
        http.addHeader("Content-Type", "application/json");
        http.addHeader("Authorization", "Bearer token");
        http.setTimeout(5000);
        int code = http.POST("{\"hello\":\"world\"}");
        if (code > 0) {
            Serial.println(http.getString());
        }
        http.end();
    }
    delay(2000);
}
```

Gotchas:
- For HTTPS, the ESP32 needs the root CA: `http.setInsecure(true)` is easiest
  for testing but not for production; prefer the site's CA cert.
- Don't block in `loop()` — if a poll can take seconds, use `millis()`-based
  timing so button/touch handling still works.
- Keep POST bodies small; ~2 KB is safe.
- Parse replies with ArduinoJson:
  `JsonDocument doc; deserializeJson(doc, payload); String expr = doc["expression"] | "idle";`
