---
lang: java
keywords: udp, datagram, DatagramSocket, DatagramPacket, send, receive, connectionless, multicast
---

# UDP with DatagramSocket

UDP is connectionless and unreliable: `DatagramSocket.send/receive` moves whole packets between endpoints with no handshake and no delivery guarantee. Use it where a dropped packet is tolerable — telemetry, discovery, DNS, game state — never for commands that must be acknowledged.

```java
import java.net.*;
import java.nio.charset.StandardCharsets;

public class UdpDemo {
    public static void main(String[] args) throws Exception {
        int port = 9_998;

        Thread receiver = new Thread(() -> {
            try (DatagramSocket sock = new DatagramSocket(port)) {
                byte[] buf = new byte[1024];
                DatagramPacket p = new DatagramPacket(buf, buf.length);
                sock.receive(p); // blocks until a packet arrives
                String msg = new String(p.getData(), p.getOffset(), p.getLength(), StandardCharsets.UTF_8);
                System.out.println("received: " + msg + " from " + p.getSocketAddress());

                byte[] reply = ("ack:" + msg).getBytes(StandardCharsets.UTF_8);
                DatagramPacket out = new DatagramPacket(reply, reply.length, p.getSocketAddress());
                sock.send(out); // reply to the sender's address+port
            } catch (Exception e) {
                e.printStackTrace();
            }
        });
        receiver.start();
        Thread.sleep(200);

        try (DatagramSocket sock = new DatagramSocket()) {
            byte[] data = "ping".getBytes(StandardCharsets.UTF_8);
            DatagramPacket out = new DatagramPacket(data, data.length,
                InetAddress.getLoopbackAddress(), port);
            sock.send(out);

            byte[] buf = new byte[1024];
            DatagramPacket in = new DatagramPacket(buf, buf.length);
            sock.receive(in);
            System.out.println("reply: " + new String(in.getData(), in.getOffset(), in.getLength(), StandardCharsets.UTF_8));
        }
        receiver.join();
    }
}
```

Gotchas:
- UDP packets are the *unit* of delivery — max ~65507 bytes payload; bigger needs fragmentation and is frequently dropped, so stay under ~1400 for the internet.
- Datagrams can arrive out of order, duplicated, or not at all — build sequence numbers, checksums, and retransmission into your protocol.
- `receive()` writes into your buffer starting at offset 0 and returns the length in the packet; read exactly `getLength()` bytes, not the whole buffer.
- A single `DatagramSocket` can both send and receive; `connect()` on a UDP socket filters packets to one peer but is still connectionless.
- Datagram packets have no sender address when received via an unconnected socket — capture `getSocketAddress()` before the buffer is reused.
- Ports below 1024 need OS privileges; `SocketException: Permission denied` usually means an unprivileged bind.
