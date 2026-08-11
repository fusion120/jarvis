---
lang: python
keywords: websocket, websockets, ws, async, broadcast, server, realtime, chat, push
---

# WebSocket broadcast server with websockets

WebSockets give full-duplex push — the server can send to the client without a request. A
chat/broadcast hub keeps every connected peer in a set and forwards each incoming message to
all of them.

```python
# pip install websockets
import asyncio

import websockets

connected: set = set()


async def handler(ws):
    connected.add(ws)
    print("peer connected, total", len(connected))
    try:
        async for message in ws:                      # one message per loop iteration
            print("broadcasting:", message)
            for peer in list(connected):
                try:
                    await peer.send(message)
                except Exception:
                    connected.discard(peer)           # dead peer — drop it
    finally:
        connected.discard(ws)


async def main() -> None:
    async with websockets.serve(handler, "127.0.0.1", 8765):
        print("ws server on ws://127.0.0.1:8765")
        await asyncio.Future()                        # run forever


if __name__ == "__main__":
    asyncio.run(main())
```

Gotchas:
- Iterate a *copy* (`list(connected)`) when broadcasting — a client connecting or disconnecting
  mid-iteration otherwise raises `Set changed size during iteration`.
- `send` on a disconnected peer raises `ConnectionClosed`; catch it and discard the peer, or
  one dead client breaks the broadcast to everyone.
- Always remove the connection in a `finally`, or dead sockets accumulate and every message
  goes to zombies.
- `websockets.serve` is a coroutine/async context manager — it must run inside the event loop,
  not in a thread or at module level.
- The handler runs as a separate task per connection, so `connected` needs no lock inside one
  event loop — but don't touch it from other threads.
- By default `serve` limits messages; set `max_size=None` or a limit if clients send big binary
  payloads, and handle `ConnectionClosedError` from the client side too.
