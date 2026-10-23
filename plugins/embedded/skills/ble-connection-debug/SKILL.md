---
name: ble-connection-debug
description: "Fix Bluetooth Low Energy peripherals that drop, stall or refuse to reconnect. Capture on air (nRF Sniffer into Wireshark) beside the phone's log before reading code. Check connection interval, peripheral latency and supervision timeout against their own constraint (timeout must exceed twice the interval times one plus latency) and against the phone platform's published limits, since a rejected parameter update looks like a drop at a fixed time. For throughput check ATT MTU, data length extension, 2M PHY and event length. After a firmware update that changes the GATT table, stale phone cache and bond mismatch break reconnects; send Service Changed. Use for \"BLE disconnects after 30 seconds on iPhone\", \"throughput is terrible\", \"won't reconnect after firmware update\", \"pairing works once then fails\". Not for wired links (serial-bus-debug) or radio energy cost (sleep-current-hunt)."
allowed-tools: Read, Glob, Grep
---

# BLE Connection Debug

A link is fixed when an air capture and the phone's log agree on why it behaved as it did, the connection parameters sit inside both the specification and the phone platform's limits, and the failing sequence now passes on the phone models and operating system versions that showed it.

The usual failure is reading firmware for a fault that is in a negotiation. Two sides propose parameters, one rejects or overrides them, and the only visible effect is a disconnect at a repeatable time or a link that is slower than the radio allows. Neither side's application code shows it; the packets do.

## Scope

Use for: a BLE peripheral (or the phone app that talks to it) that disconnects, transfers slowly, fails to reconnect after an update, or loses its pairing.

Do not use for: wired buses on the board, which is `serial-bus-debug`; the energy cost of keeping the radio on, which is `sleep-current-hunt`.

## Workflow

### 1. Capture before changing code

Collect two views of the same failure, with times that can be aligned.

- On air: a BLE sniffer, such as the nRF Sniffer for Bluetooth LE feeding Wireshark. Start it before the connection so it sees the connect request and the channel map, since a sniffer that joins late cannot follow the link. Note the sniffer's range; it must sit close to both devices.
- On the phone: Android's Bluetooth HCI snoop log (enable it in developer options and read it in Wireshark) and logcat; on iOS, Apple's Bluetooth logging profile and the PacketLogger tool, plus the app's own log of the delegate callbacks.

Write down the disconnect reason from each side. HCI reasons to know: 0x08 connection timeout (supervision timeout expired), 0x13 remote user terminated, 0x16 connection terminated by local host, 0x3D connection terminated due to MIC failure, 0x3E connection failed to be established. On Android, GATT status 8 is a timeout, 19 the peer ending the link, and 133 a generic error that needs the capture to explain.

### 2. Classify the failure by timing

- Disconnect at the same elapsed time after connecting (30 seconds, a minute): a parameter update or a timer. Look at what the peripheral requested just before.
- Disconnect after a quiet period with reason 0x08: the supervision timeout fired because packets stopped arriving, either by range, interference or a peripheral that stopped servicing the link.
- Disconnect immediately after encryption starts: bond mismatch (step 5).
- Never connects, or connects after many tries: advertising or address resolution (step 6).
- Works but slow: step 4.

### 3. Connection parameters

Three values define the link: connection interval, peripheral latency (events the peripheral may skip) and supervision timeout. They obey a constraint from the specification: the supervision timeout must be greater than twice the interval times one plus the latency. Latency of 4 at a 30 ms interval needs a timeout over 300 ms. Also check the ranges (interval 7.5 ms to 4 s, timeout 100 ms to 32 s) and that your latency leaves room for a couple of missed events in a noisy room.

Then check them against the phone. A central may accept, adjust or reject a peripheral's request, and platforms publish what they accept. Apple's accessory design guidelines set a minimum interval and bounds relating interval, latency and timeout; read the current version for the numbers rather than relying on memory. A request outside them is ignored or refused, and a peripheral that waits for the new values and then idles out looks like a disconnect at a fixed time. In the capture, find the connection update request, the response or reject from the central, and the update actually applied (an LL connection update indication). On Android the app can ask for a faster interval with `requestConnectionPriority`; the stack picks the actual values.

