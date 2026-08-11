---
lang: cpp
keywords: arduino, blink, led, uno, pin13
---
# Blink an LED on an Arduino

The hello-world of microcontrollers. Set a pin as output, toggle it forever.

```cpp
// blink.ino
const int LED = 13;      // built-in LED on the Uno

void setup() {
    pinMode(LED, OUTPUT);
}

void loop() {
    digitalWrite(LED, HIGH);   // on
    delay(500);
    digitalWrite(LED, LOW);    // off
    delay(500);
}
```

Gotchas:
- Classic boards use `delay()`; ESP32 boards can also just use `delay()`.
- To blink an LED on any pin, add a resistor (~220Ω) in series so you don't
  burn the LED out.
- `setup()` runs once, `loop()` runs forever — keep `loop()` non-blocking if
  you also need to read sensors at the same time.

Compile/flash via PlatformIO (`pio run --target upload`) or
`arduino-cli compile --fqbn arduino:avr:uno blink` then upload with `-p <COM>`.
