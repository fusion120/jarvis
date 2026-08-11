---
lang: python
keywords: socket, tcp, server, client, listen, accept, recv, sendall, networking, protocol
---

# TCP socket server (threaded, multi-client)

A raw-socket TCP server that accepts many clients and handles each in its own thread. This is
the layer under HTTP, MQTT, and custom device protocols — know it before reaching for a
framework.

```python
import socket
import threading


def handle(conn: socket.socket, addr):
    print("connected:", addr)
    with conn:
        while True:
            data = conn.recv(1024)      # blocks until some data arrives
            if not data:                # b"" == peer closed the connection
                break
            conn.sendall(b"echo: " + data)
    print("disconnected:", addr)


def main(host: str = "127.0.0.1", port: int = 9000) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((host, port))
        srv.listen(5)
        print("listening on", host, port)
        while True:
            conn, addr = srv.accept()
            threading.Thread(target=handle, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
```

Gotchas:
- TCP has no message boundaries: `recv(1024)` may return half a message or several messages
  glued together. Use a length prefix or delimiter and buffer until complete.
- `send()` can send fewer bytes than given — always use `sendall()` for the full payload.
- `recv` returning `b""` is the *only* reliable end-of-stream signal; check it, not exceptions.
- Bind before listen; set `SO_REUSEADDR` before `bind` or restart after a crash hits
  "Address already in use".
- `accept()` blocks forever — give it a `srv.settimeout(seconds)` or select/poll if the main
  loop must also do other work.
- Each thread holds one client; for thousands of connections switch to an event loop
  (`asyncio.start_server`), not a thread per socket.
