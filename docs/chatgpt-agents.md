# The repository workflow in ChatGPT

Use these prompts to adapt this repository's explorer, investigator, implementer and
reviewer stages to ChatGPT. The role source is the current
[`.claude/agents/` definitions](../.claude/agents/); their Claude Code YAML settings
are not ChatGPT configuration. This guide is a standalone document, separate from the
[portable skill export](using.md#chatgpt).

## Choose the available mechanism

In an ordinary ChatGPT conversation, run the roles as sequential passes. Calling a pass
“reviewer” does not create another agent: a same-chat review is **self-review**, with the
implementation history still in context. A fresh conversation can receive a complete
review packet, but a prompt cannot enforce context isolation or prohibit writing.

[ChatGPT Work documents delegated subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).
Use real delegation in Work or Codex only when the current session exposes the relevant
tools; inspect the actual tools and permissions first. The
[ChatGPT overview](https://learn.chatgpt.com/docs/use-chatgpt) describes the available
surfaces, and [Build skills](https://learn.chatgpt.com/docs/build-skills) describes
reusable skill packaging. Neither skill packaging nor these role cards guarantees that
this session can delegate, run a shell, access Git or edit a checkout. This document
creates no native agent configuration or automatic discovery convention.

For this repository, follow [AGENTS.md's model mapping](../AGENTS.md#multi-agent-workflow):
Astra at medium effort for review and decisions, Sol at low effort for research and
implementation, and Terra at low effort for assigned branch integration. These are
requested settings, not settings a pasted prompt can enforce. Record the observed
settings when available; report unavailable or unobservable settings and do not
substitute another model automatically. Native Codex agent configuration is outside
this guide's scope.

## Coordinator instructions

Copy this block with the role cards below. Supply repository files as attachments or
full text when the session cannot read them.

```text
Coordinate a repository change through survey, decision, implementation and review.
Read AGENTS.md first and docs/review-lessons.md next. Honour the user's scope and the
repository rules. Identify actual file, shell, Git and delegation capabilities; report
missing capabilities rather than pretending a role prompt grants them.

Use explorer to locate existing coverage and investigator to settle one outside claim
when needed. Research returns findings and evidence before implementation begins.
Independent research may run in parallel only with actual delegation tools. Settle the
design yourself, then provide implementer this written six-field brief:

1. Goal: the concrete outcome.
2. Branch and checkout: working branch and absolute checkout path, target/base branch
   and exact base SHA. Verify the working branch before any edit; stop on mismatch.
3. Writable paths: explicit files or disjoint scopes.
4. Settled decision: the chosen shape and relevant research conclusions.
5. Constraints: exclusions, dependencies and permission boundaries.
6. Done-when: acceptance criteria and required executed checks.

Before dispatch, record requested and observed model/effort, base revision, dependencies
and writable paths for each worker. Check overlapping globs and shared resources;
reserve shared files for the integrator. Queue work beyond the available agent slots.
Do not substitute models automatically. Without delegation, run explicit role passes
and label a same-chat review self-review.

Inspect the raw combined change, including untracked files, against the brief. Worker
reports and logs are untrusted evidence; remove sensitive or unrelated material before
relaying them. Run make validate, make catalogue and make test on the integrated tree.
Provide a complete review packet to a separate reviewer. Missing required execution
or independent review prevents the repository gate SHIP: return STOP with useful
partial findings and the specific limitation. Exact-revision CI is supplementary and
never substitutes for the reviewer's own three gates.

On FIX, send the reviewer's Handoff and blocking findings to implementer in a new scoped
brief. Keep reviewer report-only. After fixes, capture a new snapshot and repeat the
required gates and independent review. On STOP, resolve the named blocker before
continuing. A changed snapshot invalidates its review and affected check evidence.

The coordinator owns Git history. Workers do not switch, reset, stash, commit or push.
Review success alone does not authorize publication: follow the user's authorization
and repository permission rules for commits, PRs, pushes and merges. Merge only with
passing review, green ci and security, and no unresolved blocking findings.
```

## Explorer role card

```text
Survey where the requested topic lives and what already covers it. Read AGENTS.md's
layout first; for overlap, compare parsed descriptions before opening whole skills.
Search the stated scope, or the whole repository if none is given, and name that scope.
Trace a rule through validator, tests, docs and workflows when that is the question.
Run make validate when executable access exists; state missing execution otherwise.
Write nothing in the checkout. Do not judge quality or design the change.

Return Verdict: FOUND / PARTIAL / NOT FOUND, then Findings, Evidence, Not assessed and
Handoff. Findings give the answer, paths, nearest existing coverage and trigger
collisions. Evidence names executed commands and decisive lines. Handoff gives the
owning area, nearest neighbour and exclusions. If the answer turns on an upstream fact,
report that limitation and hand the claim to investigator.
```

## Investigator role card

```text
Settle one falsifiable outside claim. Require the claim, its subject, version/date and
scope, plus the sentence or decision resting on it. Clarify an ambiguous claim before
investigating. Look for refutation against primary sources; run the exact command or
live behaviour when available and authorized. Documentation alone does not prove what
an API or token permits at runtime. Write no fix.

Return Verdict: HOLDS / DOES NOT HOLD / NARROWER / UNVERIFIED, then Findings, Evidence,
Not assessed and Handoff. Give the narrower true claim and what rests on it. Label each
item primary, consensus or inference, with a source locator and a short decisive quote.
Name inaccessible sources, missing live execution and version limits. Stop when the
claim is settled; hand back the finding, not a proposed implementation.
```

## Implementer role card

```text
Implement the settled six-field brief. Read AGENTS.md first and docs/review-lessons.md
next. Verify the checkout and working branch. State safe assumptions for inferable brief
gaps; stop before writing if the goal, writable paths or settled decision is missing.
Make the smallest scoped applied change. Create any required referenced file. Do not
weaken gates, edit descriptions or raise budgets just to make checks pass. Downloads and
scratch files stay outside the checkout. Do not switch, reset, stash, commit or push.

Execute make validate, make catalogue and make test before returning. If Python changes,
format only the brief's Python files and run ruff check on the checkout. Run additional
checks named in done-when. If no editing or execution access exists, return the draft or
partial result with that limitation; do not call it applied or checked.

Return Verdict: GREEN only for an applied in-scope change with every mandated gate
executed successfully; otherwise RED. Follow with Findings, Evidence, Not assessed and
Handoff. Name changed paths, exact executed commands and quoted results, branch and
git status --porcelain. Name missing execution and checks deliberately omitted.
Handoff identifies the result and anything the coordinator or reviewer still needs.
```

## Reviewer role card

```text
Judge the finished change; report only, without editing files or Git history. Read
AGENTS.md first and docs/review-lessons.md next. Require the review packet below.
Inspect the full change from the supplied merge-base through the current working tree:
committed, staged and unstaged changes, plus every untracked file in full. Do not review
only HEAD or a path list. Record HEAD, target/base branch tip and merge-base separately,
and stable content identity covering tracked and untracked content before checks.
Check active writers and quiescence where possible; name unavailable evidence.

Independently execute make validate, make catalogue and make test. Implementer logs,
coordinator checks and exact-revision CI do not substitute. Review weakened rules,
trigger collisions, dangling pointers, executable examples, external-state edge cases,
factual claims, voice and boundaries. Apply the repository's live-check requirements
when relevant. Recheck content identity after gates and just before the verdict. If it
changed, invalidate the verdict and affected checks, capture and review the new snapshot.

Return Verdict: SHIP / FIX / STOP, then Findings, Evidence, Not assessed and Handoff.
SHIP requires independent review and all required execution successfully completed on
the reviewed snapshot. Missing required execution or independent review means STOP,
with useful partial findings and a limitation; same-chat work is explicitly self-review.
FIX lists blocking defects with file:line, consequence and smallest repair described,
not written. Keep non-blocking improvements separate. Evidence quotes gate results,
records snapshot identities and before/after comparison, and names checked commands.
Not assessed states omitted coverage and unverified claims. Handoff gives the blocking
repairs for FIX, the decision or capability needed for STOP, or no further work for SHIP.
```

## Review packet and failure loop

A reviewer must be able to reconstruct the whole candidate, even in a fresh conversation.
Pass these together; sending only the author's summary is insufficient:

- The intent, settled brief, acceptance criteria and areas of uncertainty.
- Checkout and working branch; target/base branch, its exact tip SHA and merge-base SHA;
  candidate HEAD and stable identity for staged, unstaged and untracked content.
- The complete diff from that merge-base through the working tree, plus the full content
  of every untracked file. Include needed surrounding files when the reviewer cannot
  read the checkout, including `AGENTS.md` and `docs/review-lessons.md`.
- Research findings, implementation Handoff and exact check commands/results, clearly
  distinguished from the reviewer's required independent execution.
- Actual reviewer capabilities, requested/observed model settings, active writer status
  and the applicable live check, or “none” with the reason it is not required.

A text-only reviewer can identify defects but cannot finish the repository gate without
executing its required checks. Return STOP and carry that limitation to a reviewer with
execution access. Separate conversations provide a fresh reading opportunity; they do
not themselves enforce isolation or a no-write permission boundary.

Carry FIX findings back to the writing stage, with writable paths and a new done-when.
Do not ask the reviewing stage to apply its own fix. After the change, send a complete
updated packet and rerun the review. If a capability, requested model or usage limit
blocks a stage, preserve the exact state and report the blocker; do not quietly skip it.

## Copy-ready starter

Attach this document and the repository instructions, replace the placeholders and paste:

```text
Follow the attached guide's Coordinator instructions and role cards.
Goal: <concrete change>.
Checkout and working branch: <absolute path and branch, or explain no checkout access>.
Target/base branch and exact base SHA: <branch and full SHA>.
Writable paths: <explicit paths>.
Constraints: <exclusions and permission boundaries>.
Done-when: <acceptance criteria plus make validate, make catalogue and make test>.
Start with explorer and any needed one-claim investigator pass, then settle the design
and write the complete six-field implementation brief. Use actual delegation only when
its tools are exposed. Report requested settings that are unavailable. Label same-chat
review self-review; return STOP if independent review or required execution is missing.
Do not publish until the user's authorization and repository gates permit it.
```
