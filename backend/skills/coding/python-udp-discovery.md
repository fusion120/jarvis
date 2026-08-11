---
lang: python
keywords: udp, broadcast, discovery, socket, datagram, recvfrom, LAN, multicast, announce
---

# UDP broadcast discovery on the LAN

UDP lets a device announce itself and a listener discover it with no server, no handshake, and
no connections — ideal for finding printers, MQTT brokers, or ESP32/MicroPython boards on a
local network. Each `sendto` is one datagram; `recvfrom` returns data plus the sender address.

```python
import socket
import time

DISCOVERY_PORT = 37020


def listener(port: int = DISCOVERY_PORT) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("", port))                       # "" = all interfaces
        while True:
            data, addr = s.recvfrom(1024)
            print("heard from", addr, "->", data.decode(errors="replace"))


def announcer(name: str, port: int = DISCOVERY_PORT) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:
            s.sendto(f"hello i am {name}".encode(), ("255.255.255.255", port))
            time.sleep(2)


# Run in two terminals:
#   python -c "from python_udp_discovery import listener; listener()"
#   python -c "from python_udp_discovery import announcer; announcer('jarvis')"
```

Gotchas:
- UDP is fire-and-forget: no delivery guarantee, no ordering, possible duplicates — include a
  request/ack or message id if it matters.
- Datagrams are capped (typically ~1500 bytes for LAN MTU); larger sends may be silently
  dropped or truncated — chunk big payloads.
- Broadcast `255.255.255.255` may be filtered on some networks/routers; target the subnet
  broadcast or use multicast if discovery fails.
- The listener must call `s.bind(...)`; the announcer must NOT bind to the port (or it can't
  receive while sending). A socket bound to a port on one program blocks another from binding.
- `SO_BROADCAST` must be set on the sender or you get `PermissionError`.
- Messages are bytes; decode with an explicit encoding and `errors="replace"` for robustness.
