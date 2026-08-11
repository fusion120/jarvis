---
lang: cpp
keywords: arduino, servo, motor, pan, tilt
---
# Drive a servo from an Arduino

Standard hobby servo (e.g. SG90, MG996R) on a PWM-capable pin.

```cpp
#include <Servo.h>
Servo servo;

void setup() {
    servo.attach(9);      // signal pin 9
}

void loop() {
    servo.write(0);       // sweep across the range
    delay(500);
    servo.write(90);      // center
    delay(500);
    servo.write(180);
    delay(500);
}
```

Gotchas:
- `Servo.write(angle)` takes 0–180, not microseconds.
- Servos want **4.8–6V power**, not 5V from the board's pin — a big servo
  browning out the MCU is the #1 cause of "it resets when it moves". Give it
  its own supply and share the ground.
- Don't slam it from 0 to 180 instantly with heavy loads; a slow ramp avoids
  jitter and stalls.
- On ESP32, `Servo.h` works too but you must pick a PWM-capable GPIO.
