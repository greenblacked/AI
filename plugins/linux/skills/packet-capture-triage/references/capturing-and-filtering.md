# Capturing and filtering

Read this when you need to take a capture rather than read one, or when the first read needs a
better filter. The rule throughout: capture broadly, filter narrowly, and write down the filter
you used so the read is reproducible.

## Taking a capture

```bash
# Everything on one interface to a rotating set of files, not to memory
sudo tcpdump -i eth0 -s 0 -w /tmp/cap.pcap -C 100 -W 10

# One host and one port, which is usually enough
sudo tcpdump -i any -s 0 -w /tmp/cap.pcap host 10.0.0.5 and port 443

# Read it back with timestamps and no name resolution
sudo tcpdump -r /tmp/cap.pcap -nn -tttt | head
```

- `-s 0` captures the whole frame; the old default snaplen truncated to 68 bytes and cut off
  payloads, which is why an old capture shows headers but no data.
- `-C` and `-W` bound the capture to a ring of files so a long run does not fill the disk.
- `-i any` captures on all interfaces; the link-layer header then varies, which some filters
  and Wireshark decoders care about.
- `-nn` keeps addresses and ports numeric; name resolution adds latency and hides the real
  address behind a stale name.
- `-p` avoids putting the interface in promiscuous mode; on a switched network a host only
  sees its own traffic anyway, which is a common reason a capture "shows nothing".

## BPF: the capture filter

The `host ... and port ...` syntax is Berkeley Packet Filter, applied in the kernel before the
copy, so it is cheap. Common forms:

| Goal | Filter |
| --- | --- |
| One host | `host 10.0.0.5` |
| One subnet | `net 10.0.0.0/24` |
| One port | `port 443` |
| A conversation | `host 10.0.0.5 and host 10.0.0.9 and port 5432` |
| TCP only | `tcp` |
| Not SSH, to cut noise | `not port 22` |
| A SYN only | `tcp[tcpflags] & tcp-syn != 0` |
| RST only | `tcp[tcpflags] & tcp-rst != 0` |

BPF is not the display-filter language; `-Y` is tshark's display filter and has its own syntax.
Mixing them up is why a capture comes back empty.

## Display filters (tshark `-Y`)

Applied after decoding, so they can reference decoded fields:

```bash
tshark -r cap.pcap -Y 'ip.addr == 10.0.0.5 && tcp.port == 443'
tshark -r cap.pcap -Y 'tcp.flags.reset == 1'
tshark -r cap.pcap -Y 'tcp.analysis.retransmission'
tshark -r cap.pcap -Y 'tls.alert_message'
tshark -r cap.pcap -Y 'dns.flags.rcode != 0'
```

## Useful one-shot statistics

```bash
tshark -r cap.pcap -q -z conv,tcp          # per-conversation bytes and duration
tshark -r cap.pcap -q -z io,phs            # protocol hierarchy
tshark -r cap.pcap -q -z expert            # built-in anomaly hints (retransmit, zero window)
tshark -r cap.pcap -q -z follow,tcp,ascii,0
```

The `expert` view is a shortcut: it flags the same retransmissions, resets and window
conditions the manual read looks for, but it does not attribute them, which is the actual work.

## Trimming a large capture

```bash
editcap -A '2026-10-26 10:00:00' -B '2026-10-26 10:05:00' big.pcap window.pcap
editcap -c 1000 big.pcap - | tshark -r - ...
```

Keep the original and work on a copy; a trimmed capture is the artifact you attach to the
finding, and its time bounds are part of the record.

## Flow logs are not captures

A cloud flow log (VPC flow logs, NSG logs) records five-tuples, byte and packet counts and an
action (`ACCEPT`/`REJECT`), not payloads or TCP flags. It answers "was traffic allowed and how
much of it", not "which side reset". Use one for the allow/deny question and a capture for the
how.
