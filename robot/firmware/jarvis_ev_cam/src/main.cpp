/*
 *  JARVIS EV / MIMO  —  ESP32-CAM firmware  v0.2
 *  ==============================================
 *  A QBIT-bodied desk companion with the camera ON the body:
 *  the head tilts (SG90) and the ESP32-CAM streams JPEG over WiFi,
 *  so MIMO's eyes physically move with his body and he can see
 *  what you're doing at the desk.
 *
 *  HARDWARE  (AI-Thinker ESP32-CAM, PSRAM version)
 *    Camera:       OV2640, on the 15 dedicated camera pins (see below)
 *    OLED:         0.96" SSD1306 128x64, I2C SDA=GPIO15 SCL=GPIO14, addr 0x3C
 *    Servo:        SG90 head tilt, signal=GPIO13
 *    Touch:        TTP223, OUT=GPIO16 (digital HIGH when touched)
 *    Buzzer:       passive, GPIO17 (LEDC PWM)
 *    Speaker amp:  MAX98357A I2S — RESERVED pins BCLK=2 LRC=4 DIN=3
 *                  (not driven yet; PC TTS is MIMO's voice for now)
 *    Flash LED:    GPIO4 repurposed for I2S LRC later (flash unused)
 *
 *  WIRING TABLE (see robot/docs/PROTOCOL.md for protocol)
 *    ESP32-CAM              OLED   Servo  Touch  Buzzer
 *    GPIO15 (SDA)  ------>  SDA
 *    GPIO14 (SCL)  ------>  SCL
 *    GPIO13        ------>        orange
 *    GPIO16        ------>               OUT
 *    GPIO17        ------>                      +
 *    3V3 / GND     ------>  VCC/GND  +/GND   VCC/GND  -/GND
 *
 *  CAMERA PINS (fixed by the board layout, do not change):
 *    PWDN=32 RESET=-1 XCLK=0  SIOD=26 SIOC=27
 *    D7=35 D6=34 D5=39 D4=36 D3=21 D2=19 D1=18 D0=5
 *    VSYNC=25 HREF=23 PCLK=22
 *
 *  ENDPOINTS (WiFi, port 80)
 *    GET /                  status page (HTML)
 *    GET /cam.jpg           latest JPEG frame (agent polls this)
 *    GET /stream            MJPEG stream (browser test: http://<ip>/stream)
 *    GET /servo?angle=0..180  move head servo
 *
 *  BACKEND
 *    Polls GET /api/robot/poll every 2s (auth: X-Jarvis-Token).
 *    Commands: eye <expr>  |  blip <freq> <ms>  |  status  |  look <angle>
 *    Touch events POST to /api/robot/poke.
 *
 *  PLATFORMIO SETUP
 *    1. Edit platformio.ini: set WIFI_SSID, WIFI_PASS, BACKEND_HOST, API_TOKEN
 *    2. pio run --target upload
 *    3. pio device monitor   (debug output)
 *    4. Open http://<board-ip>/stream in a browser to verify the camera.
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include "esp_camera.h"

// ── PIN MAP ──────────────────────────────────────────────────
#define PIN_SDA       15
#define PIN_SCL       14
#define PIN_TOUCH     16
#define PIN_BUZZER    17
#define PIN_SERVO     13
#define PIN_I2S_BCLK  2     // reserved (MAX98357A) — not driven yet
#define PIN_I2S_LRC   4     // reserved — repurposes the flash LED pin
#define PIN_I2S_DIN   3     // reserved

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

// ── CAMERA ───────────────────────────────────────────────────
#define CAM_FRAME_SIZE  FRAMESIZE_VGA    // 640x480 — good for MediaPipe
#define CAM_JPEG_QUALITY 12              // 10-12 keeps it low-latency

// ── GLOBALS ──────────────────────────────────────────────────
Adafruit_SSD1306 display(OLED_W, OLED_H, &Wire, -1);

// face state
String currentExpr = "idle";
bool   blinkActive = false;
unsigned long blinkEnd = 0;
unsigned long lastBlink = 0;
long   blinkInterval = 4000;
bool   exprChanged = true;
unsigned long talkEnd = 0;   // when "talk" mouth animation expires → idle

// touch state
volatile bool touchTriggered = false;
unsigned long lastTouchDebounce = 0;

// polling
unsigned long lastPoll = 0;
const unsigned long POLL_INTERVAL = 2000;  // 2 seconds

// servo state
Servo headServo;
int   servoAngle = 90;        // home = straight ahead
unsigned long lastGlance = 0;
long  glanceInterval = 30000; // first idle glance ~30s after boot

// ── OLED FACE DRAWING ────────────────────────────────────────
// Same expression engine as the ESP32-C3 version.

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

// ── SERVO (head tilt) ────────────────────────────────────────
void servoSet(int angle) {
    servoAngle = constrain(angle, 0, 180);
    headServo.write(servoAngle);
}

// A gentle idle glance now and then, so the head isn't a statue.
void idleGlance() {
    int wander = random(-25, 26);
    servoSet(90 + wander);
    Serial.printf("glance -> %d\n", servoAngle);
}

// ── CAMERA + WEB SERVER ──────────────────────────────────────
WebServer server(80);

void initCamera() {
    camera_config_t config;
    memset(&config, 0, sizeof(config));
    config.pin_pwdn    = 32;
    config.pin_reset   = -1;
    config.pin_xclk    = 0;
    config.pin_sccb_sda = 26;
    config.pin_sccb_scl = 27;
    config.pin_d7      = 35;
    config.pin_d6      = 34;
    config.pin_d5      = 39;
    config.pin_d4      = 36;
    config.pin_d3      = 21;
    config.pin_d2      = 19;
    config.pin_d1      = 18;
    config.pin_d0      = 5;
    config.pin_vsync   = 25;
    config.pin_href    = 23;
    config.pin_pclk    = 22;
    config.xclk_freq_hz = 20000000;
    // Timer/channel 1, NOT 0 — ESP32Servo + the buzzer grab LEDC channel 0,
    // and a shared channel would kill the camera clock.
    config.ledc_timer  = LEDC_TIMER_1;
    config.ledc_channel = LEDC_CHANNEL_1;
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size  = CAM_FRAME_SIZE;
    config.jpeg_quality = CAM_JPEG_QUALITY;
    config.fb_count    = 2;
#if defined(BOARD_HAS_PSRAM)
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.grab_mode   = CAMERA_GRAB_LATEST;
#endif

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("camera init FAILED: 0x%x — check PSRAM/board type\n", err);
        return;
    }

    // slightly favour speed over sharpness for live tracking
    sensor_t *s = esp_camera_sensor_get();
    if (s) {
        s->set_framesize(s, CAM_FRAME_SIZE);
        s->set_quality(s, CAM_JPEG_QUALITY);
        s->set_brightness(s, 0);
        // uncomment to flip/swap the image to match mounting:
        // s->set_vflip(s, 1);
        // s->set_hmirror(s, 1);
    }
    Serial.println("camera OK");
}

// Latest JPEG frame — this is what the PC agent polls.
void handleCamJpg() {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
        server.send(503, "text/plain", "no frame");
        return;
    }
    server.send(200, "image/jpeg", fb->buf, fb->len);
    esp_camera_fb_return(fb);
}

// Browser MJPEG stream (test: http://<ip>/stream)
void handleStream() {
    WiFiClient client = server.client();
    client.setTimeout(5);
    const char *boundary = "frame";
    client.print("HTTP/1.1 200 OK\r\n");
    client.print("Content-Type: multipart/x-mixed-replace; boundary=");
    client.print(boundary);
    client.print("\r\n\r\n");
    while (client.connected()) {
        camera_fb_t *fb = esp_camera_fb_get();
        if (!fb) { delay(10); continue; }
        client.print("--");
        client.print(boundary);
        client.print("\r\nContent-Type: image/jpeg\r\nContent-Length: ");
        client.print(fb->len);
        client.print("\r\n\r\n");
        client.write(fb->buf, fb->len);
        client.print("\r\n");
        esp_camera_fb_return(fb);
        delay(0);
    }
}

void handleServo() {
    int angle = server.arg("angle").toInt();
    if (server.arg("angle").length() == 0) {
        server.send(200, "text/plain", String(servoAngle));
        return;
    }
    servoSet(angle);
    server.send(200, "text/plain", "ok " + String(servoAngle));
}

void handleRoot() {
    String html = F(
        "<!doctype html><html><head><meta charset=utf-8>"
        "<title>MIMO</title></head><body>"
        "<h1>MIMO — ESP32-CAM</h1>");
    html += "<p>IP: <b>" + WiFi.localIP().toString() + "</b></p>";
    html += "<p>Uptime: <b>" + String(millis() / 1000) + "s</b></p>";
    html += "<p>Face: <b>" + currentExpr + "</b> | Servo: <b>" + String(servoAngle) + "&deg;</b></p>";
    html += F("<p><a href=/cam.jpg>Snapshot</a> &middot; "
              "<a href=/stream>Stream</a> &middot; "
              "<a href=/servo?angle=90>Home servo</a></p></body></html>");
    server.send(200, "text/html", html);
}

void handleNotFound() {
    server.send(404, "text/plain", "not found");
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
    } else if (action == "look") {
        int angle = cmd["angle"] | 90;
        servoSet(angle);
        Serial.printf("look -> %d\n", servoAngle);
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
    if (action == "look") res["angle"] = servoAngle;
    String body;
    serializeJson(res, body);
    post.POST(body);
    post.end();

    return true;
}

// Post a touch event to the backend (MIMO pokes the user back!)
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
    Serial.println("JARVIS EV / MIMO v0.2 (ESP32-CAM) starting");

    // camera first — the AI-Thinker pins are fixed by the board
    initCamera();

    // OLED
    Wire.begin(PIN_SDA, PIN_SCL);
    if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
        Serial.println("OLED init failed");
    }
    display.clearDisplay();
    renderFace();

    // Buzzer (LEDC channel)
    ledcAttach(PIN_BUZZER, 2000, 8);

    // Head servo — home it to center
    headServo.attach(PIN_SERVO, 500, 2500);
    servoSet(90);

    // Touch sensor (interrupt on rising edge = touch detected)
    pinMode(PIN_TOUCH, INPUT);
    attachInterrupt(digitalPinToInterrupt(PIN_TOUCH), onTouch, RISING);

    // Web server
    server.on("/", handleRoot);
    server.on("/cam.jpg", handleCamJpg);
    server.on("/stream", handleStream);
    server.on("/servo", handleServo);
    server.onNotFound(handleNotFound);
    server.begin();
    Serial.println("http server up");

    // startup chime
    blip(880, 60);
    delay(90);
    blip(1318, 60);

    // WiFi (after chime so the boot blips aren't delayed by WiFi)
    connectWifi();

    Serial.println("ready — MIMO online, Sir.");
}

// ── LOOP ─────────────────────────────────────────────────────
void loop() {
    unsigned long now = millis();

    // serve HTTP (camera + servo) — fast so polling stays responsive
    server.handleClient();

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

    // idle glance so the head moves even when nobody's commanding it
    if (now - lastGlance >= (unsigned long)glanceInterval) {
        lastGlance = now;
        glanceInterval = random(25000, 50000);
        idleGlance();
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
