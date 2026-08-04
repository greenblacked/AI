# Writing a subagent

Subagents live in the `agents/` directory as single Markdown files with YAML
frontmatter — see [`skill-reviewer.md`](../agents/skill-reviewer.md) for the one this
repository has today. A subagent is a separate Claude instance with its own context window,
its own system prompt, and its own tool allowlist, invoked by the main agent and
returning a result to it.

## Frontmatter

```yaml
---
name: skill-reviewer
description: Review a candidate SKILL.md against this repository's rules and against what actually makes a skill trigger and work. Use when a new skill has been drafted, when an existing one is being edited, or when a skill exists but never seems to fire.
tools: Read, Glob, Grep, Bash
---
```

- **`name`** — the identifier the main agent delegates to, and the filename stem.
- **`description`** — the only text the main agent sees when deciding whether to
  delegate. Same economics as a skill description: if it does not name the situations,
  the subagent never runs.
- **`tools`** — a comma-separated allowlist. Omit it and the subagent inherits the main
  agent's full tool set, which is almost never what you want.

Note that this key is `tools`, not the `allowed-tools` used in skill frontmatter. They
are different formats; [the skill validator](../src/skillcheck/rules.py) does not run
over `agents/`.

The body is the system prompt. Write it as instructions to a colleague who has just
walked in: it starts with no memory of the conversation that produced the delegation.

## When a subagent is the right tool

The honest discriminator is not "is this a distinct task". Skills also carve out distinct
tasks, and a skill is cheaper — no round trip, no re-derivation, no summarisation loss.
Two things a skill genuinely cannot do:

**Context isolation.** A subagent's context is discarded when it returns. That matters
when the work would otherwise flood the main context with material nobody needs
afterwards: a megabyte of CI logs, a large Terraform plan JSON, a hundred files grepped
to answer one question. The main agent gets the conclusion; the raw material never enters
its window. If the work produces a small amount of reading, do it inline.

**Tool restriction.** A subagent can be denied capabilities the main agent has. This is
the reason `skill-reviewer` has no `Write` or `Edit`: a reviewer that can write will
eventually "helpfully" fix the thing it was asked to assess, and you lose the assessment.
The restriction is what makes the review a review.

If neither applies, write a skill. See [writing a skill](writing-skills.md).

## Single responsibility

A subagent should do one thing and be describable in one sentence. A general-purpose
subagent is worse than no subagent, for a reason specific to how delegation works: the
main agent chooses by reading descriptions, and a description broad enough to cover
everything matches nothing in particular. It either fires constantly — paying the round
trip and the summarisation loss on work that should have been inline — or the main agent
cannot tell when it applies and it never fires at all.

Concretely: "reviews things" is not a subagent. "Reads a failed CI run and returns the
failing step with the decisive log lines" is.

## Restricting tools

Grant the minimum. Work out what the subagent must read, must search, and must execute,
and grant exactly those.

- A reviewer or analyst gets `Read`, `Glob`, `Grep`, and `Bash` only if it needs to run a
  checker. No `Write`, no `Edit`.
- A log reader needs `Bash` (for `gh`) and `Read`. It does not need `Edit`.
- Anything that summarises rather than changes should be unable to change anything.

This is not defence against a malicious model; it is defence against a helpful one.
Capability that is present will eventually be used, and a subagent that quietly fixed
what it was asked to evaluate has destroyed the evidence you delegated for.

## Writing the description so delegation happens

Same failure mode as skills: descriptions written for someone who already knows what the
subagent does. Write the triggering circumstance.

`skill-reviewer`'s description names three: a new skill has been drafted, an existing one
is being edited, and — the useful one — a skill exists but never seems to fire. That
third clause is what makes it get invoked in the case where the user does not know they
want a review.

State the boundary too. A subagent that plausibly matches the same request as another
one means neither is chosen reliably.

## What a subagent should return

A conclusion and its evidence. Not a transcript.

The whole economic argument for a subagent is that the caller does not have to read what
the subagent read. Returning the raw material, or a narration of the steps taken, gives
back the cost you delegated to avoid. The shape that works:

1. The verdict, first, in one or two sentences.
2. The evidence that decided it — the specific log lines, the specific finding, quoted.
3. What to do about it, concretely.
4. What was **not** assessed. A result that implies coverage it did not have is worse
   than a short one that says where it stopped.

`skill-reviewer` encodes this: rank findings by what they cost, give each an observation,
a concrete consequence and the smallest fix, separate blocking defects from
improvements, and say explicitly which parts were not assessed.

## Failure modes

**Re-deriving context the caller already had.** The subagent starts cold, so it explores
to rebuild state the main agent could have handed it in two sentences. Fix it in the
prompt: state what the caller will provide and instruct the subagent to use it rather
than rediscover it. `skill-reviewer` does this by starting with the validator run and
explicitly telling itself not to re-derive mechanical findings it can get from one
command.

**Output the caller has to read in full.** If the return value needs the same attention
the raw material would have needed, the isolation bought nothing. Cap it: a conclusion, a
handful of evidence lines, an action.

**Fan-out with no synthesis step.** Launching five subagents and pasting five reports
into the context is a slower way to have read everything yourself. Parallel delegation
needs a step that reconciles the results — resolves disagreement, deduplicates, and
produces one answer. If nobody is going to do that reconciliation, launch one subagent,
not five.

**Delegating work that needed the conversation.** Anything depending on judgement built
up over the session travels badly through a description and a cold prompt. Keep it
inline.

## The subagents in this repository

The `engineering` plugin in
[`marketplace.json`](../.claude-plugin/marketplace.json) declares four:

- **`skill-reviewer`** — reviews a candidate `SKILL.md` against this repository's rules
  and against what makes a skill actually trigger. Runs the validator first to settle
  every mechanical question, then reviews what the validator cannot see: whether the
  description carries the whole trigger, whether the body assumes context the model will
  not have, whether depth is in the right layer, whether it is a procedure or an essay,
  whether it overlaps an existing skill, and whether the commands it shows are real. It
  has `Read`, `Glob`, `Grep` and `Bash`, and no write access — by design:
  [`agents/skill-reviewer.md`](../agents/skill-reviewer.md).
- **[`ci-log-reader`](../agents/ci-log-reader.md)** — reads a failed pipeline run and
  returns a classification. This is the canonical context-isolation case: whole CI logs
  are large, and the caller needs the failing step and the decisive lines, not the log.
  It checks the default branch first, because if that is red too the answer is "not
  this change" and nothing further needs reading.
- **[`plan-reviewer`](../agents/plan-reviewer.md)** — reads a Terraform plan JSON and
  returns the blast radius, destroys first. Same shape: the plan is large, the answer is
  a short list of risky changes, and a reviewer that can apply is not a reviewer.
- **[`incident-scribe`](../agents/incident-scribe.md)** — turns raw triage notes into a
  blameless postmortem draft: timeline from timestamped evidence, roles rather than
  names, and a literal `[TK: metric]` wherever a figure was not supplied.

All four files exist and all four are listed in the `engineering` plugin's `agents`
array. Worth knowing: the validator's manifest cross-check covers `skills` entries, not
`agents` entries, so a subagent listed in the manifest but missing from disk would not
fail [CI](ci.md). Check that by reading.
