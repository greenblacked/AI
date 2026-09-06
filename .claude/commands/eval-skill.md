---
description: Score whether one skill's or subagent's description actually triggers, by running its eval queries against the whole catalogue of descriptions.
argument-hint: [skill or subagent name, or --all]
allowed-tools: Bash(python3:*), Read, Glob
---

Score the trigger eval set for `$0`. A description nobody has tested is a guess, and the
interesting output is not the headline number but the specific query that came out wrong,
because that names the phrasing the description is missing.

```bash
python3 scripts/run_trigger_eval.py --skill "$(find plugins -type d -name "$0")" --verbose
# or, for a subagent:
python3 scripts/run_trigger_eval.py --agent "$(find plugins -path "*/agents/$0.md")" --verbose
```

Use `--all` if that was the argument. This calls a model three times per query, so it
costs real money and real time — say what it is about to run before running it if the set
is large. Add `--budget 8000` to score the description the way the runtime shows it when
the listing is over budget, and `--baseline` with an earlier `--json` output to see what
moved.

Report four numbers and then stop presenting numbers:

- **recall** — of the queries that should fire, how many did. Low recall is
  under-triggering, the failure mode nobody notices, because a skill that never fires
  looks exactly like a skill that was never needed.
- **specificity** — of the queries that should not fire, how many correctly did not. Low
  specificity means the description claims too much and will steal invocations from its
  neighbours.
- **routing** — of the negatives that name the sibling that should win, how many went
  there. This is the one that catches a description stealing a neighbour's queries; a
  plain negative cannot see it.
- **pass rate** against the threshold. `narrow` beside it counts queries decided by a
  split vote, which is where a description sits on the model's decision boundary.

Then do the part that matters: for every query that came out wrong, quote it, say which
skill fired instead, and decide between two explanations — the description is missing a
phrasing, or the label is wrong. Both happen, and a mislabelled query silently caps the
score forever. Say which you think it is and why.

If the harness itself fails — the CLI is missing, a call times out — report that and stop.
A run where the tool never answered scores as perfect specificity, and reporting it as a
result would be worse than reporting nothing.

Do not edit the description to raise the score. Say what you would change and let the
author decide.
