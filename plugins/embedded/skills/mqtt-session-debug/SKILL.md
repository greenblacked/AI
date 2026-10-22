---
name: mqtt-session-debug
description: "Diagnose MQTT devices that flap, miss messages or stampede the broker. Check in order: duplicate client ids (two units sharing one id take each other's session over in a loop), keepalive against the shortest NAT or cellular idle timeout (set near half), clean versus persistent session and expiry, QoS 0 loss and QoS 1 duplicates, retained and last-will semantics, silent topic ACL denials in the broker audit log, then reconnect backoff with full jitter and a recovery estimate of devices divided by accepted connections per second. Use for \"devices keep disconnecting every few minutes\", \"two devices kick each other off\", \"messages lost after reconnect\", \"the broker melted after the outage\". Not for service queues (event-driven-reliability), broker sizing (capacity-planning), clock or trust-root TLS failure (device-trust-anchors), other handshakes (tls-handshake-debugging)."
allowed-tools: Read, Glob, Grep
---

# MQTT Session Debug

A fleet is healthy when each device holds one stable session, loses no message it was promised across a reconnect, and a broker restart brings every unit back in a time you computed beforehand rather than discovered.

The usual failure is staring at one device. Flapping is nearly always a property of the pairing between a client setting and something in the path (another client, a NAT, a broker limit), so the fastest route is the broker's own log read across many clients, not one device's serial output. The second failure is a retry loop with no jitter: it turns a ten-second broker blip into a self-inflicted outage.

## Scope

Use for: devices that disconnect on a rhythm, devices that evict each other, messages that vanish or repeat around reconnects, commands that never arrive, and a fleet that overwhelms the broker when it comes back.

Do not use for: queue and consumer design in the services behind the broker, which is `event-driven-reliability`; sizing the broker for steady load, which is `capacity-planning`; a handshake rejected because of a wrong clock or a stale trust root, which is `device-trust-anchors`; one failing handshake otherwise, which is `tls-handshake-debugging`.

## Workflow

### 1. Get the broker's view, not the device's

Ask for the broker log with connection messages enabled and a window covering several flaps, plus the broker's metrics for connected clients. Note, per disconnect, who ended it: the client (clean DISCONNECT or TCP close), the broker (keepalive timeout, takeover, protocol error), or the network (reset with no DISCONNECT). The three causes below map to three different log signatures; read `references/log-signatures.md` to match them.

### 2. Write down the period

Compute the time between disconnects for one client and for the fleet.

- A fixed period that is the same on every unit points at a timer: keepalive against an idle timeout, a token or certificate lifetime, a scheduled broker job.
- A period that differs per unit but repeats within a unit points at that unit's path (its carrier, its NAT).
- Immediate reconnect and immediate disconnect in a tight loop, several times a second, is a client id collision until proved otherwise.

### 3. Duplicate client ids

The protocol requires a broker to disconnect the existing connection when a second client connects with the same id. Two units sharing an id therefore evict each other forever, each reconnect kicking the other out. The id is often derived from something not unique: a default string left in firmware, a truncated MAC, a value cloned in a golden image, or a serial number that the manufacturing step failed to write.

Search the broker log for the id that connects most often and for the takeover message (MQTT 5 uses reason code 0x8E, session taken over). Then compare ids against the fleet registry. The fix is an id derived from the device identity, and for a certificate-authenticated listener, an authorisation rule that ties the id to the certificate subject so a clone cannot claim another unit's id.

### 4. Keepalive against the path

The broker closes a connection when it hears nothing for one and a half times the keepalive interval. A NAT or cellular carrier closes an idle flow after its own timeout, often far shorter than assumed, and neither end is told. The result is a device that looks connected until its next publish goes nowhere.

- Find the shortest idle timeout on any path the fleet uses: measure it by holding an idle connection on that carrier and noting when it dies, rather than trusting a table.
- Set keepalive to about half of that timeout, so one lost ping does not kill the session.
- A very short keepalive costs battery and carrier data; a long one hides dead links. Choose the longest value that is safely under the measured timeout.
- Check that the client library sends PINGREQ on its own when idle and that a blocking publish or a long flash write does not starve it.

### 5. Session state

