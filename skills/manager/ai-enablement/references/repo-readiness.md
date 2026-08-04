# Repository readiness for agent-assisted work

## Contents

- [The premise](#the-premise)
- [AGENTS.md outline](#agentsmd-outline)
- [Readiness checklist](#readiness-checklist)
- [Common blockers](#common-blockers)
- [Diagnosing "it does not work in our codebase"](#diagnosing-it-does-not-work-in-our-codebase)
- [Sequencing the work](#sequencing-the-work)

## The premise

An agent has the same requirements as a competent new joiner with no tribal
knowledge and no colleague to ask: it must be able to set the project up, run the
tests, understand the conventions that are actually enforced, and verify its own
change. Where a repository depends on knowledge that lives only in people, the
agent fails — visibly and repeatedly, which is why the complaint surfaces as "AI
does not work here" rather than as an onboarding finding.

The useful consequence is that this work is not AI-specific. Every item below
shortens human onboarding too, which makes it the easiest part of an enablement
programme to fund and the part that retains value if the programme stops.

## AGENTS.md outline

One file at the repository root. Written for someone with no context, kept next to
the code, and updated when the commands change — a stale `AGENTS.md` is worse than
none, because it is followed.

```markdown
# AGENTS.md

## What this is
[One paragraph: what the service or library does, who consumes it, what it talks
to. Enough to judge whether a proposed change is in scope.]

## Setup
[Exact commands, in order, from a clean clone. Required runtimes with versions.
Which secrets or env vars are needed and where they come from — the mechanism,
never the values. What can be stubbed for local work.]

## Running the tests
[The single command for the full suite. The fast subset and its command. How to
run one test. Expected runtime for each, so a long run is not read as a hang.]

## Verifying a change
[Lint, type check, format, build. The exact commands CI runs, so a local pass
means a CI pass.]

## Conventions
[Only what is actually enforced. Error handling, logging, module layout,
migration process, dependency policy. Anything aspirational belongs elsewhere —
listing unenforced conventions here trains the reader to ignore the section.]

## Do not touch
[Generated files, vendored code, anything with an external contract, anything
under active migration. Say why for each; a reason is followable, a prohibition
is guessed around.]

## Where things are
[The map: entry points, domain logic, config, tests, deployment. Two or three
lines saves a broad and expensive search.]

## Gotchas
[The things a new joiner is told verbally in week one. This section is usually
the highest-value part of the file and the one that gets written last.]
```

## Readiness checklist

Assess per repository. Each item is a yes or a no; "mostly" is a no.

### Runnable

- [ ] One command installs dependencies from a clean clone
- [ ] One command runs the test suite
- [ ] One command runs lint, type checks and formatting
- [ ] Required runtime versions are pinned and declared
- [ ] Local development needs no credential that only one person can issue
- [ ] External dependencies can be stubbed, mocked or pointed at a sandbox

### Fast

- [ ] A fast test subset completes in roughly two minutes or less
- [ ] The full suite completes in a time a person will actually wait for
- [ ] Test failures name what broke, not just an assertion count
- [ ] The suite is deterministic — no known flaky tests treated as normal

### Documented

- [ ] `AGENTS.md` exists at the root and matches the current commands
- [ ] Conventions listed are the enforced ones
- [ ] Off-limits areas are named with reasons
- [ ] Someone verified the file by following it from a clean clone this quarter

### Gated

- [ ] CI runs the same checks as the documented local commands
- [ ] Required review is enforced by branch protection, not convention
- [ ] An agent's change goes through exactly this gate — no separate path, no
      relaxed threshold, no auto-merge on a lower bar
- [ ] Secret scanning covers the paths agents read and write

## Common blockers

| Blocker | Why it stops an agent | Fix |
| --- | --- | --- |
| Setup requires undocumented manual steps | Cannot reach a working state, so every subsequent action is guesswork | Script the setup; the script becomes the documentation |
| Tests need production credentials | Cannot verify its own change | Stubs, fixtures or a sandbox tier |
| Flaky tests | Cannot distinguish its own breakage from ambient noise; iterates on a phantom | Quarantine and fix; a tolerated flake taxes every change |
| Forty-minute suite | Iteration becomes impractical for agents and unpleasant for humans | Carve out a fast subset on the affected paths |
| Conventions only in reviewers' heads | Produces plausible code that fails review on unstated rules | Write them into `AGENTS.md`; enforce the mechanical ones with a linter |
| Generated files not marked | Edits them, and the edits vanish on the next generation | Mark in `.gitattributes` and name in the do-not-touch section |
| Monorepo with no per-package boundaries | Loads or edits far outside the task | Per-package `AGENTS.md` and clear ownership boundaries |
| No error messages, only exit codes | Cannot self-correct; retries the same failure | Make failures say what failed and what would fix it |

## Diagnosing "it does not work in our codebase"

Work through these in order before accepting the conclusion. In most cases the
finding is repository readiness, not model capability.

1. Can a new joiner set this repository up unaided in under an hour? If not, the
   agent is failing at the same step, for the same reason.
2. Can the tests be run and read without asking anyone? If not, the agent cannot
   verify anything it produces, and every change is unvalidated.
3. Does `AGENTS.md` exist and does following it from a clean clone actually work?
4. Are the conventions the agent violated written down anywhere?
5. Is the feedback loop fast enough to iterate — minutes, not tens of minutes?
6. Is the task actually well-specified? "It got it wrong" frequently means the
   request omitted the constraint that made the obvious answer wrong.
7. Only after all six: is this genuinely beyond the tool? Sometimes it is, and
   that is a legitimate finding — but it is the last hypothesis, not the first.

## Sequencing the work

Do not attempt every repository. Pick the one the pilot team works in daily, make
it genuinely ready, and let the resulting `AGENTS.md` and setup scripts serve as
the template others copy.

Rough order, cheapest and highest-leverage first:

1. `AGENTS.md` with real, verified commands — hours, and it unblocks the rest.
2. Deterministic setup script — a day, and it also fixes onboarding.
3. Fast test subset — days, and it improves every human's inner loop too.
4. Fix or quarantine flaky tests — ongoing, and the most commonly deferred item
   despite being the one that most reliably wastes everyone's time.
5. Align CI with the documented local commands — a day, and it removes the "passes
   locally, fails in CI" class entirely.

Verify by having someone who has never worked in the repository follow
`AGENTS.md` from a clean clone. If they succeed without asking a question, the
repository is ready. That test is cheap, and it is the only one that settles the
question.
