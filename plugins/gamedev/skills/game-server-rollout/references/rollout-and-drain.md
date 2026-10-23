# Rollout and drain

## Contents

expand and contract, handshake and pool keys, drain states, pool sizing, a rollout checklist

## Expand, migrate, contract

For any schema or format change the server reads or writes (player profile, match results, inventory):

1. Expand: deploy a build that can read both the old and new shape and still writes the old one. Safe to roll back because nothing new is written yet.
2. Migrate: switch writes to the new shape, backfill existing records.
3. Contract: after the rollback window is closed and no old build can run, remove the old shape.

Each step is its own deploy. Combining expand and migrate in the build that is also the first canary removes the rollback.

## Handshake and pool keys

- The client sends a protocol version, and a content or build identifier if rules depend on data files. The server answers with accept, or reject with a reason code the client can show ("update required", "server ahead of you").
- Key matchmaking pools by the protocol version, never by guessing from the client's build string. A client that cannot find a lobby after an update is almost always one of: pool keyed by the wrong field, or new pool empty because it was not warmed.
- Keep the reject path tested. A server that closes the socket on mismatch looks identical to a network fault in player reports.

## Drain states

```text
ready -> allocated -> (match ends) -> draining? -> exited
ready ------------------------------> draining -> exited   (idle, no match held)
```

- Idle old servers exit at once when drain starts.
- Allocated old servers continue to the end of their match, then exit rather than returning to ready.
- A server must stop advertising itself as available the instant it is allocated or marked draining; the usual leak is a gap between allocation and the matchmaker learning about it.
- Match cap: take the 99th percentile match length plus a margin, or the rule "game ends after the current round". Document it; a drain with no cap has no end.

## Pool sizing

Warm pool per region (new build) = peak concurrent matches in that region x fraction of matches that start during the overlap window + the ready buffer you normally keep. Example arithmetic: 400 peak matches, a 30 minute overlap against a 30 minute average match means roughly all of them turn over once, so size close to peak before the flip. Add the old pool's remaining servers to cost, since both run for the overlap.

If servers boot slowly, include boot time: pool must be ready before the flip, not scaling up after it.

## Checklist

- [ ] Protocol version and reject reason in handshake
- [ ] Pools keyed by protocol; old and new both visible to matchmaker
- [ ] Data change additive; separate migrate step planned
- [ ] Match cap and drain deadline written down
- [ ] Warm pool sized and verified ready per region
- [ ] Canary region, gates and their thresholds chosen before the deploy
- [ ] Rollback flipped once in test
- [ ] Support and community told when the client update and server flip land
