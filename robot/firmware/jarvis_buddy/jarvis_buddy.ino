/*
 *  JARVIS BUDDY  —  Uno/Nano body firmware  v1.0
 *  =================================================
 *  A pan-tilt desk companion with an OLED face. Talks to the desktop agent
 *  over USB serial (protocol: see robot/docs/PROTOCOL.md).
 *
 *  WIRING (see robot/docs/BUILD_SPEC.md)
 *    Pan servo   signal -> D9      power -> 5V rail (external 5V/2A)
 *    Tilt servo  signal -> D10     power -> 5V rail (external 5V/2A)
 *    Servo GNDs  -> shared GND (tie to Uno GND!)
 *    OLED SDA -> A4   SCL -> A5   VCC -> 5V   GND -> GND
 *    Buzzer +  -> D3 (through 100 ohm)   Buzzer - -> GND
 *
 *  LIBRARIES (Arduino IDE -> Library Manager)
 *    - Adafruit SSD1306
 *    - Adafruit GFX
 *    (Servo is built in.)
 *
 *  TEST: open Serial Monitor @115200, send:  MOVE 45 60 500   /   EYE happy   /   BLINK
 */

#include <Servo.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define PAN_PIN    9
#define TILT_PIN   10
#define BUZZER_PIN 3
#define OLED_W     128
#define OLED_H     64
#define OLED_ADDR  0x3C

Adafruit_SSD1306 display(OLED_W, OLED_H, &Wire, -1);
Servo pan, tilt;

// ---- movement state ----
int panCur = 90, tiltCur = 90;
int panTgt = 90, tiltTgt = 90;
const int MOVE_STEP = 2;          // max degrees per tick
unsigned long lastStep = 0;
int stepDelay = 15;               // ms between ticks (MOVE tunes this)

// ---- face state ----
String expr = "idle";
bool blinkActive = false;
unsigned long blinkEnd = 0;
unsigned long lastBlink = 0;
long blinkInterval = 4000;
bool exprChanged = true;

// ---- serial ----
String cmd = "";

// =====================================================  SETUP
void setup() {
  Serial.begin(115200);
  pinMode(BUZZER_PIN, OUTPUT);
  randomSeed(analogRead(0));

  pan.attach(PAN_PIN);
  tilt.attach(TILT_PIN);
  pan.write(90);
  tilt.write(90);

  Wire.begin();                    // A4/A5 on Uno/Nano
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("ERR oled-not-found");
  }
  display.clearDisplay();
  renderFace();
  display.display();

  blip(880, 60);
  delay(90);
  blip(1318, 60);
  Serial.println("READY jarvis-buddy v1.0");
}

// =====================================================  LOOP
void loop() {
  unsigned long now = millis();

  // smooth servos
  if (now - lastStep >= (unsigned long)stepDelay) {
    lastStep = now;
    stepServos();
  }

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

  // redraw face (at ~30fps, or on state change)
  static unsigned long lastDraw = 0;
  if (exprChanged || blinkActive || now - lastDraw >= 33) {
    lastDraw = now;
    renderFace();
    exprChanged = false;
  }

  // serial
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') { handle(cmd); cmd = ""; }
    else if (c != '\r') cmd += c;
  }
}

// =====================================================  SERVOS
void stepServos() {
  if (panCur < panTgt) panCur = min(panCur + MOVE_STEP, panTgt);
  else if (panCur > panTgt) panCur = max(panCur - MOVE_STEP, panTgt);
  if (tiltCur < tiltTgt) tiltCur = min(tiltCur + MOVE_STEP, tiltTgt);
  else if (tiltCur > tiltTgt) tiltCur = max(tiltCur - MOVE_STEP, tiltTgt);
  pan.write(panCur);
  tilt.write(tiltCur);
}

void setMove(int p, int t, long ms) {
  panTgt = constrain(p, 0, 180);
  tiltTgt = constrain(t, 0, 180);
  if (ms >= 50) {
    long dist = max(abs(panTgt - panCur), abs(tiltTgt - tiltCur));
    int steps = (int)(dist / MOVE_STEP) + 1;
    stepDelay = (int)(ms / steps);
    stepDelay = constrain(stepDelay, 1, 80);
  } else {
    stepDelay = 15;
  }
}

// =====================================================  BUZZER
void blip(int freq, int ms) {
  if (freq <= 0 || ms <= 0) return;
  tone(BUZZER_PIN, freq, (unsigned long)ms);
}