Decide per device class what must survive a reconnect.

- MQTT 3.1.1 has one flag, clean session; MQTT 5 splits it into clean start and a session expiry interval. A persistent session keeps subscriptions and queued messages only while the broker keeps it, so check the broker's expiry and queue limits; a device offline longer than the expiry returns to nothing.
- By default most brokers keep queued messages only for subscriptions made at QoS 1 or 2 (Mosquitto can queue QoS 0 with `queue_qos0_messages`). Queued messages are delivered at the lower of the publish QoS and the subscription QoS. On a broker left at that default, a subscription at QoS 0 loses everything sent while the device was away, whatever the publisher used.
- Check the broker's per-client queue cap. A full queue drops silently, usually the oldest or newest by setting.
- A client that connects with clean start true and then assumes its subscriptions are still in place has none. Re-subscribe on every connect unless the CONNACK says a session was present.

### 6. QoS, retained messages and last will

- QoS 0 is lost on any disconnect; accept that only for data that is superseded by the next sample.
- QoS 1 is at least once, so the receiver sees duplicates after a retry. Make handlers idempotent with a message id or sequence number; do not try to detect duplicates by payload.
- QoS 2 is rarely worth its extra round trips on a constrained link; prefer QoS 1 with idempotency.
- A retained message is delivered to each new subscriber and survives until replaced or cleared with an empty retained payload. A retained command replays at every reconnect, so a retained "reboot" reboots the device again each time it connects.
- The last will is published only on an ungraceful end. A clean DISCONNECT suppresses it, so a presence topic needs a retained "online" published on connect and a retained "offline" as the will, plus the same "offline" on a clean shutdown.

### 7. Silent authorisation failures

A topic ACL denial is often silent. In MQTT 3.1.1 a denied subscription returns failure code 0x80 in the SUBACK, which many client libraries ignore, and a denied publish at QoS 0 is dropped without telling the client. MQTT 5 can return a not-authorised reason, code 0x87, but only if the broker is configured to. Read the broker's authorisation or audit log for denials, and have the client log SUBACK codes. A device that connects fine and receives nothing is this until the log says otherwise.

### 8. Reconnect behaviour and the stampede

When the broker or the network recovers, every device retries at once. The cost is not the connections but the TLS handshakes, which spend broker CPU, and the session restores, which spend disk and memory.

- Require exponential backoff with full jitter: wait a random time between zero and the smaller of a cap and the base times two to the power of the attempt number. Fixed delays and "plus a little jitter" keep the herd synchronised.
- Cap the delay at a value that matches how long you can accept a device being dark, commonly a few minutes, and reset the backoff only after a connection has stayed up for a while, not on the first CONNACK. A broker that accepts then drops under load otherwise gets a hot loop.
- Estimate recovery time: devices divided by the connections per second the broker accepts with TLS. A hundred thousand units at five hundred accepted connections a second is two hundred seconds at best, and longer if a restored session replays a backlog. Check this figure is inside your recovery objective; the jitter window should be about as wide as this estimate.
- Rehearse it against a staging broker that runs the production configuration, never the production broker. Drive a connection simulator at ten times the real fleet, restart that broker, and record the time to a steady connected count, the peak CPU and the number of rejected connections. Keep the result with the broker configuration it was measured on.

### 9. Hand back

Give the confirmed cause with the log lines or counts that show it, the one change that fixes it, the measured idle timeout and the keepalive chosen, the computed recovery time, and the rehearsal result if one was run. State what was not checked, such as a carrier not in the sample.

## Anti-patterns

**Raising the keepalive to stop disconnects.** It moves the failure to the first publish after an idle gap, and the NAT still drops the flow.

**Fixing the client id on one unit.** The collision is a property of how ids are assigned; the next cloned unit repeats it.

**Retrying on a fixed timer.** After an outage every unit lines up on the same second, and the broker sees the same peak again.

**Trusting QoS 1 to mean once.** It means at least once; the duplicate arrives on the day the link is worst.

## Reference files

- `references/log-signatures.md` — read at steps 1 to 3 and 7: what each cause looks like in a broker log and in broker metrics, the questions to ask of each, and a template for the reconnect rehearsal record.
