---
lang: general
keywords: raspberry, pi, gpio, ssh, headless, rpi, gpiozero
---
# Control a Raspberry Pi's GPIO from Python

A Pi is a Linux computer — write Python, run it over SSH. Never flash it like
an Arduino.

```python
# blink.py — run on the Pi
from gpiozero import LED
from time import sleep

led = LED(17)                     # GPIO17
while True:
    led.on()
    sleep(0.5)
    led.off()
    sleep(0.5)
```

Run it over SSH from Mohamed's PC:

```
scp blink.py pi@<pi-ip>:~
ssh pi@<pi-ip> python3 -u ~/blink.py
```

Gotchas:
- `gpiozero` is preinstalled on Raspberry Pi OS; `RPi.GPIO` also works.
- Pin numbers are **BCM (GPIOx)**, not physical positions.
- For headless/boot scripts, use a `@reboot` line in `crontab -e`.
- The Pi doesn't do real-time like an MCU — fine for LEDs/sensors, not for
  precise timing.
- GPIO needs the user in the `gpio` group, or run with `sudo`.
