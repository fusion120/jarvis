---
lang: general
keywords: serial, port, com, pyserial, usb, uart, /dev/tty
---
# Talk to a device over a serial port (Python)

The first thing to do with a plugged-in Arduino/ESP32 is find its port, then
read its output.

```python
import serial
import serial.tools.list_ports as ports

# 1. list ports — pick the one with a known description
for p in ports.comports():
    print(p.device, p.description)

# 2. open and read lines (Arduino prints to Serial at 115200)
ser = serial.Serial("COM3", 115200, timeout=2)
try:
    for _ in range(10):
        line = ser.readline().decode("utf-8", errors="replace").strip()
        if line:
            print(line)
finally:
    ser.close()
```

Gotchas:
- Close the port when done (`ser.close()`) — Windows locks it otherwise and
  re-uploading firmware fails with "port busy".
- On Linux it's `/dev/ttyUSB0` / `/dev/ttyACM0`; Windows is `COM3` etc.
- Use `timeout=` on `serial.Serial` so reads never block forever.
- `errors="replace"` when decoding — binary garbage is normal on noisy lines.
- The CH340/CP210x driver must be installed for clone boards to show a port.
