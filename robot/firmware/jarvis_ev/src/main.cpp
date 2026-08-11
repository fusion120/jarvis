/*
 *  JARVIS EV  —  ESP32-C3 Super Mini firmware  v0.1
 *  =================================================
 *  A QBIT-bodied desk companion that SEES you (via your PC webcam),
 *  TALKS to you (I2S speaker), and reacts with an OLED face.
 *  Think: EV from Spider-Man, but on your desk.
 *
 *  HARDWARE
 *    ESP32-C3 Super Mini  (WiFi, I2C, I2S, PWM)
 *    SSD1306 128x64 OLED  (I2C: SDA=GPIO20, SCL=GPIO21, addr 0x3C)
 *    TTP223 touch sensor  (OUT=GPIO1, digital HIGH when touched)
 *    Passive buzzer       (GPIO2, PWM via LEDC)
 *    MAX98357A I2S amp    (BCLK=GPIO4, LRC=GPIO5, DIN=GPIO3)
 *    28mm speaker         (connected to MAX98357A output)
 *
 *  PLATFORMIO SETUP
 *    1. Edit platformio.ini: set WIFI_SSID, WIFI_PASS, BACKEND_HOST
 *    2. pio run --target upload
 *    3. pio device monitor (to see debug output)
 *
 *  PROTOCOL
 *    The robot polls GET /api/robot/poll every 2s.
 *    Backend returns JSON: {"command":"eye","expression":"happy"} or null.
 *    Robot executes, posts result to POST /api/robot/result.
 *    Touch events POST to /api/robot/poke.
 *
 *  See robot/docs/PROTOCOL.md for the full command list.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ArduinoJson.h>

// ── PIN MAP ──────────────────────────────────────────────────
#define PIN_SDA       20
#define PIN_SCL       21
#define PIN_TOUCH     1
#define PIN_BUZZER    2
#define PIN_I2S_DIN   3
#define PIN_I2S_BCLK  4
#define PIN_I2S_LRC   5
#define PIN_SERVO     6     // V2: head tilt servo

#define OLED_W        128
#define OLED_H        64
#define OLED_ADDR     0x3C

// ── WIFI / BACKEND ───────────────────────────────────────────
#ifndef WIFI_SSID
#define WIFI_SSID     "YOUR_WIFI"
#endif
#ifndef WIFI_PASS
#define WIFI_PASS     "YOUR_PASSWORD"
#endif
#ifndef BACKEND_HOST
#define BACKEND_HOST  "jarvis-3hff.onrender.com"
#endif
#ifndef BACKEND_PORT
#define BACKEND_PORT  443
#endif
#ifndef BACKEND_SSL
#define BACKEND_SSL   1
#endif
// API token — same API_SECRET as the dashboard. Sent as X-Jarvis-Token.
#ifndef API_TOKEN
#define API_TOKEN     "YOUR_API_SECRET"
#endif

// ── GLOBALS ──────────────────────────────────────────────────
Adafruit_SSD1306 display(OLED_W, OLED_H, &Wire, -1);

// expression state
String currentExpr = "idle";
bool   blinkActive = false;
unsigned long blinkEnd = 0;
unsigned long lastBlink = 0;
long   blinkInterval = 4000;
bool   exprChanged = true;
unsigned long talkEnd = 0;   // when "talk" mouth animation expires → back to idle

// touch state
volatile bool touchTriggered = false;
unsigned long lastTouchDebounce = 0;

// polling
unsigned long lastPoll = 0;
const unsigned long POLL_INTERVAL = 2000;  // 2 seconds

// ── OLED FACE DRAWING ────────────────────────────────────────
// Same expression engine as the Arduino version.

void drawEyes(int cx, int cy, int r, const String &mode) {
    if (mode == "happy") {
        display.fillCircle(cx, cy, r, WHITE);
        display.fillRect(cx - r, cy, r * 2, r, BLACK);
    } else if (mode == "sad") {
        display.fillCircle(cx, cy, r, WHITE);
        display.fillRect(cx - r, cy - r, r * 2, r, BLACK);
    } else if (mode == "sleep") {
        display.fillRect(cx - r, cy - 2, r * 2, 4, WHITE);
    } else if (mode == "x") {
        display.drawLine(cx - r, cy - r, cx + r, cy + r, WHITE);
        display.drawLine(cx - r, cy + r, cx + r, cy - r, WHITE);
    } else if (mode == "blink") {
        display.fillRect(cx - r + 3, cy - 1, r * 2 - 6, 3, WHITE);
    } else if (mode == "curious") {
        display.fillCircle(cx, cy, r, WHITE);
        display.fillCircle(cx + 4, cy - 2, r / 3, BLACK);
        display.fillRect(cx - r + 2, cy - r - 5, r * 2 - 4, 3, WHITE);
    } else {
        // idle / open
        display.fillCircle(cx, cy, r, WHITE);
        display.fillCircle(cx, cy, r / 3, BLACK);
    }
}

void renderFace() {
    display.clearDisplay();
    String mode = blinkActive ? "blink" : currentExpr;
    if (mode == "talk") {
        // animated mouth under the eyes for ~3s, then settle back to idle
        unsigned long now = millis();
        if (now >= talkEnd) {
            currentExpr = "idle";
            mode = "idle";
        } else {
            int open = ((now / 100) % 2) == 0 ? 6 : 2;   // ~5Hz square-wave mouth
            display.fillRect(48, 48, 32, open, WHITE);   // centered under both eyes
        }
    }
    drawEyes(40, 26, 12, mode);
    drawEyes(88, 26, 12, mode);
    display.display();
}

// ── BUZZER ───────────────────────────────────────────────────
void blip(int freq, int ms) {
    if (freq <= 0 || ms <= 0) return;
    ledcWriteTone(PIN_BUZZER, freq);
    delay(ms);
    ledcWriteTone(PIN_BUZZER, 0);
}

// ── WIFI ─────────────────────────────────────────────────────
void connectWifi() {
    Serial.printf("connecting to %s", WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    int tries = 0;
    while (WiFi.status() != WL_CONNECTED && tries < 40) {
        delay(500);
        Serial.print(".");
        tries++;
    }
    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\nconnected! IP: %s\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println("\nWiFi failed — will retry");
    }
}

// ── BACKEND COMMS ────────────────────────────────────────────
String backendUrl(const char *path) {
    String scheme = BACKEND_SSL ? "https" : "http";
    return scheme + "://" + BACKEND_HOST + ":" + String(BACKEND_PORT) + path;
}

// Attach the shared auth token so the backend accepts the request.
void addAuth(HTTPClient &http) {
    http.addHeader("X-Jarvis-Token", API_TOKEN);
}

// Poll the backend for a robot command. Returns true if a command was received.
bool pollBackend() {
    if (WiFi.status() != WL_CONNECTED) return false;

    HTTPClient http;
    String url = backendUrl("/api/robot/poll");
    http.begin(url);
    addAuth(http);
    http.setTimeout(5000);
    int code = http.GET();
    if (code != 200) {
        http.end();
        return false;
    }

    String payload = http.getString();
    http.end();

    JsonDocument doc;
    if (deserializeJson(doc, payload)) return false;

    JsonObject cmd = doc["command"];
    if (cmd.isNull()) return false;

    String action = cmd["action"] | "";

    if (action == "eye") {
        String expr = cmd["expression"] | "idle";
        if (expr == "blink") {
            blinkActive = true;
            blinkEnd = millis() + 130;
        } else {
            currentExpr = expr;
            exprChanged = true;
            if (expr == "talk") {
                talkEnd = millis() + 3000;   // mouth animates ~3s, then idle
            }
        }
        Serial.printf("eye -> %s\n", expr.c_str());
    } else if (action == "blip") {
        int freq = cmd["freq"] | 880;
        int ms = cmd["ms"] | 80;
        blip(freq, ms);
        Serial.printf("blip %dHz %dms\n", freq, ms);
    } else if (action == "status") {
        // backend just wants to know we're alive
    }

    // post result
    HTTPClient post;
    post.begin(backendUrl("/api/robot/result"));
    post.addHeader("Content-Type", "application/json");
    addAuth(post);
    JsonDocument res;
    res["ok"] = true;
    res["action"] = action;
    String body;
    serializeJson(res, body);
    post.POST(body);
    post.end();

    return true;
}

// Post a touch event to the backend (EV pokes the user back!)
void postPoke() {
    if (WiFi.status() != WL_CONNECTED) return;
    HTTPClient http;
    http.begin(backendUrl("/api/robot/poke"));
    http.addHeader("Content-Type", "application/json");
    addAuth(http);
    http.POST("{\"event\":\"touch\"}");
    http.end();
    Serial.println("poke sent");
}

// ── TOUCH INTERRUPT ──────────────────────────────────────────
void IRAM_ATTR onTouch() {
    touchTriggered = true;
}

// ── SETUP ────────────────────────────────────────────────────
void setup() {
    Serial.begin(115200);
    Serial.println("JARVIS EV v0.1 starting");

    // OLED
    Wire.begin(PIN_SDA, PIN_SCL);
    if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
        Serial.println("OLED init failed");
    }
    display.clearDisplay();
    renderFace();

    // Buzzer (LEDC channel 0)
    ledcAttach(PIN_BUZZER, 2000, 8);

    // Touch sensor (interrupt on rising edge = touch detected)
    pinMode(PIN_TOUCH, INPUT);
    attachInterrupt(digitalPinToInterrupt(PIN_TOUCH), onTouch, RISING);

    // startup chime
    blip(880, 60);
    delay(90);
    blip(1318, 60);

    // WiFi
    connectWifi();

    Serial.println("ready — Jarvis EV online, Sir.");
}

// ── LOOP ─────────────────────────────────────────────────────
void loop() {
    unsigned long now = millis();

    // natural idle blinks
    if (!blinkActive && now - lastBlink > (unsigned long)blinkInterval) {
        blinkActive = true;
        blinkEnd = now + 130;
    }
    if (blinkActive && now > blinkEnd) {
        blinkActive = false;
        lastBlink = now;
        blinkInterval = random(3000, 8000);
    }

    // redraw face (~30fps)
    static unsigned long lastDraw = 0;
    if (exprChanged || blinkActive || now - lastDraw >= 33) {
        lastDraw = now;
        renderFace();
        exprChanged = false;
    }

    // touch → poke backend
    if (touchTriggered && now - lastTouchDebounce > 1000) {
        touchTriggered = false;
        lastTouchDebounce = now;
        blip(1200, 40);
        postPoke();
    }

    // poll backend for commands
    if (now - lastPoll >= POLL_INTERVAL) {
        lastPoll = now;
        pollBackend();
    }

    // reconnect WiFi if dropped
    if (WiFi.status() != WL_CONNECTED) {
        static unsigned long lastReconnect = 0;
        if (now - lastReconnect > 30000) {
            lastReconnect = now;
            Serial.println("WiFi reconnecting...");
            connectWifi();
        }
    }
}
