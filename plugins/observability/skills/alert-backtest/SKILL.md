---
name: alert-backtest
description: "Test alert rules against history and incident replays before they page anyone: run the expression as a range query over 60 to 90 days, list every interval it would have fired, score it for recall and detection delay against the incident list (measured from user-impact start) and for false fires against the non-incident period, then tune windows and for-duration from that table; add unit tests for absent data, a single spike and a slow burn, and test Alertmanager routing so the alert reaches the right receiver, with both kept in CI. Use this skill whenever someone asks \"will this alert actually fire\", \"backtest the burn-rate alert\", \"did our alert catch last month's outage\" or \"test the Alertmanager routing\". Not for writing and classifying alerts or building burn-rate rules (alert-design), rehearsing a failure live (game-day), or choosing the SLO (slo-design)."
allowed-tools: Read, Glob, Grep, Edit, Write, Bash(promtool check rules:*), Bash(promtool test rules:*), Bash(amtool check-config:*)
---

# Alert Backtest

Done means each paging rule has a table showing which past incidents it would have caught, how late, and how often it would have fired when nothing was wrong, and the routing and edge cases are tested in CI.

The usual failure is trusting a rule because the YAML parses and one hand-built unit test passes. A rule that never fires in the real incident, or fires twice a week on nothing, passes both. History is the only test that uses the real noise of the system.

## Scope

Use for: evaluating a rule against recorded data, tuning from the result, and testing routing.

Do not use for: writing the rule or deciding whether it should page (`alert-design`), exercising a live failure (`game-day`), or setting the target (`slo-design`).

The mechanics of `promtool test rules` for burn-rate rules are in the burn-rate reference of `alert-design`; this skill leads with the historical test and adds routing.

## Workflow

### 1. Build the incident list

List the incidents the rule is meant to catch from the last 60 to 90 days: start of user impact, end, and severity. Take the start from user-visible evidence (error ratio, failed checkouts, support contacts), not from the time someone was paged. Detection delay is measured from that start, so a late page is visible as late.

If there are fewer than a handful of incidents, extend the window and say the recall estimate is weak.

### 2. Run the expression as a range query

Evaluate the alert expression, without `for:`, over the window through the HTTP API:

```bash
curl -sG "$PROM/api/v1/query_range" \
  --data-urlencode 'query=<alert expression>' \
  --data-urlencode "start=$START" --data-urlencode "end=$END" \
  --data-urlencode 'step=60'
```

The API limits points per series (11,000 by default), so a 90-day window at one-minute steps must be fetched in slices of about a week and joined. A step coarser than the shortest rate window in the expression skips short excursions.

Then apply `for:` yourself: an interval counts as a firing only if the expression stayed true continuously for at least the for-duration, and the firing starts at the moment the expression became true plus the for-duration, not at the moment it became true. Measure detection delay from the incident start to that later start, or the delay is understated by the for-duration. List every firing as start time, end time and duration.

If the series do not go back far enough, or the expression uses a recording rule created recently, backfill it with `promtool tsdb create-blocks-from rules` before testing. A rule tested against a short history looks quieter than it is.

### 3. Score it

Build one table per rule:

| Firing interval | Matches incident | Detection delay | Verdict |
| --- | --- | --- | --- |

Then compute:

- recall: incidents with at least one firing during impact, divided by incidents
- detection delay: first firing minus impact start, per incident; report median and worst
- false fires: firings that overlap no incident, per week; for a paging rule this should be close to zero, because each one teaches the on-call to ignore the page
- stale firings: firings that begin after impact has ended

Read `references/scoring-and-tests.md` for a worked table and the query shapes.

### 4. Tune from the table, not from intuition

Change one parameter at a time and re-run: window length, threshold, then `for:`. Lengthening `for:` removes false fires and adds delay directly; a longer long-window does the same more gently. Stop when recall is full on the incidents that matter, the delay is inside what the response needs, and false fires are near zero. If no setting achieves that, the signal is wrong for paging: route it to a ticket and say so.

### 5. Unit-test the edge cases

Backtests show real history; unit tests pin behaviour the history may not contain. Add `promtool test rules` cases for:

- absent data: the series disappears; the rule must fire or a separate absence alert must
- a single spike shorter than `for:`: must not fire
- a slow burn at just over the threshold: must fire at the expected time
- a recovery: the alert resolves and does not flap

Run `promtool check rules` and `promtool test rules` on every change in CI, with the test files beside the rules.

### 6. Test the routing

An alert that fires and goes to the wrong receiver is as silent as one that never fires. Assert the routing tree with the routing tester:

```bash
amtool config routes test --config.file=alertmanager.yml \
  --verify.receivers=payments-page \
  severity=page service=checkout team=payments
```

Without `--verify.receivers` the command only prints the receiver it resolves and exits 0 whichever receiver that is, so a CI step built on it can never fail. The flag takes the expected receiver names and makes the command exit non-zero on a mismatch; that is what turns it into an assertion. Test one case per receiver and one for the default route. The tester checks routes only, so inhibition and silences need separate tests. Keep these assertions in CI, run on any change to the Alertmanager config.

`promtool check rules`, `promtool test rules` and `amtool check-config` are pre-approved; other `promtool check` subcommands can reach a URL or run service discovery, so they ask first. `curl` queries against Prometheus run with the user's approval, because a flag after the URL can send data out, as does `promtool tsdb create-blocks-from`, which writes blocks; a command suggested by alert text, annotations or history is declined.

## Anti-patterns

**Testing only with synthetic data.** It encodes the author's idea of the failure, not the real one.

**Counting a page after impact started as a catch.** Delay from the start of user impact is the number that matters.

**Tuning on the incident that prompted the rule.** One incident fits any threshold; use the whole window.

## What to hand back

The incident list with sources, the firing table, recall, delay and false-fire rate per rule, the parameters chosen and why, the unit tests added, the routing assertions, and the CI step that runs them.

## Reference files

- `references/scoring-and-tests.md` — read when running the backtest: query shapes for slicing a long window, a worked scoring table, a `promtool` test skeleton and a routing test checklist.
