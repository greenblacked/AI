# Model and prompt lifecycle

Read this at step 3, before a model or prompt change goes anywhere near production: why
a moving alias invalidates the evaluation that passed it, how to track a pinned
snapshot's retirement, what to monitor once a version is live, and the order the
surrounding work happens in.

## Contents

- [An alias is not a version](#an-alias-is-not-a-version)
- [The retirement calendar](#the-retirement-calendar)
- [Production drift signals](#production-drift-signals)
- [The coordination checklist](#the-coordination-checklist)

## An alias is not a version

A model alias — a name a vendor points at whichever dated snapshot is current — can move
to a different underlying model with no deploy on your side and no entry in your own
changelog. An evaluation run against an alias is a claim about whatever the alias
resolved to on the day the run happened. If the alias moves before the change ships, the
evaluated behaviour and the shipped behaviour belong to two different models wearing the
same name in your report, and nothing about your own release process will show you that
this happened.

The fix is the same discipline step 3 already asks for every other run input: pin a
dated model snapshot identifier in the task contract, the same way you pin a dependency
image or a tool definition version. Pair every prompt revision with the exact model
identifier it was tuned and evaluated against, and treat a change to either one — the
prompt or the pinned model — as the same release, gated the same way.

## The retirement calendar

A vendor that retires a pinned snapshot announces it on its own schedule, not yours.
Track every pinned snapshot's retirement date on a calendar with a named owner, the same
way `certificate-automation` tracks a certificate's expiry — a retirement date announced
months ahead and left untracked is a self-inflicted outage on a date nobody put on a
calendar.

When a retirement date arrives with no replacement already evaluated, fail closed to a
flagged-off feature or the previous evaluated snapshot, never to whatever the alias is
currently resolving to. Falling back to an alias at the exact moment a pinned version
disappears reintroduces the same problem this file opened with, at the worst possible
time to discover it.

## Production drift signals

A model or prompt version that passed its offline evaluation can still drift once it is
live, because production traffic is broader than any dataset. Track these per
model-and-prompt version, not only in aggregate:

| Signal | What it indicates |
| --- | --- |
| Refusal rate | The model is declining a growing share of requests it used to complete |
| Schema-violation rate | Structured-output failures against your own validator, not the vendor's |
| Output-length distribution | A shift here often precedes a cost or latency regression before either shows up on its own dashboard |
| User-edit and retry rate | Users are correcting or re-running the model's output more than the baseline |
| Sampled judge score | A rubric-scored sample of live traffic, using the same calibrated judge from step 6, run on a schedule rather than only at release |

Read `instrumentation` for how to actually emit each of these as a metric, and
`alert-design` for what should page on it — this file names the signals worth watching;
it does not restate either skill's own procedure for wiring them up.

## The coordination checklist

A model-or-prompt swap is one release, not three independent changes made by three
different people on three different days:

1. **Offline evaluation** — this skill's own workflow, gated the way any other candidate
   is.
2. **Cost and token delta** — hand it to `llm-cost`; a new tokenizer can move the bill
   without changing a single word of the prompt, which is exactly the kind of change an
   evaluation focused on task success will not catch on its own.
3. **Rollout** — gate the swap itself through `release-strategy`'s canary or ring
   mechanism rather than an instant cutover, even when the evaluation passed cleanly.
4. **Retirement-calendar update** — record the new pinned snapshot's own retirement date
   the moment it goes live, not after the old one has already been retired.

Each step hands off to the skill that owns it rather than restating its procedure here.
