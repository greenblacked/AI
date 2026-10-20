# The decision record

Read this at step 9, once the canary has finished or the migration has been abandoned. It
is short on purpose: the record exists so the next migration, or the next person asking
why the feature behaves differently, can read what was decided and what was accepted
without reconstructing it from chat.

Keep it beside the feature (a `docs/decisions/` entry, the pull request description, or
the ticket), not in a message that will scroll away.

## Template

```markdown
# Move <feature> from <old model id> to <new model id>

Date: <date of decision>    Owner: <named person>
Reason: <deprecation | cost | quality>, and the date or number that forced it
Retirement date of the old id: <date from the provider page, with the link>
Cutover date: <date>    Old id removed from config on: <date>

## What changed
- Request changes required by the provider (from the behaviour list): ...
- Prompt changes, each with the case or hypothesis that motivated it: ...
- Settings tuned against the eval set (effort, max tokens, thinking): ...

## Evidence
- Eval set: <name and revision>, <n> cases, <k> repeats, baseline run <date>, candidate run <date>
- Baseline noise (cases that disagreed with themselves): ...
- Regressed cases and what was done about each: ...
- Improved cases: ...
- Cost per request, old and new, from usage fields over the replay set: ...
- Latency p50 and p95, old and new: ...
- Cache: hit behaviour old and new, and any prompt that fell below the cacheable minimum: ...

## Rollout
- Shadow period and what it covered: ...
- Canary steps, the rollback trigger (signal, threshold, window) and whether it fired: ...
- Rollback tested on: <date>

## Accepted risks
- <Behaviour change with no covering case, or a regression accepted, and who accepted it>

## Follow-ups
- <Remove old model id and request profile by <date>>
- <Re-calibrate the judge if it ran on the old model>
```

Leave no field blank. "Not applicable" with a reason is an answer; an empty field is a
question the next reader has to ask.
