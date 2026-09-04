---
description: Score whether one skill's description actually triggers, by running its eval queries against the whole catalogue of descriptions.
argument-hint: [skill name, or --all]
allowed-tools: Bash(python3:*), Read, Glob
---

Score the trigger eval set for `$1`. A description nobody has tested is a guess, and the
interesting output is not the headline number but the specific query that came out wrong,
because that names the phrasing the description is missing.

```bash
python3 scripts/run_trigger_eval.py --skill "$(find plugins -type d -name "$1")" --verbose
```

Use `--all` if that was the argument. This calls a model once per query, so it costs real
money and real time — say what it is about to run before running it if the set is large.

Report three numbers and then stop presenting numbers:

- **recall** — of the queries that should fire, how many did. Low recall is
  under-triggering, the failure mode nobody notices, because a skill that never fires
  looks exactly like a skill that was never needed.
- **specificity** — of the queries that should not fire, how many correctly did not. Low
  specificity means the description claims too much and will steal invocations from its
  neighbours.
- **pass rate** against the threshold.

Then do the part that matters: for every query that came out wrong, quote it, say which
skill fired instead, and decide between two explanations — the description is missing a
phrasing, or the label is wrong. Both happen, and a mislabelled query silently caps the
score forever. Say which you think it is and why.

If the harness itself fails — the CLI is missing, a call times out — report that and stop.
A run where the tool never answered scores as perfect specificity, and reporting it as a
result would be worse than reporting nothing.

Do not edit the description to raise the score. Say what you would change and let the
author decide.
