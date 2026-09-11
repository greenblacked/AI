---
name: technical-docs
description: "Write and maintain documentation still true in six months — a README, an onboarding or handover guide, an architecture overview, an API guide, and the pruning of whatever has gone stale: name the reader and what they can already do, pick exactly one Diátaxis mode (tutorial, how-to, reference or explanation) rather than blending two, execute every command and verify every path and link, stamp an owner and a last-verified date, and delete a page that has gone false rather than writing a newer one beside it. Use this skill whenever someone asks to \"write a README for this\", \"document this service before I go on leave\", \"write an architecture overview\", \"our docs are out of date\", \"nobody can onboard onto this without me sitting with them\", or \"how do we stop the wiki growing forever\". Do not use it for the procedure someone follows at 3am (runbook), a decision and its alternatives (decision-record), a publishable article (write-technical-article), the incident write-up (postmortem), ramping a new joiner (onboarding-plan), designing the interface (api-design), or the dated orientation snapshot of a repository you have just landed in (codebase-orientation)."
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(git:*), Bash(rg:*), Bash(curl:*)
---

# Technical Docs

A document is finished when a named reader who has only the stated prerequisites can follow it end to end without asking anyone, every command in it has been executed as written, and it carries an owner and a date proving when that was last true.

Documentation fails in five specific ways, and none of them is "not enough documentation". It is written for nobody in particular, so it simultaneously over-explains to the expert and under-explains to the newcomer. It mixes two of the four Diátaxis modes — a tutorial with reference tables wedged into it, a how-to interrupted by three paragraphs of rationale — so the reader following steps has to skim past theory and the reader seeking understanding has to skim past commands. Its commands were written from memory rather than run, so a flag is wrong, a path moved, and the reader loses trust at the first failure and stops believing the rest. It has no owner and no date, so it decays invisibly and is trusted exactly as much on the day it becomes false as on the day it was written. And when it does go stale someone writes a new page beside it rather than deleting the old, so the reader now has two documents that disagree and no way to tell which is current. This skill fixes each in turn: reader first, one mode per document, every command executed, owner and date stamped, and pruning treated as part of writing rather than a project nobody schedules.

## Scope

Use for: a README for a repository or service; a how-to for a task someone performs during working hours; an architecture or design overview explaining how a system fits together; an API guide a human reads alongside the generated reference; an onboarding or setup document; auditing and pruning a documentation set that has gone stale.

Do not use for: the operational procedure a responder follows during an incident (`runbook`), recording a decision and the alternatives rejected (`decision-record`), an article written for publication with a thesis and an argument (`write-technical-article`), the incident write-up afterwards (`postmortem`), the plan for onboarding a person rather than documenting a system (`onboarding-plan`), or designing the interface the guide describes (`api-design`).

The boundary with `codebase-orientation` is the artefact rather than the topic, and it runs both ways: the dated, confidence-marked orientation snapshot someone writes after reading an unfamiliar repository belongs to `codebase-orientation`; anything owned, re-verified and linked from the README belongs here.

## The four modes, and why mixing them is the core defect

Diátaxis is Daniele Procida's framework, published at https://diataxis.fr under CC BY-SA. It splits documentation by what the reader is doing when they open it. The split matters because the four have incompatible obligations: a tutorial must never present a choice, and reference must present every choice.

| Mode | Reader's state | Obligation | Failure when mixed in |
| --- | --- | --- | --- |
| **Tutorial** | Learning, no context, needs a win | One path, no options, guaranteed to work end to end | Options inserted "for completeness" leave a beginner stalled at a decision they have no basis to make. |
| **How-to** | Competent, has a specific goal now | The shortest correct sequence of steps for that goal | Explanation inserted between steps is skimmed under time pressure, taking a conditional step with it. |
| **Reference** | Knows the goal, needs a fact | Complete, accurate, structured, consistent, boring | Narrative and worked examples make a fact hard to look up and make completeness impossible to audit. |
| **Explanation** | Away from the keyboard, wants to understand | Context, alternatives, trade-offs, why it is this way | Commands here are executed by someone who is not in a position to run them safely. |

Decide the mode before the first sentence and write it at the top of the file. When a draft needs two, that is two documents with a link between them, not one document with a heading. The commonest instance in the wild is a README that is a tutorial for the first screen, reference for the second, and explanation for the third, which serves none of the three readers.

## Workflow

### 1. Name the reader and their starting point

Write both down, above the draft, before anything else: who this is for, and what they can already do. "A backend engineer on another team, who can run our standard dev environment but has never seen this service" produces different documentation from "a data scientist with Python and no Docker".

