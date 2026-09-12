# Flag hygiene

Read this when adding flags to a codebase that already has a lot of them, or when
auditing an estate that has grown past anyone's memory: how to name and type a flag, what
it must evaluate to when the flag service is unreachable, the audit that finds the stale
ones, the removal pull request, and how kill switches differ in storage and testing.

## Contents

- Naming and typing
- Default values and failure modes
- Evaluating flags without making every call a network call
- The stale-flag audit
- The removal pull request
- Kill switches
- Metrics that keep the estate honest

## Naming and typing

A flag's name should say what it controls, who owns it and when it dies without anyone
opening a registry.

```text
<type>.<team>.<subject>            release.checkout.new-tax-engine
                                   ops.platform.disable-recommendations
                                   exp.growth.onboarding-checklist-v2
```

Register four fields with every flag at creation, in code next to the definition or in
the flag service, whichever the team will actually keep current:

| Field | Why |
| --- | --- |
| `type` | Release, experiment, operational or entitlement — it determines the expected lifetime |
| `owner` | A team, not a person; people change teams and the flag outlives them |
| `created` | The age is the single best predictor of whether a flag is still needed |
| `remove_by` | A date. Without one the flag has no end state and will not get one later |

Entitlement flags — plan tiers, per-customer feature access — are not release flags. They
are permanent business logic and belong in the authorisation or plan model, where they
can be tested, audited and priced. Leaving them in the flag system inflates the estate
and hides the flags that genuinely need removing.

## Default values and failure modes

Every flag evaluation must produce an answer when the flag service is unreachable, and
that answer has to be the safe behaviour.

- **Release flags default off**, to the previously shipped behaviour. The new path is the
  one with less production exposure.
- **Kill switches default to the state that keeps the system up.** Think about this one
  carefully: if the switch means "disable the recommendation service", the safe default
  during a flag-service outage is usually the normal state (enabled), because defaulting
  every switch to its emergency position during an unrelated outage degrades the whole
  product at once.
- **Cache the last known value locally**, with a bounded staleness, so a flag-service
  blip does not stampede every service back to defaults simultaneously. The stampede is
  worse than the outage that caused it.
- **Test the unreachable path.** Block the flag service in a staging environment and
  confirm the system serves. This takes an afternoon and is the difference between a flag
  system that reduces risk and one that adds a new single point of failure.

## Evaluating flags without making every call a network call

Flag evaluation on a hot path must be local. The usual shape is an SDK that maintains a
streamed or polled local ruleset and evaluates in-process, so an evaluation is a hash and
a comparison rather than an HTTP request.

Evaluate once per request, as early as possible, and carry the decision. Re-evaluating
the same flag in five services during one request risks five different answers if a ramp
lands mid-request, and produces a state that is inconsistent inside a single user action.

Emit an exposure event (which subject saw which variant, when) if the flag drives an
experiment. Without exposure data, the experiment measures the population you intended
rather than the one that actually saw the change.

## The stale-flag audit

Run it quarterly at minimum. What to gather:

```bash
# Flags in code, by definition site.
grep -rEn 'flags\.(isEnabled|variation|bool)\("[^"]+"' --include='*.go' --include='*.ts' src/ \
  | sed -E 's/.*\("([^"]+)".*/\1/' | sort | uniq -c | sort -rn

# Age of each definition, which is the strongest staleness signal.
git log -1 --format='%ad %h' --date=short -S'release.checkout.new-tax-engine' -- src/
```

Cross-reference three lists, and the gaps between them are the findings:

1. Flags defined in code.
2. Flags configured in the flag service.
3. Flags evaluated in the last 30 days, from the service's evaluation telemetry.

| Gap | Meaning | Action |
| --- | --- | --- |
| In code, not in the service | Evaluates to its default forever | Remove the branch, keep the default behaviour |
| In the service, not in code | Orphaned configuration | Delete the configuration |
| Evaluated, but 100% one way for 30+ days | The rollout finished and nobody closed it out | Remove, this is the bulk of the estate |
| Past `remove_by`, still ramping | The rollout stalled | Ask the owner: finish it or revert it. A stalled rollout is a decision nobody made |
| Never evaluated | Dead code, or a flag whose code path is unreachable | Remove, and check why the path is unreachable |

Report the estate as two numbers the team will recognise: total flags, and median age of
a release flag. A median release-flag age above a few weeks means the removal step is not
happening, and no amount of individual diligence will fix that — the fix is making
removal part of the rollout's definition of done.

## The removal pull request

Removing a flag is a code change with its own risk, because it deletes a branch that is
currently doing something.

1. Confirm the flag has been at 100% (or 0%) for a full bake period, from the service's
   telemetry rather than from memory.
2. Delete the losing branch and the flag check in the same commit. Leaving the check with
   a hardcoded `true` is not removal; it is the same branch with worse documentation.
3. Delete the tests for the losing path, and check that the remaining tests still cover
   the winning path — a surprising number of tests exercise only the old branch.
4. Remove the flag from the flag service after the code is deployed, not before. Removing
   configuration first sends every running instance to its default, which for a release
   flag at 100% is a silent full rollback.
5. Reference the rollout in the pull request body, so the history connects the removal to
   the change it completed.

## Kill switches

Different requirements from release flags, and worth storing differently.

- **Storage independent of the system it protects.** A switch that disables the
  recommendation service cannot live behind that service, and one that sheds database
  load cannot be read from that database. Separate control plane, aggressively cached on
  each host.
- **Propagation delay measured, not assumed.** Pull the switch in a low ring and time how
  long until the last instance honours it. On-call needs that number to decide whether
  the switch is a mitigation or a distraction.
- **A short list, in the runbook.** Name, what it disables, what users see when it is
  pulled, propagation delay, owner. On-call finds it in seconds or does not use it.
- **Exercised on a schedule.** A game day is the natural place: pull each switch, confirm
  the degraded behaviour matches the documented blast radius, restore. A switch that has
  never been pulled is documentation, not capability.
- **Alarm when one is left pulled.** A kill switch pulled during an incident and never
  restored is a permanently degraded product that nobody is looking at. Alert on any
  operational flag in its non-default state for longer than a stated period.

## Metrics that keep the estate honest

Four numbers, reviewed with the team rather than filed:

- Total flags, split by type.
- Median and maximum age of release flags.
- Count past `remove_by`, and the owning teams.
- Kill switches not exercised in the last two quarters.

Reviewing them takes five minutes and is the only thing that reliably prevents the slow
accumulation described in the main procedure. Individual discipline does not survive a
busy quarter; a number on a recurring agenda does.