Set conservative parameters first, compare the capture, then tune for power or speed.

### 4. Throughput

Compute the ceiling, then find what is below it.

- Payload per packet is bounded by the ATT MTU: a notification carries MTU minus three bytes. A default MTU of 23 gives 20 bytes. Request a larger MTU from the app (Android `requestMtu`; iOS negotiates its own and reports it) and check the peripheral accepts it.
- Data length extension lets one link-layer packet carry up to 251 bytes. Without it, a large MTU is still split into small packets. Check both sides support it and it was negotiated.
- The 2M PHY doubles the raw rate where both ends and the phone support it; coded PHY trades rate for range.
- Packets per connection event matter as much as the interval. Some stacks cap the number per event, and a short connection event length ends the event early. A shorter interval gives more events per second.
- Notifications do not wait for acknowledgement; writes with response do, one per round trip. Use write without response and notifications for bulk data, with flow control at the application level.
- iOS and Android limit how many notifications they deliver per event. Measure, do not assume.

Quote the result as application bytes per second, measured over a minute with the same phone model, and compare it with the computed ceiling.

### 5. Reconnect failures and bonding

After a firmware update that changes the GATT table, the phone may hold a stale copy of the attribute table and fail with handle errors or missing characteristics. A phone caches the table of a bonded peripheral.

- Include the Service Changed characteristic in the Generic Attribute service, make it indicate, and send the indication after an update that changes handles. The indication is only sent to a bonded, subscribed central. An unbonded phone rediscovers on connect.
- Keep handle layout stable between versions where possible, and add new attributes at the end.
- If an update erases the bond storage on the peripheral while the phone keeps its key, the phone starts encryption with a key the peripheral does not have and the link ends. Persist bond data across updates, or deliberately clear it and tell the user to forget the device on the phone. Seeing "pairing works once then fails" usually means one side lost the bond.
- Check security requirements on characteristics match the pairing method used, and that the peripheral accepts a bonded central's encrypted reconnect without asking to pair again.

### 6. Advertising, addresses and coexistence

- Advertising interval: a long interval makes discovery and reconnect slow. Use a fast interval for the first seconds after a disconnect or power-up, then slow down, and read the phone vendor's guidance for values.
- Private addresses: a peripheral using a resolvable private address changes it periodically; a bonded phone resolves it with the identity resolving key it stored. If the peripheral lost or regenerated that key, the phone sees a stranger.
- Coexistence: BLE shares 2.4 GHz with Wi-Fi, USB 3 noise and microwave ovens. The link hops channels and can mask poor ones with a channel map; check the map in the capture and look for retransmissions grouped on channels near a busy Wi-Fi channel. Range problems cluster with orientation and body position, so test with the device in its real housing.

### 7. Verify on a matrix

Repeat the failing sequence on each phone model and operating system version in the reports, with the sniffer running, and keep one capture of the passing run. Vendors change behaviour between releases, so record the versions.

### 8. Hand back

Give the disconnect reason from both sides, the capture excerpt showing the cause, the parameters before and after, the measured throughput, the bond and cache handling decision, and the phone matrix tested.

## Anti-patterns

**Debugging the app on one phone.** The behaviour belongs to a platform's rules, so reproduce on at least one phone of each platform.

**Asking for 7.5 ms intervals on every link.** The central may refuse, the radio uses more power, and coexistence gets worse.

**Clearing bonds silently on update.** The user finds a phone that cannot connect and no explanation.

**Treating Android status 133 as a cause.** It is a symptom; the capture holds the reason.

## Reference files

- `references/parameters-and-captures.md` — read at steps 1 to 5: parameter worked examples, a table of capture filters and what each packet shows, a throughput ceiling calculation, and an update checklist for GATT changes.
