# MQTT log signatures

## Contents

- Matching a symptom to a cause
- Questions to ask of the broker
- Client-side checks
- Reconnect rehearsal record

## Matching a symptom to a cause

Wording varies by broker and version, so match on meaning rather than exact text. Turn on the broker's connection and disconnection messages first; most brokers log them only on request.

| What the broker log shows | Cause | Next step |
| --- | --- | --- |
| The same client id connecting repeatedly, each time closing an older connection from a different address | Duplicate client id | Compare addresses and certificate subjects for that id; check the registry |
| A client closed for exceeding its timeout, then reconnecting, at a constant interval | Keepalive longer than the path allows, or the client stopped sending pings | Measure the path idle timeout; check the client's ping handling |
| A client's socket closed with no DISCONNECT, then a new connect from a different source port | NAT or carrier dropped the flow | Shorten keepalive to about half the measured timeout |
| Connect, then immediate close, repeated for many ids at once after an outage | Reconnect stampede | Add full-jitter backoff; check accept rate |
| Connect refused with a not-authorised code | Wrong credentials or a client id the listener's rules reject | Check the authentication log, not the client log |
| Clean connect, no subscription traffic, device receives nothing | ACL denial on SUBSCRIBE | Look for denied subscriptions; log SUBACK codes in the client |
| Messages for a client dropped because its queue is full | Persistent session with a long absence | Raise the queue cap deliberately or shorten the expiry |
| Connect succeeds, session not present, subscriptions gone | Session expired or clean start used | Re-subscribe on every connect |

## Questions to ask of the broker

- How many clients are connected, and what was that count before and after the first flap? Most brokers publish it as a metric; Mosquitto exposes it on the `$SYS` topics, which a subscriber can read with `mosquitto_sub -v -t '$SYS/#'`.
- What are the limits on connections, in-flight messages and queued messages per client, and which ones were hit?
- Does the broker enforce a maximum connection rate or a maximum packet size, and what does it do when exceeded: refuse, delay or close?
- What is the persistent session expiry, and does it differ from the device's offline times?
- Is there a load balancer or proxy in front, and what is its own idle timeout? A balancer with a sixty-second idle timeout and a ninety-second keepalive produces exactly the period pattern in step 2.

## Client-side checks

- The client logs the CONNACK return code and whether a session was present.
- The client logs every SUBACK code, and treats 0x80 as a failure.
- The client id source is printed once at start-up.
- The ping interval and the last packet sent time are visible in a debug build.
- A blocking operation longer than the keepalive does not occur on the thread that services the network.

## Reconnect rehearsal record

Fill this in for each rehearsal and keep it with the broker configuration.

```text
Date:
Broker version and instance size:
Simulated clients (real fleet size, and multiple of it):
Backoff parameters (base, cap, jitter, reset rule):
Time from broker restart to first accepted connection:
Time to 50 percent, 95 percent and 100 percent connected:
Peak broker CPU and memory:
Connections refused or timed out:
Messages lost or replayed:
Result against the recovery objective:
```

Compare the measured time to the estimate of devices divided by accepted connections per second. A large gap means a limit nobody has named, often TLS handshake CPU, a proxy limit or a session restore backlog.
