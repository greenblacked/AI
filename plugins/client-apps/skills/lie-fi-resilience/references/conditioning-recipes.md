# Conditioning recipes

How to produce each of the four conditions from step 1 on each platform. The OS
conditioners cover slow links and total loss; the connected-but-silent and captive-portal
cases need a stub or a proxy, because no OS profile produces a link that accepts a
connection and then says nothing.

## Contents

- iOS
- Android emulator
- Physical Android devices
- Browsers and Playwright
- Linux hosts and CI
- Stub servers for silence, trickle and portal
- A note on HTTPS and captive portals

## iOS

- **Device:** Settings, then Developer, then Network Link Conditioner. The Developer menu
  appears once the device has been used for development from Xcode. Profiles include
  `3G`, `Edge`, `100% Loss`, `Very Bad Network` and `High Latency DNS`, and custom
  profiles can be added. It conditions the whole device, so turn it off afterwards.
- **Simulator:** the simulator uses the Mac's network. Install Network Link Conditioner
  from Additional Tools for Xcode and enable it on the Mac.
- **Physical device without the Developer menu:** share a conditioned Mac connection
  through Internet Sharing, or point the device's Wi-Fi proxy at a throttling proxy.

## Android emulator

```bash
adb emu network speed umts      # also gsm, gprs, edge, hsdpa, lte, evdo, full
adb emu network delay umts      # also gprs, edge, none
adb emu network speed full      # restore
adb emu network delay none
```

The emulator's Extended controls, under Cellular, set network type and signal strength
from the UI. Airplane mode in the emulator gives the 100%-loss-with-no-route case, which
is the easy one; for loss with a route, point the app at a stub that never answers.

## Physical Android devices

There is no built-in conditioner. Either set the Wi-Fi proxy to a throttling proxy on a
laptop, or run the stub servers below on the laptop and forward them to the device:

```bash
adb reverse tcp:8081 tcp:8081   # device's localhost:8081 reaches the laptop's 8081
```

Then point a debug build's base URL at `http://localhost:8081`. Test on a low-end device
as well as a flagship: slow CPUs make parsing and UI work on a slow response worse.

## Browsers and Playwright

- DevTools Network panel: the throttling presets and Offline, plus custom profiles with
  latency, download and upload values.
- Playwright: `context.setOffline(true)` for no route. For silence, register
  `page.route('**/api/**', () => {})` and never call `fulfill`, `continue` or `abort`, so
  the request stays pending. For a portal, `route.fulfill({ status: 200, contentType:
  'text/html', body: '<html>Sign in to continue</html>' })`.

## Linux hosts and CI

`netem` shapes a real interface. Run it in a disposable container or VM, not on a shared
runner's main interface:

```bash
sudo tc qdisc add dev eth0 root netem delay 300ms 100ms loss 5%
sudo tc qdisc change dev eth0 root netem loss 100%
sudo tc qdisc del dev eth0 root
```

Toxiproxy sits between the client under test and a real backend and adds named toxics:
`latency`, `bandwidth`, `timeout` (with a timeout of 0 it holds the connection open and
drops data until the toxic is removed, which is lie-fi exactly), `limit_data` and
`reset_peer`. Use it when the test must exercise the real backend.

## Stub servers for silence, trickle and portal

Run with `python3 -I stub.py`. Each listens on a port and misbehaves in one way.
They bind to loopback, which is enough for `adb reverse`; use `0.0.0.0` only when a device reaches the laptop over Wi-Fi, and only on a network you trust.

```python
# silent.py: accept, read, never answer
import socket

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", 8081))
s.listen()
held = []
while True:
    conn, _ = s.accept()
    held.append(conn)
```

```python
# trickle.py: send headers, then one byte every five seconds
# an idle timer that resets on data never fires against this
import socket, threading, time


def serve(conn):
    conn.recv(65536)
    conn.sendall(
        b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 1000000\r\n\r\n"
    )
    while True:
        conn.sendall(b" ")
        time.sleep(5)


s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", 8082))
s.listen()
while True:
    c, _ = s.accept()
    threading.Thread(target=serve, args=(c,), daemon=True).start()
```

```python
# portal.py: every path answers 200 with a login page
from http.server import BaseHTTPRequestHandler, HTTPServer


class Portal(BaseHTTPRequestHandler):
    def _page(self):
        body = b"<html><body>Sign in to the network</body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = do_PUT = do_DELETE = _page


HTTPServer(("127.0.0.1", 8083), Portal).serve_forever()
```

The trickle case is the one most clients fail: it is what a congested cell looks like to
an idle timer.

## A note on HTTPS and captive portals

A real portal cannot answer TLS for your domain. Against an HTTPS API it shows up as a
failed handshake, a certificate error or a reset, and only plain-HTTP requests (and some
embedded web views) see the login page itself. Test both: point a debug build at the
portal stub to check that HTML is never parsed or cached as data, and confirm that TLS
and certificate errors are classified as network failures that get the offline
treatment, not as a fatal error screen.