// =====================================================  FACE
// Draws a pair of eyes centered on the 128x64 screen.
void renderFace() {
  display.clearDisplay();
  String mode = blinkActive ? "blink" : expr;
  drawEyes(40, 26, 12, mode);      // left eye
  drawEyes(88, 26, 12, mode);      // right eye
  display.display();
}

void drawEyes(int cx, int cy, int r, const String &mode) {
  if (mode == "happy") {
    // upward arcs  ^ ^
    display.fillCircle(cx, cy, r, WHITE);
    display.fillRect(cx - r, cy, r * 2, r, BLACK);      // hide bottom half -> cap shape
  } else if (mode == "sad") {
    // downward arcs  u u
    display.fillCircle(cx, cy, r, WHITE);
    display.fillRect(cx - r, cy - r, r * 2, r, BLACK);  // hide top half -> cup shape
  } else if (mode == "sleep") {
    // closed lines
    display.fillRect(cx - r, cy - 2, r * 2, 4, WHITE);
  } else if (mode == "x") {
    display.drawLine(cx - r, cy - r, cx + r, cy + r, WHITE);
    display.drawLine(cx - r, cy + r, cx + r, cy - r, WHITE);
  } else if (mode == "blink") {
    // eyelid line (shorter than sleep)
    display.fillRect(cx - r + 3, cy - 1, r * 2 - 6, 3, WHITE);
  } else if (mode == "curious") {
    // pupils shifted + raised brows
    display.fillCircle(cx, cy, r, WHITE);
    display.fillCircle(cx + 4, cy - 2, r / 3, BLACK);
    display.fillRect(cx - r + 2, cy - r - 5, r * 2 - 4, 3, WHITE);
  } else {
    // idle / open: round eye with centered pupil
    display.fillCircle(cx, cy, r, WHITE);
    display.fillCircle(cx, cy, r / 3, BLACK);
  }
}

// =====================================================  SERIAL COMMANDS
String upcase(const String &s) {
  String r = s;
  for (unsigned int i = 0; i < r.length(); i++) {
    if (r[i] >= 'a' && r[i] <= 'z') r[i] -= 32;
  }
  return r;
}

void handle(const String &raw) {
  String s = raw;
  s.trim();
  if (s.length() == 0) return;
  String tok = upcase(s.substring(0, s.indexOf(' ')));
  if (tok.length() == 0) tok = upcase(s);
  String args = s.substring(s.indexOf(' ') + 1);
  args.trim();

  if (tok == "PING") {
    Serial.println("PONG");
  } else if (tok == "POS") {
    int p, t;
    if (sscanf(args.c_str(), "%d %d", &p, &t) == 2) {
      panTgt = constrain(p, 0, 180);
      tiltTgt = constrain(t, 0, 180);
      stepDelay = 8;   // snap quickly
      Serial.println("OK pos");
    } else Serial.println("ERR bad args");
  } else if (tok == "MOVE") {
    int p, t; long ms = 400;
    int n = sscanf(args.c_str(), "%d %d %ld", &p, &t, &ms);
    if (n >= 2) {
      setMove(p, t, ms);
      Serial.println("OK move");
    } else Serial.println("ERR bad args");
  } else if (tok == "EYE") {
    args.toLowerCase();
    if (args == "idle" || args == "happy" || args == "sad" || args == "curious"
        || args == "blink" || args == "sleep" || args == "x") {
      if (args == "blink") { blinkActive = true; blinkEnd = millis() + 130; }
      else { expr = args; exprChanged = true; }
      Serial.println("OK eye=" + args);
    } else Serial.println("ERR unknown eye: " + args);
  } else if (tok == "BLINK") {
    blinkActive = true;
    blinkEnd = millis() + 130;
    Serial.println("OK blink");
  } else if (tok == "BLIP") {
    int f, d;
    if (sscanf(args.c_str(), "%d %d", &f, &d) == 2) {
      blip(f, d);
      Serial.println("OK beep");
    } else Serial.println("ERR bad args");
  } else if (tok == "STATUS") {
    Serial.print("OK pan="); Serial.print(panCur);
    Serial.print(" tilt="); Serial.print(tiltCur);
    Serial.print(" expr="); Serial.print(expr);
    Serial.print(" up="); Serial.println(millis() / 1000);
  } else if (tok == "RST") {
    panTgt = 90; tiltTgt = 90;
    stepDelay = 8;
    Serial.println("OK reset");
  } else {
    Serial.print("ERR unknown: ");
    Serial.println(raw);
  }
}
