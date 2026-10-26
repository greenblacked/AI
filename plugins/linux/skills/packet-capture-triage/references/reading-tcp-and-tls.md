# Reading TCP and TLS

Read this with one stream filtered. Every claim below is a field or a flag you can point at in
a frame, so the report cites frames rather than impressions.

## Contents

- [The handshake](#the-handshake)
- [The options that decide throughput](#the-options-that-decide-throughput)
- [Loss, reordering and the window](#loss-reordering-and-the-window)
- [Teardown: who ended it](#teardown-who-ended-it)
- [TLS records and alerts](#tls-records-and-alerts)
- [Attributing the delay](#attributing-the-delay)

## The handshake

```
client ──SYN──────────────►  server
client ◄─────────SYN,ACK────  server
client ──ACK──────────────►  server
```

- **Time from SYN to SYN-ACK** is the round trip plus the server's accept latency. It is the
  single best RTT estimate you have.
- **A retransmitted SYN** means the first SYN or its SYN-ACK was lost, or the server was not
  yet listening. `tshark -Y 'tcp.analysis.retransmission && tcp.flags.syn==1'`.
- **A SYN answered by RST** means the port is closed or a firewall rejected it (`-z expert`
  labels this). A SYN answered by nothing at all, with retransmits, is a silent drop — the
  signature of a firewall dropping rather than rejecting, which is `firewall-rule-tracing`.

## The options that decide throughput

The SYN and SYN-ACK carry TCP options. Read them once per stream:

| Option | Meaning if missing |
| --- | --- |
| MSS | The peer's maximum segment size; an old default of 536 caps every segment |
| Window scale (`wscale`) | Absent on one side caps the window at 64 KiB, so a long-fat path runs slow |
| SACK permitted | No selective acknowledgement, so one lost segment forces a bigger retransmit |
| Timestamps | No RTT measurement without a payload, and no protection against a wrapped sequence number |

A connection that is slow only over a long distance usually has a missing or small `wscale` or
a small receive window; that is a host configuration finding, not a network fault.

## Loss, reordering and the window

```bash
tshark -r cap.pcap -Y 'tcp.analysis.retransmission'      # a segment sent again
tshark -r cap.pcap -Y 'tcp.analysis.fast_retransmission' # after three duplicate ACKs
tshark -r cap.pcap -Y 'tcp.analysis.duplicate_ack'       # receiver missing a segment
tshark -r cap.pcap -Y 'tcp.analysis.zero_window'         # receiver buffer full
tshark -r cap.pcap -Y 'tcp.analysis.window_full'         # receiver window exhausted
```

- **Retransmission** — an ACK did not arrive in time. Whether the segment or the ACK was lost
  depends on where the capture was taken.
- **Duplicate ACK** — the receiver got an out-of-order segment and is asking for the missing
  one; three of them trigger fast retransmit.
- **Zero window / window full** — the receiver is not draining its buffer. The sender is
  healthy; the reader (application or host) is the finding.
- **Spurious retransmission** — a retransmit after the ACK was in flight; looks like loss but
  is not.

## Teardown: who ended it

```
FIN,ACK ──►     graceful close by the sender
RST ──────►     abrupt close
```

- A `FIN` followed by the peer's `FIN` is an orderly close.
- A `RST` after data means the application or the OS aborted the connection — often a socket
  closed with unread data, or a crash.
- A `RST` with no preceding data is usually a closed port or a middlebox reject.

## TLS records and alerts

```bash
tshark -r cap.pcap -Y 'tls.handshake.type == 1'   # ClientHello
tshark -r cap.pcap -Y 'tls.handshake.type == 2'   # ServerHello
tshark -r cap.pcap -Y 'tls.alert_message'
```

The handshake sequence: `ClientHello` → `ServerHello` → `Certificate` → `ServerHelloDone` →
`ClientKeyExchange` → `ChangeCipherSpec`/`Finished` on each side. What a gap means:

- **No `ServerHello` after a `ClientHello`** — the server or a middlebox dropped it; check the
  server and the path, not the client certificate.
- **An `Alert` record** names the failure: `handshake_failure`, `certificate_expired`,
  `unknown_ca`, `bad_certificate`. That is `tls-handshake-debugging`'s subject; record the
  alert and hand it over.
- **Handshake completes, then a stall** — TLS is done; the delay is the application. The
  `Finished` frame is the boundary.

Note that with TLS 1.3 the certificate and most of the handshake are encrypted; you will see
record sizes and timing but not the certificate, and the alert is encrypted too. Say so rather
than reporting a missing certificate as a fault.

## Attributing the delay

Build the timeline with absolute timestamps (`-tttt`):

| Segment | Owner | How to measure |
| --- | --- | --- |
| Last request byte → first response byte | server | the server's think time |
| SYN → SYN-ACK | network + server accept | the RTT estimate |
| First → last response byte | network throughput | window and MSS explain it |
| Before the SYN | client | application think time |

The largest labelled gap is the finding, and a capture can only label the gap at the boundary;
inside the server is a trace.
