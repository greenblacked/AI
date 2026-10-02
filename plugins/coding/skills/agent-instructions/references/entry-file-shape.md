# The shape of an entry file

Read this when drafting a new instruction file or restructuring one that has grown. It gives a skeleton, says what each section is for, and shows a worked before and after on an invented repository.

## Contents

- [The skeleton](#the-skeleton)
- [What each section is for](#what-each-section-is-for)
- [Writing a rule](#writing-a-rule)
- [Worked example: before](#worked-example-before)
- [Worked example: the evidence](#worked-example-the-evidence)
- [Worked example: after](#worked-example-after)
- [What moved where](#what-moved-where)

## The skeleton

````markdown
# AGENTS.md

One to three sentences: what this is, who uses it, the main technology.

## Layout

| Path | What lives there |
| --- | --- |
| `src/` | ... |
| `generated/` | Output of a generator. Do not edit by hand. |

## Commands

Each line was run from a clean checkout. The working directory is stated if it
is not the root.

- Setup: `...`
- Run: `...`
- Verify a change: `...`
- One test: `...`

## Boundaries

- Do not touch X. Reason. Enforced by: Y.
- Do not touch Z. Reason. Advice: nothing enforces this.

## Where to read next

- `docs/topic.md`: read before doing the thing it covers.

## Unfinished work

Where it lives, and how to leave a half-done change for the next session.
````

## What each section is for

| Section | Purpose | Leave out |
| --- | --- | --- |
| Opening | Answers "what is this" before anything else, so a session can judge whether later lines apply | A history of the project, marketing, a mission statement |
| Layout | Saves the first several tool calls an agent would spend reconstructing the tree, and marks what is generated | A listing of every file; the tree itself is the source of truth |
| Commands | The setup, run, verify and single-test commands that were executed, with the directory and what passing means | Commands nobody ran, alternatives the team does not use |
| Boundaries | What the agent must not touch, with the reason and the enforcer | Style the formatter already enforces |
| Where to read next | One line per topic file saying when to read it, so depth is loaded on demand | A bare list of links with no trigger |
| Unfinished work | Where open work and half-done changes are recorded | An aspiration to have a tracker |

Every one of these sections answers one of the five questions the fresh-session test asks, which is the check on whether a section earns its place. A section that answers none of them belongs in a topic file or nowhere.

## Writing a rule

A rule has a reason and an enforcer, or it says it has neither.

- With both: "Do not edit `generated/`: the next `make gen` overwrites it. Enforced by: CI fails when `make gen-check` finds a diff."
- Advice: "Keep migrations additive so a rollback needs no data fix. Advice: nothing enforces this; review does."

Writing the enforcer is the useful discipline. If you cannot name one, you have found a rule that depends on every future reader remembering it, and the label tells them how much weight to give it. If the enforcer is a linter or a test, the rule itself is usually redundant: say where the config lives and drop the prose.

Delete a rule when its cause is gone: the service it worked around was retired, the bug it avoided was fixed, the tool it named was replaced. Check the history before deleting if you are unsure why it was added.

## Worked example: before

An invented repository, `ledgerline`, a TypeScript invoicing API with a Postgres database. This is an excerpt of the file as it stood, shortened to the lines that matter.

````markdown
# AGENTS.md

Welcome to Ledgerline. Please be careful and follow best practices at all times.

## Getting started
Run `npm install`, then `npm test` to make sure everything works.
Use `npm run lint:fix` before committing.

## Code style
- Use 2 spaces for indentation
- Use single quotes
- Sort imports alphabetically
- Keep functions small and focused

## Rules
- Do not edit the dist folder
- Do not touch the old billing module
- Write tests for everything
- Always update the changelog

## Architecture
(four screens describing every service, written in the first year)
````

Three kinds of problem sit in it. The commands were never rerun after the project moved. The style rules restate what the formatter and linter configuration already enforce. And the rules give no reason and no enforcer, so a reader cannot tell which are gates and which are habits.

## Worked example: the evidence

Following the procedure, the commands were run in a fresh clone before anything was rewritten.

| Command | Directory | Result | Verdict |
| --- | --- | --- | --- |
| `npm install` | repo root | exit 1, `ERESOLVE`: the lockfile is pnpm's; the project moved to pnpm | drop, replace |
| `pnpm install --frozen-lockfile` | repo root | exit 0 | keep |
| `pnpm test` | repo root | exit 1, `connect ECONNREFUSED 127.0.0.1:5432` | keep, name the prerequisite |
| `docker compose up -d db && pnpm test` | repo root | exit 0 | keep |
| `pnpm test src/invoices/totals.test.ts` | repo root | exit 0, one file run | keep as the narrow command |
| `npm run lint:fix` | repo root | exit 1, `Missing script: "lint:fix"` | drop |
| `pnpm lint --fix` | repo root | exit 0 | keep |
| `pnpm gen:types` | repo root | exit 0, rewrote `src/db/types.ts` | keep, note output is generated |

The realistic failure is the third row: `pnpm test` fails on a clean checkout because the test suite expects a Postgres on the default port that nothing starts. That is a finding. The old file said "make sure everything works" and never mentioned the database, so every cold session failed at the first test and either gave up or wasted effort on the connection error.

Enforcement was checked the same way. The formatter and linter are configured in the repository and run in CI, so the style rules are redundant. `dist/` is gitignored, so a hand edit never reaches a commit and the rule is harmless but needless. The changelog rule has a CI job that fails when the file is untouched, so it is enforced. "Write tests for everything" and "keep functions small" have no enforcer. The old billing module is covered by a code owner file that requires a review from its team, and the reason the file never gave is that its tests are known to be incomplete.

## Worked example: after

````markdown
# AGENTS.md

Ledgerline is a TypeScript API that creates and totals invoices for small
businesses. Node, Postgres, pnpm.

## Layout

| Path | What lives there |
| --- | --- |
| `src/invoices/` | Invoice creation and totals |
| `src/billing/` | The legacy billing module, see Boundaries |
| `src/db/types.ts` | Generated by `pnpm gen:types`, do not edit by hand |
| `migrations/` | SQL migrations, applied in filename order |

## Commands

Run from the repository root.

- Setup: `pnpm install --frozen-lockfile`
- Start the database the tests need: `docker compose up -d db`
- Verify a change: `pnpm test` (exits 0 when green; fails with
  `ECONNREFUSED 127.0.0.1:5432` if the database is not up)
- One test file: `pnpm test src/invoices/totals.test.ts`
- Format and lint: `pnpm lint --fix`

## Boundaries

- Do not edit `src/db/types.ts`: the next `pnpm gen:types` overwrites it.
  Enforced by: CI fails on a diff after regeneration.
- Do not change `src/billing/` without the billing team. Its tests are known
  to be incomplete, so a green run proves little. Enforced by: code owners
  require their review.
- Keep migrations additive so a rollback needs no data repair. Advice:
  nothing enforces this; review does.
- Update `CHANGELOG.md` for any user-visible change. Enforced by: the
  changelog job in CI.

## Where to read next

- `docs/testing.md`: before adding or changing a test.
- `docs/migrations.md`: before writing a migration.

## Unfinished work

Open work is in the issue tracker. Leave a half-done change on a branch named
`wip/short-description` with a note in the pull request on what is left.
````

Run the fresh-session test on this file. A cold session should answer question 1 from the opening, question 2 from the table, question 3 and 4 from Commands, and question 5 from the last section. If the session starts the tests without the database, the Commands section failed to make the prerequisite visible and gets reworded, not the question.

## What moved where

| Before | After | Why |
| --- | --- | --- |
| `npm install`, `npm test`, `npm run lint:fix` | pnpm commands, with the database step | Executed on a clean checkout; the old ones failed |
| Four style rules | Removed | The formatter and linter already enforce them |
| "Do not edit the dist folder" | Removed | Gitignored, so it cannot reach a commit |
| "Write tests for everything", "keep functions small" | Removed | No reason and no enforcer; the testing topic file covers what to test |
| "Do not touch the old billing module" | A boundary with the reason and the code owner enforcement | The reason is what lets an agent judge an edge case |
| Four screens of architecture | The layout table, and depth in topic files | Depth is read on demand rather than on every session |
| "Please be careful and follow best practices" | Removed | Says nothing a reader can act on |
