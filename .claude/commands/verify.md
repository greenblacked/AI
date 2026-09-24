---
description: Run a claim a change rests on through the verification loop — investigator settles it against primary sources and labels what it could not verify, reviewer judges whether the finding supports the change.
argument-hint: '[the claim to check, for example "kubectl drain --force skips the grace period"]'
allowed-tools: Agent(investigator), Agent(reviewer), Read, Grep, Glob, Bash(make:*), Bash(git status:*), Bash(git diff:*)
---

Check this claim: $ARGUMENTS

Run the two stages in order, and do not collapse them. The second exists because the
first is the wrong context — and in this loop, the wrong kind of evidence — to do that
work in.

## 1. Decide, then investigate

Pick the claim that matters yourself. A change usually rests on several checkable things
and only one of them holds it up; which one that is depends on what the change argues,
which lives in this conversation and travels badly through a cold prompt. This is the
same split [`/ship`](ship.md) makes when it keeps the shape of a change out of
`implementer`.

Then delegate to `investigator` with one claim and what rests on it. It finds the source
and reads it, prefers refuting to confirming, labels each finding primary, consensus or
inference, and reports what it could not verify.

Send one claim. Three gets you a finding about none of them.

If it comes back "does not hold" or "unverified", the change needs editing, not a second
investigation. Take the finding to the files — or to `implementer` — rather than asking
another agent for another opinion, which is how a refuted claim gets confirmed on the
third attempt.

## 2. Judge

Delegate to `reviewer` on the change with the finding attached. The question here is no
longer whether the claim is true, because `investigator` settled that. It is whether the
change is now consistent with what was found: whether the sentence that cited the claim
says something the evidence actually supports, whether the paragraph built on it still
stands once the premise narrowed, whether a figure softened to "roughly a third" is still
doing the work the precise number was doing.

That cannot be folded back into stage two. An agent that has just spent its context
establishing a fact is the worst-placed reader of the prose around it, because it knows
what the sentence was meant to say and reads that in. `reviewer` arrives cold, with the
contract in `AGENTS.md` and no stake in the finding.

## Finish

Report to the user: the claim as checked, the verdict with its label, what could not be
verified, and the specific edit the finding implies. Quote the evidence rather than
summarising it — a summary of a source is a new claim, and it starts the loop again.

If the verdict is unverified, say so plainly rather than as a hedge attached to a claim
you are keeping. An unverified number is worse than no number, because the figure carries
an authority its provenance does not.

Do not commit and do not push. The loop ends with a finding and a recommended edit; what
to do with it is the user's call.