This sentence is the tool that settles every later argument about depth. Without it, every review comment ("should we explain what a migration is?") is an unresolvable matter of taste; with it, the answer is a fact about the named reader.

### 2. State the goal and the finished state

One sentence naming what the reader will be able to do, and one describing how they know it worked — a specific output, a URL that responds, a row that exists. A document that ends without a success criterion leaves the reader unsure whether to proceed or debug, and that uncertainty is where they give up and ask a person, which is the cost the document existed to avoid.

### 3. Pick exactly one mode

Use the table above. If the draft resists the choice, the goal in step 2 is two goals; split it and link them.

### 4. List the prerequisites as checks, not nouns

Each prerequisite is a command the reader can run to confirm they have it, with the expected output. "Requires Docker" tells a reader with the wrong major version nothing; `docker --version` with the minimum stated tells them immediately. Put access and credentials here too — the request that takes two days to approve has to appear before step 1, not in step 7 where it stalls the whole document.

### 5. Write the body in the mode's own shape

A tutorial is a single path with no branch. A how-to is numbered steps, each one action, with the conditional stated before the action rather than after it. Reference is tabular, alphabetical or otherwise mechanically ordered, and complete. Explanation is prose that names the alternatives considered and why the current shape won.

Keep one instruction per step. A step containing two verbs is two steps, and the second is the one that gets missed.

### 6. Execute everything

This is the gate that separates documentation from plausible documentation. Run every command as written, in a clean environment, in the document's own order. Follow every link. Confirm every file path exists at the path given.

```bash
git ls-files '*.md' '*.mdx' | while read -r f; do
  rg -o '\]\(([^)#][^)]*)\)' -r '$1' "$f" | while read -r link; do
    case "$link" in http*) continue;; esac
    link=${link%%#*}
    [ -n "$link" ] || continue
    [ -e "$(dirname "$f")/$link" ] || printf '%s: broken link %s\n' "$f" "$link"
  done
done
```

Two details decide whether that reports anything. `rg -n` on the file list prefixes a line
number, so every filename arrives as `12:docs/x.md` and every inner command fails silently
while the loop still exits 0 — list the files with a pathspec instead. And stripping the
fragment before the existence test is what stops `](writing-skills.md#trigger-eval-sets)`
being reported as broken.

A path that does not exist is the failure this repository's own validator was written to catch: two skills shipped for months naming reference files nobody had written, and nothing failed — the reader follows the pointer, finds nothing, and proceeds on incomplete information with no error anywhere. A broken pointer in documentation is the same defect with the same silence. Verify the pointer at the moment you write it.

Where a command cannot be executed — it is destructive, or it needs production access — mark it explicitly as unverified with the date, rather than letting it sit among the verified ones wearing the same clothes.

### 7. Cut what the reader does not need

Delete anything that is true but not needed to reach the goal: the history of why the flag is named that, the alternative approach the team rejected, the reassurance that this is easy. Each belongs in an explanation document or nowhere. Length is a cost paid by every reader, and in a how-to the cost is paid under time pressure.

### 8. Stamp ownership and verification

At the top, visible without scrolling: the owning team or rota, and the date the steps were last executed — not the date of the last typo fix. Name a team, never a person, because "ask Priya" is correct for about eleven months.

A document dated fourteen months ago still helps: it tells the reader to treat every command in it with suspicion, which is far better than undated confidence. Undated documentation cannot be audited, cannot be pruned on evidence, and is trusted equally on its best and worst day.

### 9. Test it on someone who is not you

Give it to one person matching the step 1 reader and watch without helping. Every question they ask is a defect, and the place they stop is the document's real quality level. Ten minutes of this beats any amount of re-reading, because the author cannot see their own assumed knowledge by reading.

## What belongs in a README

The README is the most over-stuffed document in most repositories, because everything with no other home lands in it.

| Belongs | Does not belong | Where it goes instead |
| --- | --- | --- |
| One sentence on what this is and who uses it | A feature tour or marketing copy | The product site, or nowhere. |
| How to run it locally, verified today | Every configuration option | A reference page, generated from the config schema where possible. |
| How to run the tests and the linters | The full test strategy | A contributing guide. |
| The handful of commands used weekly | Every command ever useful | A reference page or the tool's own help output. |
| Where to go next, as links with one line each | The architecture in prose | An explanation document, linked. |
| Who owns it and how to reach them | Individual names | A team, a rota, a channel. |
| The last-verified date | Changelogs and release notes | `CHANGELOG.md`, or the releases page. |

The test is the newcomer's first hour: if a section does not help someone get the thing running or decide where to read next, it is costing every reader and serving a few. `references/readme.md` has the full skeleton with the ordering that works and the sections to resist.

