---
lang: cpp
keywords: arduino, sensor, analogread, digitalread, button, debounce, dht, ultrasonic
---
# Read sensors on an Arduino

Two kinds of inputs: analog (potentiometer, LDR, temp) and digital (button, PIR).

Analog input (a potentiometer → serial):

```cpp
const int POT = A0;
void setup() {
    Serial.begin(9600);
}
void loop() {
    int val = analogRead(POT);      // 0..1023
    Serial.println(val);
    delay(200);
}
```

Button with software debounce (ignore the bouncy edges):

```cpp
const int BTN = 2;
bool last = HIGH;
unsigned long lastDebounce = 0;
const unsigned long debounceMs = 50;

void setup() { pinMode(BTN, INPUT_PULLUP); Serial.begin(9600); }

void loop() {
    bool read = digitalRead(BTN);           // PULLUP: HIGH=released, LOW=pressed
    if (read != last) {
        lastDebounce = millis();
        last = read;
    }
    if (millis() - lastDebounce > debounceMs && read == LOW) {
        Serial.println("pressed");
    }
}
```

Gotchas: `INPUT_PULLUP` means the button is LOW when pressed — don't wire an
external pulldown too. `analogRead` is 10-bit (0–1023). Never `delay()` long
inside `loop()` if you also read buttons — use `millis()` timing instead.
