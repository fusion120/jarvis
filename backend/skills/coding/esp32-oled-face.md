---
lang: cpp
keywords: esp32, oled, ssd1306, display, face, eyes
---
# Draw a face on an SSD1306 OLED (128x64)

The exact pattern this repo's robot uses for MIMO's eyes.

```cpp
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define OLED_W 128
#define OLED_H 64
#define OLED_ADDR 0x3C
#define SDA_PIN 20
#define SCL_PIN 21

Adafruit_SSD1306 display(OLED_W, OLED_H, &Wire, -1);

void drawEyes(int cx, int cy, int r, String mode) {
    if (mode == "happy") {                       // upward arcs
        display.drawLine(cx - r, cy, cx, cy - r, WHITE);
        display.drawLine(cx, cy - r, cx + r, cy, WHITE);
    } else if (mode == "sleep") {                // closed lines
        display.fillRect(cx - r, cy - 2, r * 2, 4, WHITE);
    } else {                                     // round idle eyes
        display.fillCircle(cx, cy, r, WHITE);
        display.fillCircle(cx, cy, r / 3, BLACK);
    }
}

void setup() {
    Wire.begin(SDA_PIN, SCL_PIN);
    if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
        while (true);                            // OLED missing
    }
    display.clearDisplay();
    drawEyes(40, 26, 12, "happy");
    drawEyes(88, 26, 12, "happy");
    display.display();
}

void loop() {}
```

Gotchas: I2C addr is usually `0x3C`; `Wire.begin(sda, scl)` pin order matters
on ESP32. `display.display()` pushes the buffer — always call it after drawing
or nothing shows. `fillCircle(x, y, r, BLACK)` on top of a white circle makes a
pupil. The buffer is 1 KB; re-draw the whole frame each `display.display()`.
