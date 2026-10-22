# Parameters and captures

## Contents

- Parameter constraint examples
- Reading a capture
- Throughput ceiling
- GATT change checklist

## Parameter constraint examples

The supervision timeout must exceed (1 + latency) x interval x 2.

| Interval | Latency | Minimum timeout | A sensible timeout |
| --- | --- | --- | --- |
| 30 ms | 0 | 60 ms, below the 100 ms floor | 2 s |
| 30 ms | 4 | 300 ms | 2 s |
| 100 ms | 4 | 1 s | 4 s |
| 500 ms | 9 | 10 s | 20 s |

A timeout much longer than the minimum makes a lost link take that long to be noticed; one just above it disconnects on two lost events. Choose a few multiples of the interval and test in a noisy room.

Latency saves power only when the peripheral has nothing to send. If it must send every second and the interval is 30 ms, latency up to 30 still lets it send on time but delays any central-to-peripheral message by up to latency x interval.

## Reading a capture

In Wireshark, with the sniffer's dissector:

- Find the connect indication at the start: it holds the interval, latency, timeout and channel map the link began with.
- Filter for link-layer control packets: connection update indications, channel map updates, feature exchange, data length requests, PHY updates. Each shows what changed and when.
- Find L2CAP connection parameter update requests and responses, which carry a peripheral's request and the central's accept or reject result.
- At a disconnect, look at the last packets: a terminate indication carries the reason; no terminate and a run of empty polls then silence means a supervision timeout.
- Check retransmissions (repeated sequence numbers) clustered on particular channels.
- For ATT, look for MTU exchange, errors such as "attribute not found" after an update, and the Service Changed indication.

Align sniffer time with the phone log by an event both show, such as the connect or a known write.

## Throughput ceiling

For a link with a 15 ms interval, a data length of 251 bytes, ATT MTU 247 and 2M PHY, and a stack that sends up to 4 packets per event:

- Payload per notification: 244 bytes (MTU minus 3).
- Notifications per event: 4, if the stack allows and the event length is long enough.
- Events per second: 1000 / 15, about 66.
- Ceiling: 244 x 4 x 66, about 64 kilobytes per second.

On the 1M PHY a 251-byte packet takes about 2 ms on air, so four fit comfortably in a 15 ms interval only if the controller allows; if the stack sends one per event the ceiling drops to about 16 kilobytes per second. The measured number tells you which limit you are on.

## GATT change checklist

1. Compare the old and new attribute tables handle by handle.
2. If any handle moved or changed, make sure Service Changed is present and the indication is sent on first connect after the update.
3. Confirm bond data survives the update (stored outside the region being rewritten).
4. Test an update with a bonded phone that has cached the old table, on each platform.
5. Test an update with an unbonded phone.
6. Test the app after the update without clearing its own cache of discovered services, since apps cache too.
7. Record the phones and operating system versions used.
