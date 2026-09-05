---
description: Draft an on-call handover from what actually happened — pages, deploys, open incidents and anything left mid-flight — so the next person starts informed rather than surprised.
argument-hint: [since, default the start of the shift]
allowed-tools: Bash(gh:*), Bash(git:*), Bash(kubectl:*), Read, Grep
---

Draft the handover for the shift starting at `$1`, defaulting to the last seven days if
nothing was given.

Gather what happened rather than what you remember. Memory at the end of a shift is worst
exactly where the handover matters most:

```bash
gh issue list --label incident --state all --search "updated:>=$1" --json number,title,state,updatedAt
gh run list --workflow=deploy.yml --created=">=$1" --json conclusion,displayTitle,createdAt
git log --since="$1" --no-merges --format='%h %s' --all
```

Then write it under these headings, and keep it short enough to be read in the two minutes
it will actually get:

- **Still open.** Anything unresolved, with its current state, what has been tried, and
  the next thing you would do. This is the only section that is genuinely urgent, so it
  goes first.
- **Fixed but fragile.** Mitigations still in place — a scaled-up replica count, a
  disabled feature flag, a paused job, a manual workaround. Each with what has to happen
  to undo it and who knows about it. This is the section people skip and then rediscover
  at 4am, since a temporary mitigation nobody wrote down becomes permanent by accident.
- **Noise.** Alerts that fired and needed no action, named specifically. Two shifts
  reporting the same noisy alert is the evidence that gets it fixed — hand off to the
  `alert-design` skill for the pruning.
- **Changes landing.** Deploys and migrations in flight or scheduled during the incoming
  shift, and who owns each.
- **Nothing happened.** Say so plainly if that is true. A handover padded to look
  substantial teaches people to skim the ones that matter.

Where an incident is still open, link the runbook rather than restating it, and say
explicitly if no runbook exists — that absence is itself the handover's most useful line.