## Pruning: the half nobody does

Documentation sets fail by accumulation, not by absence. Adding is easy and socially safe; deleting feels destructive, so a stale page survives beside its replacement and the reader gets two answers.

Audit on evidence rather than impressions. For each page answer three questions in order, and stop at the first that decides it:

1. **Does it execute?** Run its first three commands. A failure settles the page immediately: it is actively harmful, because it sends the reader confidently wrong. Fix it now or delete it now — there is no third option and no backlog ticket.
2. **Is it reached?** No inbound link and no page views in twelve months means nobody depends on it, whatever its quality.
3. **Is it contradicted?** Another page describing the same thing differently makes both untrustworthy, because the reader has no way to choose. Merge into one and redirect the other.

A page that executes, is reached and is uncontradicted is fine even if it is old. Age alone is not a defect; unverified age is.

Deleting documentation is reversible — the version history holds it — while leaving false documentation in place is not, because the cost lands on a reader who cannot tell. `references/pruning.md` carries the verdict table for every signal the audit turns up, how to run it across a whole set, the redirect and archive mechanics, and how to make deletion routine instead of a decision.

## Anti-patterns

**Documentation with no named reader.** Written for "the user", it simultaneously explains what a container is and assumes knowledge of the internal deployment tool. Every review argument about depth becomes taste rather than fact. Name the reader in one sentence at the top of the draft.

**Two Diátaxis modes in one document.** The commonest single defect. A how-to with rationale between the steps is skimmed under time pressure and the reader loses a conditional clause; a tutorial with a reference table stalls a beginner at a choice they cannot make. Split it and link.

**Commands written from memory.** A wrong flag or a moved path fails at step 2 of 9, and the reader now disbelieves the remaining seven steps — including the ones that were right. The damage is to the whole document, not the one line. Execute everything, in a clean environment, in order.

**A path or link nobody checked.** It fails silently: the reader follows it, finds nothing, and continues with a gap they do not know they have. This is precisely the failure that motivated this repository's validator, after two skills shipped for months pointing at reference files that were never written. Verify at the moment of writing.

**No owner and no last-verified date.** The document cannot be audited or pruned on evidence, and it looks exactly as authoritative on the day it becomes false as on the day it was written. A team name and a date cost one line.

**Documenting the workaround instead of fixing the thing.** Six paragraphs explaining how to get around an unclear error message, when changing the message is a two-line diff. Documentation becomes the place where defects are stored rather than fixed, and it grows without bound. Ask whether the fix is cheaper than the page; it often is.

**Screenshots of text.** They are unsearchable, unreadable by assistive technology, invisible to a diff, and stale the moment a button moves — and unlike prose, nobody can see they are stale. Paste the text or the command; screenshot only genuinely visual layout.

**A new page instead of fixing the old one.** "Setup (new)" beside "Setup" leaves the reader to guess, and they guess wrong roughly half the time. Fix in place, and delete what the fix replaced.

**Deferring deletion to a backlog ticket.** The ticket is never prioritised because deleting documentation has no visible benefit, so harmful pages persist for years. Delete in the same change as the discovery; that is the only moment the evidence is in hand.

**Explaining what the code already says.** A comment-level restatement of each function goes stale with the next refactor and nothing catches it. Document the why, the contract and the surprising parts; generate the rest from the source where it can be generated.

## Output format

```markdown
# [Title naming the reader's goal, in their words]

**Type:** [Tutorial | How-to | Reference | Explanation]
**For:** [the named reader and what they can already do]
**Owner:** [team or rota] · **Last verified:** [YYYY-MM-DD, by whom, against what version]

## What you will end up with
[One sentence on the outcome, and the observable proof it worked.]

## Before you start
[Each prerequisite as a command with its expected output, access requests first.]

## [The body, in the shape of the declared mode]
[Tutorial: one path, no choices. How-to: numbered steps, one action each.
Reference: tables, mechanically ordered, complete. Explanation: prose with
the alternatives and the trade-offs.]

## When it does not work
[The two or three failures that actually happen, each with its fix.]

## Where to go next
[Links with one line each saying what the reader would go there for.]
```

## Reference files

- `references/diataxis.md` — read when a draft resists being one mode, or when splitting an overloaded page: the four modes in full, the diagnostic questions that place a document, and worked splits of the mixed pages that occur most often.
- `references/readme.md` — read when writing or trimming a README: the section order that works for a newcomer's first hour, what each section must contain, and the sections to move out with where each goes.
- `references/pruning.md` — read when auditing an existing documentation set rather than writing a new page: how to gather usage and staleness evidence, the archive and redirect mechanics, and how to make deletion a routine part of changes instead of a project.
