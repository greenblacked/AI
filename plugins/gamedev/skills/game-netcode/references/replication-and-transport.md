# Replication and transport

Read this at steps 5 and 6: what to put on the wire, at what rate, and what to put it on. The two decisions are related — the transport decides what loss costs, and that decides whether a delta scheme is safe.

## Contents

- [The three kinds of replication](#the-three-kinds-of-replication)
- [Delta compression, and the part people leave out](#delta-compression-and-the-part-people-leave-out)
- [Area of interest](#area-of-interest)
- [Quantisation](#quantisation)
- [Prioritisation](#prioritisation)
- [Computing a budget](#computing-a-budget)
- [Why UDP for state](#why-udp-for-state)
- [Where reliable ordered is still right](#where-reliable-ordered-is-still-right)
- [Browser transports](#browser-transports)
- [Packet size, MTU and encryption](#packet-size-mtu-and-encryption)
- [Sources](#sources)

## The three kinds of replication

**Snapshot.** The full state of everything the client should know about, every send. It is stateless on the server, trivially recovers from loss because the next packet is complete, and it is the right starting point for a small game. It is also the most expensive, and it scales with world size rather than with change.

**Delta.** Encode only what changed against a reference state that both ends agree on — specifically, the last snapshot the client acknowledged. In a game where most objects are still most of the time, this is an order-of-magnitude saving. It costs server memory per client and a fallback path.

**Event.** A message describing something that happened rather than state that is: a shot was fired, a door opened, an item was picked up, a round ended. Events are usually small, usually rare, and usually cannot be dropped, which is what justifies a reliable channel for them.

Most games use all three: delta-compressed state for the continuous world, snapshots as the delta fallback, and reliable events for the discrete things. The mistake is using one mechanism for everything — reliable events for positions reintroduces head-of-line blocking, and state replication for a one-off effect means the effect is missed by anyone who was not connected at that instant.

## Delta compression, and the part people leave out

Quake III is the readable reference implementation, and it is worth describing precisely because the fallback is the part that gets omitted.

The server keeps the last 32 snapshots it sent each client. Each client acknowledges the newest snapshot it received. The server encodes the next snapshot as a delta against that acknowledged frame, writing only the fields that differ, and marking entities that entered or left the client's view. Two conditions force a fall back to a full baseline-relative snapshot: the acknowledged frame being older than 29 of the 32 kept, and the server's shared entity ring buffer having overwritten the entities that frame referenced.

Without those two fallbacks, a client that loses packets for a second has no valid reference state and never recovers — it either receives deltas against a frame it does not have, or the connection stalls. Build the fallback at the same time as the delta path, and test it under the 10% loss profile, because it is a path that never executes in development.

The same design gives an ordering property worth stating: because every packet is decodable against a state the client already has, packets may be dropped freely and a newer one supersedes an older one. That is what makes an unreliable transport correct here rather than merely tolerable.

## Area of interest

The largest bandwidth lever in any game with a world bigger than a screen, and the only defence against wallhacks that works. The principle is that the client is sent what its player can perceive, and nothing else.

| Scheme | Fits | Notes |
| --- | --- | --- |
| Radius | Small, open arenas | One distance check; cheap and crude |
| Grid or cell | Most 2D and 3D worlds | Subscribe to the player's cell and its neighbours; updates on cell change |
| Visibility precomputation | Indoor levels with rooms and portals | Culls through geometry, which radius cannot |
| Relevancy by role | MMOs, team games | Teammates and objectives are always relevant regardless of distance |

Two cautions. The audible radius is larger than the visible one, so culling on sight alone makes footsteps disappear. And the boundary is where cheating returns: a client that receives an entity one metre before it becomes visible can draw it, so build the cull for the strictest case the game can afford and accept the pop-in.

## Quantisation

Send the smallest representation that the player cannot distinguish from the exact one.

- **Position.** Fixed-point at the smallest unit that affects play. A centimetre is finer than any player perceives in a metre-scale world; a 32-metre arena at centimetre resolution needs 12 bits per axis rather than 32.
- **Orientation.** A normalised quaternion has three degrees of freedom, so send the three smallest components and a two-bit index naming the one that was dropped, reconstructing it from the unit constraint. Nine to eleven bits per component is ample for a character.
- **Velocity.** Usually derivable on the client from successive positions. Send it only where it drives prediction or an effect.
- **Angles.** A yaw in one byte is 1.4 degrees, which is too coarse for aiming and fine for a body facing. Use two different precisions for the two purposes.
- **Booleans and enumerations.** Bitfields, not bytes. A dozen state flags is two bytes, not twelve.

Quantise on the server before the state is used for anything else, so the client's reconstruction is exactly the server's value. Quantising only on the wire means the client's replayed prediction diverges from the server's simulation by the rounding error, every tick, which reconciliation then corrects visibly.

## Prioritisation

When everything relevant does not fit in a packet, send the most important of it rather than sending all of it late. The Tribes engine's ghost manager is the canonical design: every replicated object has a priority derived from distance, recency of change and gameplay importance, and each packet is filled with the highest-priority objects that fit, with the rest carried forward.

This turns bandwidth from a constraint that breaks the game into one that degrades it gracefully: on a bad connection the distant scenery updates slowly and the player being shot at updates every tick. Tribes was designed against a 28.8 kbit/s modem, which is a useful reminder of how little bandwidth a good scheme needs.

## Computing a budget

Do the arithmetic before optimising anything. The inputs are entity count in view, bytes per entity after quantisation, and send rate.

- 20 entities × 20 bytes × 20 Hz = 8 KB/s downstream per client, about 64 kbit/s. Unremarkable.
- 60 entities × 32 bytes × 30 Hz = 57.6 KB/s, about 460 kbit/s. Noticeable on a poor connection, and 3.6 MB/s of upstream from a 64-player server instance.
- Inputs upstream are negligible in comparison: a bitfield and two angles at 60 Hz is well under 1 KB/s, which is why re-sending the last several inputs in every packet is the right call.

Three consequences fall out of that arithmetic. Server upstream, not client downstream, is usually the limit, and it scales with the square of the player count when everyone can see everyone — which is the case for area of interest, not for compression. The send rate multiplies everything, so halving it saves more than any encoding change. And a mobile or console target has a data cost as well as a bandwidth cost, which is a product decision rather than an engineering one.

## Why UDP for state

TCP delivers a reliable ordered byte stream, and the ordering is the problem. When one segment is lost, every segment received after it is held in the kernel until the retransmission arrives, even though those later segments are sitting in the receive buffer already decoded. For a game that means the newest position of every entity is withheld while waiting for a position that is already obsolete. The correct recovery for state is to use the newer state and forget the old one, and TCP has no way to be told that.

The secondary reasons are real but smaller: TCP's congestion response to loss is a throughput collapse that a fixed-rate game does not want, and Nagle's algorithm coalesces small writes unless disabled.

What UDP costs is that everything TCP provided has to be built: connection establishment, a sequence number, an acknowledgement scheme, keepalives, timeouts, MTU handling, congestion awareness, and encryption. Use an existing library — the engine's own, or a standalone reliability layer — rather than writing this for a first game, and understand what it does before trusting it.

## Where reliable ordered is still right

Reliability is a per-message property, not a per-connection one. The list that needs it is short and predictable:

- Authentication, session establishment, matchmaking.
- Level and map load, initial world state, joining mid-session.
- Chat, and anything with a transcript.
- Economy: purchases, inventory changes, currency.
- Discrete gameplay events whose loss changes the outcome: a kill, a round end, a score, a spawn.

Implement these as reliable channels over the same UDP connection, with independent ordering per channel so a lost chat message does not delay a spawn event. Opening a TCP connection alongside the UDP one gives two congestion states, two sets of timeouts, two firewall problems and a new class of bug where the two disagree about whether the session is alive.

The exception is genuinely out-of-band traffic — the account API, the store, the patcher, telemetry. That is HTTP, it belongs on HTTP, and it is designed as a web API rather than as part of the netcode.

## Browser transports

A browser cannot open a UDP socket. The options, in order of preference for game state:

| Transport | Unreliable delivery | Costs |
| --- | --- | --- |
| WebTransport over HTTP/3 | Yes, datagrams, plus independent streams on the same connection | Needs HTTP/3 on the server and a certificate the browser trusts; browser support is narrower than WebSockets, so check the actual target browsers |
| WebRTC data channels | Yes, when configured unordered with no retransmissions | ICE, STUN and a TURN relay fallback, a signalling server, and an SCTP-over-DTLS stack on the server. Substantial machinery for a game that has no other use for peer connections |
| WebSockets | No — TCP underneath | The head-of-line problem in a game loop. Acceptable for turn-based, card and strategy games, and for the reliable channel of any game |

The honest routing: a turn-based or slow game in a browser uses WebSockets and is finished. A real-time browser game starts with WebTransport if the target browsers support it, and falls back to WebRTC data channels if they do not. Do not reach for WebRTC because it is the familiar name; it is the heavier option and its NAT machinery is pure cost when the server is a server.

## Packet size, MTU and encryption

Keep a datagram's payload under about 1200 bytes. The common path MTU is 1500 bytes including headers, tunnels and VPNs reduce it, and an IP-fragmented datagram is lost entirely when any one fragment is lost — so a 2000-byte packet on a 1% loss link is worse than two 1000-byte packets. When a message genuinely exceeds that, fragment it in the protocol where a missing fragment can be requested, rather than letting IP do it.

Encrypt the transport. DTLS, or the handshake your networking library provides, applied to everything including the state channel. Plaintext game traffic is readable by anyone on the path and rewritable by anyone in the middle, which converts a cheating problem into a trivial one.

## Sources

- Quake III Arena source, id Software, GPL — `code/server/sv_snapshot.c` for the delta encoding and both fallback conditions, `code/qcommon/qcommon.h` for the 32-frame history.
- "The TRIBES Engine Networking Model", Mark Frohnmayer and Kevin Gift, GDC 1999 — the ghost manager, prioritised replication and the modem-era bandwidth budget.
- RFC 8831, WebRTC Data Channels — the ordered and retransmission parameters that make a data channel unreliable.
- RFC 9221, An Unreliable Datagram Extension to QUIC — the datagram mechanism WebTransport exposes.
- "Overwatch Gameplay Architecture and Netcode", Tim Ford, GDC 2017 — relevancy and the cost of raising the send rate.
