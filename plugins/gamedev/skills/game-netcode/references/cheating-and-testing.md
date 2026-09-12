# Server validation and network testing

Read this at steps 7 and 8. The two halves belong together because they answer the same question from opposite ends: what do you refuse to believe, and how do you find out whether any of it works before players do.

## Contents

- [The rule](#the-rule)
- [Validation by cheat class](#validation-by-cheat-class)
- [What validation cannot fix](#what-validation-cannot-fix)
- [Clocks and timestamps](#clocks-and-timestamps)
- [What to log](#what-to-log)
- [Why localhost proves nothing](#why-localhost-proves-nothing)
- [Test profiles](#test-profiles)
- [Linux: tc and netem](#linux-tc-and-netem)
- [macOS: Network Link Conditioner, dnctl and pfctl](#macos-network-link-conditioner-dnctl-and-pfctl)
- [Windows: clumsy](#windows-clumsy)
- [Cross-platform and containers](#cross-platform-and-containers)
- [In-engine emulation](#in-engine-emulation)
- [The desync detector](#the-desync-detector)
- [What to actually run](#what-to-actually-run)

## The rule

Anything the client is authoritative over is a thing the client can lie about. Not "might" — a popular game's protocol is reverse-engineered within weeks, and every value the server accepts without checking becomes a product someone sells.

The rule that follows is that the server accepts intent and never results. An input, an aim direction, a request to pick something up, a request to buy something. It computes the result itself, from its own state, with its own constants, on its own clock.

The second-order rule is that obfuscation is not validation. Encrypting the protocol, checksumming the binary and running an anti-cheat client all raise the cost of attacking a weak protocol; none of them makes a server that believes client-supplied positions safe. Fix the protocol first; those are what you add afterwards, if the stakes justify them.

## Validation by cheat class

| Cheat | What the protocol allowed | What the server does instead | The check |
| --- | --- | --- | --- |
| Speed hack | The client integrated movement and sent the resulting position or velocity | Re-simulate the move from the input using the server's movement function and constants | Displacement per tick against the maximum the character's state permits, including every legitimate boost |
| Teleport | The protocol carried positions upstream | Positions are output only; the client sends a button bitfield and a look direction | The absence of the field is the check |
| Noclip and out-of-bounds | Collision ran only on the client | Collision runs on the server against the server's copy of the level | Reject the move and re-simulate against the wall rather than accepting the position past it |
| Rapid fire | The server trusted a client-supplied fire time | Cooldowns counted in server ticks from the server's last accepted fire | Reject the command, do not queue it; a queued early shot is the same cheat delayed |
| Inflated or arbitrary damage | The client reported "I hit X for N" | The client sends aim and fire; the server traces and computes damage from its own weapon table | Damage is never a wire field |
| Impossible aim | Nothing; aimbots send legitimate inputs | Not a validation problem at all | Statistical detection over sessions, which is a different system |
| Item and currency duplication | The client asserted an inventory change | The inventory is server state; a client message is a request that can be refused | Apply the change once, in one place, transactionally, and make the operation idempotent against a retried request |
| Loot and drop manipulation | The client rolled the drop | The server rolls, from a seed the client never sees | Never send the seed, and never send the table |
| Instant interaction at range | The server took the client's word for proximity | Check distance and line of sight on the server at the server's tick | Include a tolerance for the client's interpolation delay, and no more |
| Extra-sensory information | The server sent state the player could not perceive | Cull before sending | This is area of interest, not validation |

The pattern across the table is that most validation is not a check bolted onto a message. It is the absence of a field: there is no cheat to check for if the protocol never carried the value.

## What validation cannot fix

Three classes stay open, and being clear about them prevents wasted effort.

**Information cheats.** Wallhacks, radar hacks, seeing through fog of war. The client has data it renders selectively, and no server check applies because no invalid message is sent. The only fix is not sending the data, which is area of interest and visibility culling — and in an RTS with fog of war, this conflicts directly with deterministic lockstep, which requires every peer to have the full simulation. That conflict is genuine and unresolved in the model; a lockstep RTS with fog of war is maphackable by construction.

**Input automation.** Aimbots, trigger bots, scripted combos. The inputs are individually legitimate; only their distribution is not. This is a detection problem over many sessions, not a validation problem within one.

**Collusion and account abuse.** Two players sharing information out of band, boosting, account selling. Not a netcode problem at all.

Say which of these the design is exposed to, so nobody spends a month on validation that was never going to address the complaint.

## Clocks and timestamps

Never trust a client clock, and never let a client name the tick its input applies to without bounding it. The protocol shape that works: the client tells the server which of the server's ticks its input was sampled against, the server clamps that value into a window around its own current tick minus the measured latency, and discards anything outside. A client that can claim an arbitrary tick can fire into the past — which is lag compensation, granted to the attacker on request.

The window is a real trade-off. Too narrow and legitimate players on jittery connections lose inputs; too wide and the exploit is back. Derive it from the server's own measurement of that client's round trip and jitter, and log every clamp so the distribution can be looked at.

## What to log

Rejecting an invalid input is better than silently correcting it, because a legitimate client hitting the rejection path is a bug you want to see and a correction hides it. Log, per client per session: rejected moves with the magnitude of the violation, clamped timestamps with the distance outside the window, refused interactions with the distance that failed, and the rate of each. Alert on the rate, not on the event — a single rejection is a lost packet, and a thousand is a modified client.

## Why localhost proves nothing

Two processes on one machine communicate over a loopback with a sub-millisecond round trip, no jitter, no loss, no reordering and an effectively unbounded bandwidth. Every artefact prediction, reconciliation, interpolation and lag compensation exist to hide is absent, and so is every bug in them. A netcode change tested only on localhost has been tested for compilation.

The corollary is that the network conditioner is part of the development setup, not part of a QA phase. Shape the loopback and leave it shaped.

## Test profiles

Keep these in the repository as a script or a config so results compare across builds, and run the whole set before any netcode change is called done.

| Profile | RTT | Jitter | Loss | What it catches |
| --- | --- | --- | --- | --- |
| Same city | 20 ms | 2 ms | 0% | The baseline; anything visible here is a bug, not latency |
| Cross-country | 80 ms | 10 ms | 0.5% | Missing prediction and missing lag compensation |
| Cross-ocean | 180 ms | 30 ms | 1% | An interpolation buffer sized for a good connection |
| Bad mobile | 250 ms | 80 ms | 5% | Reconciliation tolerances, and rollback depth caps |
| Broken | 120 ms | 20 ms | 10%, reordered and duplicated | Delta-compression fallbacks and duplicate-message handling |
| Freeze | 120 ms | — | 100% for 2 s | Timeout, reconnect and rejoin paths; this is what a Wi-Fi roam looks like |
| Asymmetric | One client at 20 ms, one at 200 ms | — | — | Lag compensation's fairness cost, and peeker's advantage |

The asymmetric case is the one most often skipped and the one that most resembles a real match.

## Linux: tc and netem

`netem` shapes the egress queue of an interface. Delay takes a mean and an optional jitter, and a distribution makes the jitter realistic rather than uniform.

```bash
set -Eeuo pipefail
# 180 ms mean, 30 ms jitter, normally distributed, 1% loss
sudo tc qdisc add dev eth0 root netem delay 180ms 30ms distribution normal loss 1%

# Change an existing qdisc rather than stacking a second one
sudo tc qdisc change dev eth0 root netem delay 120ms 20ms loss 10% duplicate 0.2% reorder 1% 50%

# Inspect and remove
tc qdisc show dev eth0
sudo tc qdisc del dev eth0 root
```

Three things to know. `reorder` has no effect without a `delay`, because reordering is implemented by sending some packets early out of the delay queue. `loss` accepts correlation and model arguments if you need bursty loss rather than independent drops. And `netem` shapes egress only, so a symmetric round trip means adding half the delay at each end, or redirecting ingress through an intermediate functional block device:

```bash
set -Eeuo pipefail
sudo modprobe ifb numifbs=1
sudo ip link set dev ifb0 up
sudo tc qdisc add dev eth0 handle ffff: ingress
sudo tc filter add dev eth0 parent ffff: protocol ip u32 match u32 0 0 \
  action mirred egress redirect dev ifb0
sudo tc qdisc add dev ifb0 root netem delay 90ms 15ms loss 1%
```

For two processes on the same machine, shape the loopback — `sudo tc qdisc add dev lo root netem delay 50ms` — which is the cheapest way to make a local two-client test honest. Remember that this delays everything on `lo`, including anything else on the machine talking to itself.

## macOS: Network Link Conditioner, dnctl and pfctl

Network Link Conditioner is a preference pane in Apple's Additional Tools for Xcode, downloaded separately from Xcode itself. It has presets for common connection classes and accepts custom profiles with in and out bandwidth, delay and loss. It is system-wide and it is the least fiddly option.

For per-port control, `dnctl` configures a dummynet pipe and `pfctl` decides what goes into it. Delay is in milliseconds and `plr` is a loss probability between 0 and 1:

```bash
set -Eeuo pipefail
sudo dnctl pipe 1 config delay 90 plr 0.01
echo "dummynet out proto udp from any to any port 7777 pipe 1" | sudo pfctl -f -
sudo pfctl -E

# Tear down
sudo pfctl -d
sudo dnctl -q flush
```

Editing `pfctl` rules from the command line replaces the active ruleset, so on a machine with an existing firewall configuration use an anchor rather than `-f -`.

## Windows: clumsy

Windows has no built-in equivalent. `clumsy` is the standard answer: MIT-licensed, built on WinDivert, no installation, and it captures packets system-wide from a filter expression, applying lag, drop, throttle, duplicate, out-of-order and tamper interactively while the game runs.

Its distinguishing feature is that it works on loopback, so two clients and a server on one developer machine can be tested under real conditions without a second box. The filter field takes a WinDivert expression — `udp and outbound` for all outbound UDP, narrowed by port for a specific game — and each effect is toggled independently with its own parameters, so a profile can be changed mid-match to see what the game does.

## Cross-platform and containers

`comcast` wraps `tc` and `iptables` on Linux and `pfctl` or `ipfw` on macOS and BSD behind one flag set, which makes a shared test script possible across a mixed team:

```bash
set -Eeuo pipefail
comcast --device=eth0 --latency=180 --packet-loss=1% --target-bw=1000 \
  --target-proto=udp --target-port=7777
comcast --stop
```

It prints the underlying commands before executing them, and `--dry-run` prints without executing, which makes it a usable way to learn the `tc` incantation as well as to run it.

For containerised servers, `pumba` applies `netem` to a running container without modifying the image:

```bash
set -Eeuo pipefail
pumba netem --duration 5m delay --time 180 game-server
pumba netem --duration 5m combine --delay --delay-time 120 --loss --loss-percent 10 -- game-server
```

`toxiproxy` is worth knowing about and worth not reaching for here: it is a TCP proxy, so it can degrade the matchmaking API, the account service and a WebSocket connection, and it cannot touch a UDP game channel at all.

## In-engine emulation

Engine-level emulation is more convenient than an OS-level conditioner and less faithful — it shapes what the engine's own transport sees, and it cannot reproduce a middlebox, a real MTU problem or the operating system's buffering. Use it for a quick loop and the OS-level tools for anything being signed off.

- **Unreal Engine** exposes network emulation as `NetEmulation.` console variables for packet lag, lag variance, loss, duplication and reordering, with separate incoming and outgoing settings, and the editor's play settings carry the same controls as named profiles. They are compiled into development and editor builds and out of shipping builds; list the current set from the console's autocomplete rather than from memory, since the names have changed across versions.
- **Unity** ships a network simulator in its multiplayer tools alongside Netcode for GameObjects, with packet delay, jitter and drop applied inside Unity Transport, configurable as presets from the editor and at runtime.
- **Godot** ships no packet conditioner. Shape it with `tc` on `lo`, which is straightforward because a Godot test session is usually several processes on one machine.

Whatever the engine offers, add an on-screen debug overlay showing round-trip time, jitter, packet loss, the current interpolation buffer, the size of the last snapshot and the number of inputs replayed per reconciliation. Netcode bugs are diagnosed from those six numbers, and nobody adds the overlay until after the bug they needed it for.

## The desync detector

For a deterministic model — lockstep or rollback — this is not optional and it is built before the netcode, because a divergence found by a player is a lost match with no evidence.

1. Hash the full simulation state at the end of every simulation tick, or every eighth tick if the hash is expensive. Include everything the simulation reads: positions, velocities, timers, the random number generator's state, entity ordering.
2. Exchange the hash with the frame number it belongs to, piggybacked on the input packet.
3. On a mismatch, halt and dump both states field by field, plus the last few hundred frames of input from every peer.
4. Report the first differing field, not the first differing hash. The frame number tells you when, and only the field tells you what.

The input log is worth keeping even when nothing diverges: a deterministic simulation plus its input log is a complete replay, which gives free bug reproduction, free spectating and an automated soak test that runs scripted matches under the profiles above and asserts no peer diverged.

## What to actually run

Before calling a netcode change done: every profile in the table above with at least two clients, the asymmetric pairing, one deliberate mid-match freeze and reconnect, one run at the maximum session player count, and — for a deterministic model — a soak of scripted matches with the desync detector armed. Record the debug overlay's six numbers for each profile and diff them against the previous build, because a regression in netcode shows up as a number moving long before it shows up as a complaint.
