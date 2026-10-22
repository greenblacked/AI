---
name: matchmaking-tuning
description: "Tune how a multiplayer game groups players, trading queue time against match quality. States the target as two numbers first (median and p95 queue time per tier, and a quality metric such as predicted win probability of 0.4 to 0.6), checks real population by region, hour, platform and party size before touching the formula, picks the rating model (Elo or Glicko-2 for 1v1, TrueSkill-style for teams), widens the search on a written schedule with a ceiling, rates parties by combined rating plus a premium, and replays historical queue snapshots offline before any A/B. Use for \"queues are ten minutes at night\", \"stomps in low ranks\", \"new players get matched with veterans\", \"is our rating system Elo, Glicko or something else\", \"parties of different sizes ruin matches\". Not for unit or weapon numbers (game-balance), netcode (game-netcode), or server rollout (game-server-rollout)."
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Matchmaking Tuning

Tuning is done when a written target of queue time and match quality is met for each population tier, shown first on replayed history and then in one measured experiment, and the player outcomes that matter (leaving after a match, coming back the next day) did not get worse in any quality bucket.

Matchmaking is a trade, not an optimum. A tighter match takes longer to find; a faster queue is a worse game. Most complaints are filed against the formula, and most of the time the formula is not the cause: the pool is thin at that hour, in that region, on that platform, for that party size, and no weighting can make players who are not there. Retuning the algorithm to fix a population problem makes quality worse everywhere else for no gain at the hour in question.

## Scope

Use for: long queues, lopsided matches, new-player experience, choosing or replacing a rating system, party handling, and the evidence needed to change any of them.

Do not use for: the numbers of units, weapons or maps themselves, or win rate by skill band as a balance question (`game-balance`), latency and server-side netcode (`game-netcode`), or deploying server builds that the matchmaker routes to (`game-server-rollout`).

## Workflow

### 1. State the target as two numbers

Before touching the algorithm, write:

- Queue time: median and p95, per population tier (for example the busy regions at peak, versus small regions or off-hours). One global number hides exactly the tiers that complain.
- Match quality: a metric you can compute for every match, such as either side's predicted win probability being within 0.4 to 0.6 (the stronger side at most 0.6), or the spread in rating between sides.

An argument that "matches feel bad" has no way to end. These two numbers do.

### 2. Pull the actual population

Measure concurrent players waiting, by region, hour of day, platform, game mode and party size, over several weeks. Queue time is mostly a function of arrival rate and how finely the pool is sliced. Read `references/queue-analysis.md` for the queries and how to read the result.

Then decide which of these you are looking at:

- Thin pool: players are queuing alone in a slice with few people. The fixes are merging pools (cross-region within a latency limit, cross-platform where the game allows it, fewer separate queues per mode) or widening search sooner. Reweighting does nothing.
- Bad formula: pool is deep but matches are poor. Go to step 3.

### 3. Pick the rating model from the game

- One versus one: Elo or Glicko-2. Glicko-2 adds a rating deviation, which is what lets a returning or new player move quickly.
- Teams, free-for-all, or variable team sizes: a TrueSkill-style model, which handles uncertainty and attributes team outcomes to members.
- Whatever the model, give new accounts high uncertainty, so their rating converges in a few matches instead of dozens. Place them in a provisional pool, shielded from veterans, until the uncertainty falls below a stated value. The mistake to avoid is starting everyone at the mean with the same confidence as a veteran: new players then drag the average down and are matched as though their rating were known.

For Elo-style ratings, a rating difference of about 70 points corresponds to a 60 percent expected win for the stronger side (a 400-point logistic scale), so the 0.4 to 0.6 band equals roughly a 70 point spread; use the model's own prediction rather than this approximation once you have one.

### 4. Widen the search on a written schedule

The window of acceptable rating difference grows with time spent waiting. Write it down as a table (for example: 0 to 15 seconds within a narrow band, then wider each interval) and set a ceiling beyond which the player is not given a bad match. At the ceiling choose one of: a bot or backfill opponent, a longer-wait message that explains why, or an invitation to a different mode. Decide the ceiling per tier: a top-rank player at 4 a.m. has a different acceptable wait from a mid-rank at peak.

Without a ceiling, the queue silently degrades into random matching at exactly the hours you most want to keep players.

### 5. Rate parties by combined strength, never split them silently

A party coordinates, and that is worth rating points beyond the individual sum. Rate a party by combined rating plus a coordination premium that grows with party size, estimated from historical results rather than guessed. Match parties against parties of similar size where the pool allows it, and against solo players only with the premium applied. Splitting a party to make the numbers work is not acceptable without telling them; players leave over it.

### 6. Validate offline before any experiment

Replay historical queue snapshots (who was waiting, with which rating, region, party, and when) through the proposed matcher. Score queue time and predicted fairness against the current matcher on the same snapshots. This is cheap, repeatable and has no player cost. Change one thing per replay (the formula, the widening schedule, a pool merge) so you know what moved the result.

### 7. Run one change per experiment and gate on player outcomes

Only what survives replay goes to a live A/B, and one change at a time. A/B design (assignment, sample size and duration, and how to avoid interference between arms, which is real in matchmaking because arms share one pool) deserves care; treat the arms as separate pools or split by region where that can be arranged. Primary metrics are the targets from step 1. Gate on post-match leave rate and next-day return, broken out by quality bucket, since an improvement on average can hide a worse experience for the tail that matters.

## Hand back

The two-number targets per tier; the population findings and whether the cause was pool or formula; the rating model and new-account policy; the widening schedule and ceilings; party rules; replay results against current; and, if run, the experiment result with guardrail metrics by bucket.

## Anti-patterns

**Reweighting to fix a thin pool.** There is nobody to match.

**One global queue-time metric.** It averages the busy region into the quiet one.

**New players at the mean with full confidence.** They either stomp or get stomped for thirty matches.

**No ceiling on widening.** The system quietly stops matching by skill.

**Splitting parties silently.** The result is both lopsided matches and angry groups.

## References

- `references/queue-analysis.md` - read at steps 1, 2 and 6: population queries, the replay harness shape, and the widening schedule template.
