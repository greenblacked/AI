---
description: Run a claim a change rests on through the verification loop, where investigator settles it against primary sources and labels what it could not verify, and reviewer judges whether the finding supports the change.
argument-hint: the claim to check, for example "kubectl drain --force skips the grace period"
agent: agent
---
<!-- source: .claude/commands/verify.md sha256: 814686b7b608c9087eece0cf2197b57748ecc8c8c2bc83722ad9b6fafe7ea942 -->

Check this claim: ${input:claim:the claim to check}

Run the two stages in order, and do not collapse them. The second exists because the first is the
wrong context, and in this loop the wrong kind of evidence, to do that work in. The stages use the
custom agents `investigator` and `reviewer` (`.github/agents/`); without custom agents, run each in
its own fresh chat with that agent's file as the instructions.

## Handoff protocol

Each stage passes forward the previous stage's `Handoff` section, not a paraphrase of the whole
report. `investigator` receives the claim and what it rests on as a short brief, the way
`implementer` does in the `ship` prompt (`.github/prompts/ship.prompt.md`). Settle both in this
conversation before delegating.

From `investigator`: `DOES NOT HOLD`, `NARROWER` or `UNVERIFIED` means the change needs editing:
take the finding to the files or to `implementer` rather than investigating again, then go to stage
2 with the edit. `HOLDS` goes to stage 2 directly. `UNVERIFIED` is a real result: report it as
such, do not retry it. From `reviewer`: `FIX` returns the named findings to the files or to
`implementer`; `STOP` comes to the person for a decision; `SHIP` ends the loop. There is no round
limit, but the same finding recurring means the edit fixed a symptom rather than the premise: stop
and address that before a third try. A report with no `Verdict:` line is a question, and comes back
to this conversation.

## 1. Decide, then investigate

Pick the claim that matters yourself. A change usually rests on several checkable things and only
one holds it up; which one depends on what the change argues, and that travels badly through a
cold prompt.

Then delegate to `investigator` with one claim and what rests on it. It finds the source and reads
it, prefers refuting to confirming, labels each finding primary, consensus or inference, and
reports what it could not verify. Send one claim. Three gets you a finding about none of them.

## 2. Judge

Delegate to `reviewer` on the change with the finding attached. The question is no longer whether
the claim is true, because `investigator` settled that. It is whether the change is now consistent
with what was found: whether the sentence that cited the claim says something the evidence
supports, whether the paragraph built on it still stands once the premise narrowed, and whether a
figure softened to "roughly a third" is still doing the work the precise number was doing.

That cannot be folded back into stage one. An agent that has just spent its context establishing a
fact is the worst-placed reader of the prose around it. `reviewer` arrives cold, with the contract
in `AGENTS.md` and no stake in the finding.

## Finish

Report: the claim as checked, the verdict with its label, what could not be verified, and the
specific edit the finding implies. Quote the evidence rather than summarising it, because a summary
of a source is a new claim and starts the loop again.

If the verdict is unverified, say so plainly rather than as a hedge attached to a claim you are
keeping. An unverified number is worse than no number.

Do not commit and do not push. The loop ends with a finding and a recommended edit; what to do with
it is the person's call.

Full prompt: `.claude/commands/verify.md`.
