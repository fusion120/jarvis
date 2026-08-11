# Jarvis EV — Parts List

The robot is a **QBIT body** (3D-printed) with an **ESP32-C3** brain, an **OLED face**,
**touch input**, **speaker for voice**, and a **webcam on your PC** that lets it see you.

---

## 🟢 MVP — what to buy now (~$15–20)

| # | Part | Qty | Why | Price |
|---|---|---|---|---|
| 1 | **ESP32-C3 Super Mini** (any brand) | 1 | The brain. WiFi, fits QBIT body perfectly. | ~$3 |
| 2 | **0.96″ OLED 128×64 I2C (SSD1306)** | 1 | The face — eyes, expressions, EV personality. | ~$3 |
| 3 | **TTP223 capacitive touch module** | 1 | Tap the robot to interact — just like EV. | ~$1 |
| 4 | **Passive buzzer** (5V) | 1 | Blips, chimes, notifications. | ~$1 |
| 5 | **28mm 8Ω 0.5W speaker** + **MAX98357A I2S amp** | 1 | Real voice output — Jarvis talks to you through the robot. | ~$4 |
| 6 | **USB webcam** (any 720p/1080p) | 1 | Clips to your monitor — this is how Jarvis SEES you. | ~$5–10 |
| 7 | **USB-A to USB-C cable** | 1 | Flash the ESP32 + power it. | ~$2 |
| 8 | **Jumper wires** (male→female, ~10) | 1 pack | Connect OLED + touch + buzzer to ESP32. | ~$1 |
| 9 | **3D filament** (PLA) | ~30g | Print the QBIT body from `qbit_parts/`. | ~$1 |

> The QBIT body STLs are already extracted in `robot/cad/qbit_parts/` — drag
> `part_5.stl` (chassis) + `part_10.stl` (face frame) + `part_18.stl` (servo+camera
> tower) into Bambu Studio and print.

**Subtotal: ~$15–20** (webcam is the variable — any existing USB cam works).

---

## 🟡 V2 — upgrades later

| # | Part | Qty | Why | Price |
|---|---|---|---|---|
| 10 | **SG90 micro servo** | 1 | Physical head tilt (the body already has a servo mount). | ~$3 |
| 11 | **OV2640 camera module** + ESP32-CAM board | 1 | Robot-mounted camera (so it can look around, not just your webcam). | ~$5 |
| 12 | **MEMS mic (INMP441)** | 1 | On-robot hearing (instead of PC mic). | ~$3 |

---

## 🔌 Wiring (ESP32-C3 Super Mini)

| Signal | GPIO | Notes |
|---|---|---|
| OLED SDA | GPIO20 | I2C |
| OLED SCL | GPIO21 | I2C |
| Touch sensor OUT | GPIO1 | Digital input, HIGH when touched |
| Buzzer + | GPIO2 | PWM (LEDC) |
| Speaker amp DIN | GPIO3 | I2S data (MAX98357A) |
| Speaker amp BCLK | GPIO4 | I2S bit clock |
| Speaker amp LRC | GPIO5 | I2S word select |
| Servo signal (V2) | GPIO6 | PWM |

Power: USB-C powers everything (ESP32, OLED, touch, buzzer all at 3.3V/5V from USB).

---

## First purchase recap
```
1 × ESP32-C3 Super Mini
1 × 0.96" SSD1306 OLED I2C
1 × TTP223 capacitive touch module
1 × passive buzzer
1 × 28mm speaker + MAX98357A I2S amp
1 × USB webcam (or use one you already have)
1 × USB-A to USB-C cable
1 × pack of 10 male→female jumper wires
1 × PLA filament (~30g for the QBIT body)
```
≈ **$15–20** for a talking, seeing, reactive Jarvis EV on your desk.
