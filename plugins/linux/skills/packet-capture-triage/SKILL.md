---
name: packet-capture-triage
description: "Read a network capture you are authorised to examine — a pcap from tcpdump, tshark or Wireshark, or a cloud flow log — to answer why a connection failed or was slow. Filter to the one conversation first, then read the TCP handshake, retransmissions, resets, window and MSS, TLS alerts and DNS timing, and attribute the delay to the network, the peer or the application. Use for \"why does this connection time out\", \"the handshake fails only from one host\", \"requests are slow but the app logs look clean\", or \"what did the packet capture actually show\". Not for a firewall rule that blocks the path (firewall-rule-tracing), an MTU black hole (mtu-blackhole-hunt), a certificate error (tls-handshake-debugging), name resolution that fails outright (dns-resolution-debugging), or a Bluetooth link (ble-connection-debug)."
allowed-tools: Read, Glob, Grep, Bash(tcpdump:*), Bash(tshark:*), Bash(capinfos:*), Bash(editcap:*), Bash(strings:*)
---

# Packet capture triage

Good looks like a named conversation, a named stage that failed or stalled, and a timestamp
that places the delay on one side — with the filter that produced the view recorded, so a
reviewer can reproduce the read.

The job is hard because a capture is a flat list of frames and the answer is a relationship
between them: the gap between a SYN and its SYN-ACK, the retransmission that repeats a segment,
the RST that ends a healthy-looking stream. Reading frames one at a time hides the pattern.

## Scope

Use for: a capture or flow log you need to interpret; a connection that times out, resets or is
slow; a handshake that fails from one host or one network but not another; and confirming which
side of a connection dropped it.

Do not use for: a firewall rule that silently drops the traffic, which is
`firewall-rule-tracing`; an MTU or MSS black hole that hangs large packets but not small ones,
which is `mtu-blackhole-hunt`; a TLS certificate or trust error, which is
`tls-handshake-debugging`; name resolution that fails outright, which is
`dns-resolution-debugging`; a host under load that is not a network problem, which is
`high-load-triage`; or a Bluetooth or serial link, which is `ble-connection-debug`.

## Hard gates

1. **Authorisation and privacy.** A capture can contain credentials, cookies and personal data
   in cleartext. State whose traffic it is and why you may read it, and do not paste payload
   bytes into a report — cite the frame number and the header fields instead.
2. **Capture on the path that matters.** A capture taken at the client and one taken at the
   server show different loss; say where yours was taken before drawing conclusions.
3. **Read-only.** Triage never replays or injects traffic.

## Workflow

### 1. Establish what you have

```bash
capinfos ./capture.pcap          # duration, packet count, interfaces, encapsulation
tshark -r ./capture.pcap -q -z io,phs          # protocol hierarchy: what is actually in here
tshark -r ./capture.pcap -q -z conv,tcp        # TCP conversations with bytes and duration
```

`capinfos` first: a capture truncated at one second, or one that is all one protocol, changes
what can be answered. `-z conv,tcp` gives the top talkers and their durations, which is where
the slow connection usually shows up.

### 2. Filter to the one conversation

```bash
tshark -r ./capture.pcap -Y 'tcp.stream == 3' -V | head -80
tshark -r ./capture.pcap -q -z follow,tcp,ascii,3
```

Everything after this is about a single stream. Record the stream index and the two endpoints
with their ports; the ephemeral port identifies the client side.

[Capturing and filtering](references/capturing-and-filtering.md) has the capture commands
(tcpdump ring buffers, BPF syntax, tshark display filters) when you need to take one too.

### 3. Read the handshake and the teardown

Find the `SYN`, the `SYN-ACK` and the `ACK`. The time between `SYN` and `SYN-ACK` is the
round-trip plus the server's accept latency; a retransmitted `SYN` means the first was lost.
Read the end too: who sent `FIN` first, who sent `RST`, and whether the `RST` follows a data
segment (an application-level abort) or stands alone (a closed port or a firewall reject).

### 4. Read the loss and the window

- **Retransmissions** repeat a segment because no `ACK` arrived — real loss or an `ACK` that
  never came back. `tshark -Y 'tcp.analysis.retransmission'` lists them.
- **Duplicate ACKs** mean the receiver is missing a segment; three of them trigger a fast
  retransmit.
- **Zero window** means the receiver's buffer is full — the sender is fine, the reader is
  slow, which points at the application, not the network.
- **Window scaling and MSS** explain why one host is slow: a missing `wscale` option caps
  throughput regardless of bandwidth.

[Reading TCP and TLS](references/reading-tcp-and-tls.md) has the fields, the flags and the
`tshark` filters for each.

### 5. Read TLS and the application protocol

For TLS, find the `ClientHello`, the `ServerHello`, the certificate exchange and any `Alert`
record. An alert names the failure (`handshake_failure`, `certificate_expired`,
`unknown_ca`); a handshake that completes but stalls after the `Finished` is an application
delay, not TLS. A `ServerHello` that never arrives after a `ClientHello` is usually the server
or a middlebox, not the client.

### 6. Attribute the delay

Put every observed gap on a timeline and label the owner:

- the client's think time before the `SYN`;
- the network's RTT, from `SYN` to `SYN-ACK`;
- the server's time to first byte, from the request's last byte to the response's first;
- the application's transfer time, from first to last response byte.

The largest labelled gap is the finding. A capture cannot see inside the server, so a large
server gap is "the server took this long", not "the server's database was slow" — that is a
trace's job.

### 7. Report

Lead with the failing stage and the timestamp. Then the endpoints, the stream index, the filter
used, and the evidence frames. State where the capture was taken, because loss at the client
and loss at the server are different findings. Label what the frames show and what you
inferred.

## Anti-patterns

**Reading the whole capture in Wireshark's frame list.** The answer is the timing between
frames, which a summary line hides; filter to one stream and read the sequence.

**Calling a retransmission "packet loss".** A retransmission means an `ACK` did not arrive; the
segment may have been lost, delayed, or the `ACK` may have been lost. The location of the
capture tells you which.

**Blaming the network for a zero window.** A zero window is the receiver saying "stop"; that is
an application or host problem, and no amount of network tuning fixes it.

**Pasting payload bytes into a report.** A capture carries tokens and cookies; cite the frame
and the field, and redact the value.
