---
name: game-server-rollout
description: "Deploy a new dedicated game server build without killing live matches or stranding players on mismatched versions. Treats the fleet as long-lived sessions, not requests: fixes the version contract first (handshake protocol version, pool keyed by build, an N and N-1 window or a forced update), drains old servers under a hard cap on match length, warms the new pool per region before flipping the matchmaker, canaries one region on crash rate per match-hour, match-start success and p95 tick time, and keeps a schema-safe rollback. Use for \"patching the servers drops everyone mid-match\", \"how do we roll out a server build with a client patch\", \"old clients can't find a lobby after the update\", \"drain servers before deploy\". Not for stateless services (release-strategy), pod manifests (k8s-workloads), patch calendar and comms (game-live-ops), or the client binary (mobile-release)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Game Server Rollout

A rollout is done when a new server build serves all new matches, no match was interrupted by the deploy, clients of every supported version found a lobby throughout, and the old build can be switched back to until you decide otherwise.

Request-serving services can be replaced one instance at a time because any request can go to any instance. A dedicated game server holds one match, in memory, for fifteen minutes to an hour, with players attached to it by address. Restarting it ends the match; ignoring versions strands whoever is on the wrong side of the deploy. A standard rolling update, which treats a server as disposable, is therefore the usual cause of the incident this skill prevents. The second cause is releasing the server and the client on separate clocks, so a player who has not updated is routed to a server that refuses them.

## Scope

Use for: deploying a dedicated or session-based game server fleet, coordinating it with a client patch, draining servers, and deciding how long old and new builds coexist.

Do not use for: stateless services where a standard staged rollout fits (`release-strategy`), writing the Kubernetes manifests themselves (`k8s-workloads`), the patch calendar and player-facing communication (`game-live-ops`), or shipping the client binary through the stores (`mobile-release`).

## Workflow

### 1. Decide the version contract first

Everything else depends on this and it is hard to change under pressure. Write down:

- The protocol version carried in the connection handshake. A server rejects a mismatched client with an explicit "update required" reason, not a timeout.
- A matchmaking pool keyed by build (or protocol), so a client is only ever offered a server it can speak to.
- The overlap policy: either N and N-1 clients are both served for a stated window, or the update is forced on release. Pick by whether the protocol and simulation can actually overlap. If gameplay rules change in a way that makes N and N-1 players unfair or incompatible in one match, they cannot share one and the pools must be separate.

Pre-announce forced downtime only when the protocol cannot overlap. A window of mixed versions is usually cheaper than a maintenance announcement; the cost is running two pools for its duration.

### 2. Check the data change is backward compatible

Rollback only works if the old build can read what the new build wrote. Before shipping, confirm that any schema or save-format change is additive, that the new build still writes what the old reads for the duration of the window, and that the migration is a separate earlier deploy where it cannot be. If it is not backward compatible, the rollback step below does not exist and the rollout needs a stricter canary. See `references/rollout-and-drain.md` for the expand, migrate, contract sequence.

### 3. Drain the old build

Mark old-build servers as draining: they accept no new matches, they finish the ones they hold, then they exit. Two controls make that bounded:

- A hard cap on match length (or a "match ends after the current round" rule once drain starts), so a drain has a known end. Without it, one endless lobby holds a server for days.
- A drain deadline policy: when the deadline arrives, decide in advance whether stragglers are ended with a clean result screen or allowed to finish. Never kill without warning.

On Kubernetes, a game server fleet controller that distinguishes servers holding a match from idle ones (Agones is the common one) lets a rolling update leave allocated servers running while replacing idle ones. If you use plain Deployments, `terminationGracePeriodSeconds` must be longer than the match cap or the pod is killed mid-match, and the pod must stop reporting itself available as soon as it is allocated.

### 4. Warm the new pool before flipping

Bring the new build up per region before moving traffic. Size the warm pool from peak concurrent matches times the fraction that will start during the drain overlap, plus headroom for the ready buffer. Starting too small means new matches wait for servers to boot, and queue time rises on the day of the release. Then flip the matchmaker's pool pointer for new matches; existing matches are untouched.

### 5. Canary one region and gate on game signals

Send one region (the quietest that is representative) to the new build first. Pod health says nothing about a bad game server. Gate on:

- Crash rate per match-hour on the new build against the old.
- Match-start success rate (allocation to first player connected).
- p95 server tick time, because a performance regression shows here before it shows in complaints.
- Player-visible error and disconnect rate.

Hold for at least a full peak period for that region before widening, since the bugs that matter appear under load. Widen region by region.

### 6. Keep a working rollback

Rollback means pointing the matchmaker's pool back so new matches use the old build, with the old servers still running as a warm pool for the whole canary and a short while after. Do not tear down the old fleet until the new one has gone through a peak in every region. Practise the flip in a test environment: an untried rollback is a second experiment running inside the first.

### 7. Measure it

Record per deploy: matches interrupted (the target is zero), seconds each old server spent draining, queue time during overlap against its usual value, players refused for version, and the cost of the double fleet. Compare across deploys; a rising drain time means match caps are drifting.

## Hand back

The version contract and overlap window; the data compatibility check result; the drain policy and cap; per-region pool sizes; canary gates with the observed values; the rollback procedure and when it was last tested; and the per-deploy numbers from step 7.

## Anti-patterns

**A standard rolling update on game servers.** It kills matches in progress because the controller cannot tell a busy server from an idle one.

**Gating the canary on pod health.** A server can be healthy and crash every match after round three.

**Shipping the client and server on separate, unannounced clocks.** The gap between them is where players are stranded.

**A rollback that cannot be exercised.** Usually because the new build already migrated data the old build cannot read.

## References

- `references/rollout-and-drain.md` - read at steps 2 to 4: the expand-and-contract data sequence, handshake wording, drain state machine and pool sizing arithmetic.
