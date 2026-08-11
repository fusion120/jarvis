---
lang: javascript
keywords: websocket, ws, socket, message, reconnect, heartbeat, ping pong, binary message, onopen, onmessage, realtime
---

# WebSocket client

WebSocket gives a full-duplex, persistent connection for real-time apps. In Node use the `ws` package; browsers have `new WebSocket(url)` built in. Always add reconnect with backoff and a heartbeat so dead connections don't go silent forever.

```javascript
// npm install ws
// Node WebSocket client with auto-reconnect + heartbeat
const WebSocket = require("ws");

function createSocket(url, { onMessage = () => {}, onStatus = () => {} } = {}) {
  let ws;
  let closed = false;
  let retries = 0;

  const ping = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) ws.ping();
  }, 30000); // client-side heartbeat

  function connect() {
    ws = new WebSocket(url);
    ws.on("open", () => { retries = 0; onStatus("open"); });
    ws.on("message", (data) => {
      // data is a Buffer in Node; JSON.parse only after toString
      try { onMessage(JSON.parse(data.toString())); }
      catch { onMessage({ raw: data.toString() }); }
    });
    ws.on("close", () => {
      onStatus("closed");
      if (!closed) {
        const delay = Math.min(1000 * 2 ** retries++, 15000);
        setTimeout(connect, delay);               // reconnect with backoff
      }
    });
    ws.on("error", (err) => { onStatus(`error: ${err.message}`); });
  }

  connect();

  return {
    send(obj) {
      if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
    },
    close() {
      closed = true;
      clearInterval(ping);
      ws?.close();
    },
  };
}

const client = createSocket("wss://echo.websocket.org", {
  onMessage: (msg) => console.log("got:", msg),
});
client.send({ type: "greet", payload: "hello" });
```

Gotchas:
- In Node, message data arrives as a `Buffer`; call `.toString()` before JSON.parse. In browsers it's already a string (or Blob/ArrayBuffer for binary).
- Check `readyState === WebSocket.OPEN` before `send` or you silently drop messages (or throw).
- No built-in reconnection — implement backoff + a `closed` flag so reconnect stops on intentional close.
- Ping/pong (`ws.ping()` in Node; `send("ping")` convention in browsers) detects half-open connections that never fire `close`.
- A single bad `onmessage` throw can crash the process — wrap handlers in try/catch.
- Use `wss://` in production; `ws://` is plaintext.
