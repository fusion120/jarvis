---
lang: cpp
keywords: esp32, buzzer, tone, beep, ledc, pwm
---
# Beep a passive buzzer (ESP32 LEDC)

A passive buzzer needs a square wave to make sound — drive it with PWM.

```cpp
#define BUZZER_PIN 2

void setup() {
    ledcAttach(BUZZER_PIN, 2000, 8);     // freq, resolution bits
}

void beep(int freq, int ms) {
    ledcWriteTone(BUZZER_PIN, freq);     // start tone
    delay(ms);
    ledcWriteTone(BUZZER_PIN, 0);        // silence
}

void loop() {
    beep(880, 100);    // A5
    delay(100);
    beep(1318, 100);   // E6 — a little chime
    delay(1000);
}
```

Gotchas:
- Passive buzzer = PWM tone; active buzzer = just `digitalWrite(HIGH)`.
- On classic Arduino Uno this is `tone(pin, freq, ms)` — no LEDC needed.
- Keep tones short (≤500 ms) or they're annoying; chain two notes for a chime.
- `ledcWriteTone` replaces `tone()` on ESP32; the channel count is limited,
  don't attach too many PWM users.
