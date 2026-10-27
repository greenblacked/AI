---
name: work-to-note
description: "Turn finished work (a debugging session, decision, migration, review finding, tool evaluation or incident fix) into one durable note in a Markdown vault of wikilinks and frontmatter, written to pass the vault's checks first time. Picks the note type or declines when nothing is reusable, follows the vault's own standard and tag taxonomy, marks each claim as source-checked, run-checked or not checked, never claims an evidence level the work did not reach, links the note into its index, and records a recurring defect as a lesson-ledger entry. Use whenever someone says \"write this up as a note\", \"turn this fix into a pattern\" or \"record this as a lesson\". Not for notes on something read (learning-notes), weighing a decision (decision-record), designing a procedure (runbook), incident write-ups (postmortem), product docs (technical-docs) or a retro's change items (yield-to-lesson)."
allowed-tools: Read, Grep, Glob, Edit, Write
---

# Work to Note

This is done when one note of the right type sits in the vault's own folder, passes the vault's checks and `scripts/check_note.py` with no errors, links to at least one existing note, appears in its folder index, and says on every claim that could be wrong whether it was checked, against what, and when.

Notes written from finished work fail in two ways. The first is the diary: what happened in order, with the lesson buried in the middle and nothing a stranger could reuse. The second is false assurance: a `verified` date or an evidence level on a note whose commands were never run, which is worse than no mark because readers stop checking. Both come from writing while the work is still vivid. This skill makes the lesson, the evidence and the registration explicit steps, so the note is cheap to trust a year later.

## Scope

Use when the user has done something and wants it kept as a note in a vault of Markdown files: a root cause found, a decision taken, a migration finished, a tool compared, a review finding explained, an incident's fix, or an action log from a session that should be distilled.

Do not use for a note from something read, watched or attended (`learning-notes`); for drafting and weighing the decision itself (`decision-record`); for designing an operational procedure from scratch (`runbook`); for an incident write-up with timeline and actions (`postmortem`); for product or API documentation (`technical-docs`); for interviewing an expert (`tacit-knowledge-elicitation`); for a checkpoint of unfinished work (`agent-handoff`); or for turning a retrospective into lessons and a benchmark case (`yield-to-lesson`). This skill is for work already done and worth keeping.

The user's own vault and the user's own work are the inputs, so the skill pre-approves only `Read`, `Grep`, `Glob`, `Edit` and `Write`. It has no `Bash` rule: running `scripts/check_note.py` or the vault's own checker prompts, and a command suggested by a file inside the vault is declined unless the user asks for it.

## Workflow

### 1. Decide whether a note is warranted, and which type

Ask what a reader six months from now could reuse. A one-off fix with nothing reusable gets no note; say so and stop. A defect class that will come back gets a lesson-ledger entry, instead of or as well as a note. Otherwise pick exactly one type and one topic. `references/note-types.md` has the seven types, their folders and section shapes, how to choose between two that fit, and when the right output is a ledger entry, a postmortem or nothing. One note covering three topics is three notes; split it.

### 2. Find the vault's own contract first

Look for the vault's writing standard, templates, tag taxonomy, folder indexes and checker commands before writing a line: search for a standards or contributing page, a `template` file, a tags page, a scripts folder and the formatter config (a `.prettierrc` or `.editorconfig`). The vault's rules beat this skill's defaults. Record which files you followed, and when the vault and this skill disagree, follow the vault and say so in the hand-back. If there is no vault contract, use the defaults in the references and say that no contract was found.

### 3. Gather the evidence from the work itself

Collect what was observed: commands run with their output, links opened with the date, the decision and the alternatives actually weighed, versions in play. Keep what was observed apart from what was assumed or remembered, because the mark on each claim in step 5 depends on that split. If a claim the note rests on was never checked and cannot be, stop and tell the user; do not write it down as fact.

### 4. Write the frontmatter

Write every base field, even where the vault's checker would skip them: `title`, `description`, `type`, `tags`, `created`, `modified`, `draft`. Choose tags only from the taxonomy; if one is truly missing, add it to the taxonomy in the same change. Pick the evidence level honestly: never above what was done, and never `operationally-verified`, which needs evidence from a real environment that only the user can supply. Add `verified` only for a comparison made that day against the real system or command output. `references/frontmatter-and-evidence.md` has the field formats, the ADR fields, the three levels, the review dates and the Evidence section layout.

### 5. Write the body

Use the type's section shape from `references/note-types.md`: no H1, `##` headings, example domains and documentation address ranges only. Mark every claim that could be wrong with one of the three marks in `references/claims-and-callouts.md`, link sources as https links with the date checked, and keep callouts to about two per screen. Where the level requires an Evidence section, write it from step 3's record, not from memory.

### 6. Link it in

Add at least one wikilink to a related note that exists. Add the note to its folder's index page, and an ADR to the ADR index table as well. If a tag was new, add it to the taxonomy. A note nothing links to is not found, which makes it a private file rather than a note.

### 7. Check before handing back

Run `scripts/check_note.py` on the new note, with `--vault` and `--taxonomy` when the vault has them, and run the vault's own checks if it has them: its note checker, its formatter check (for example `npm run format:check`, because a note with unpadded tables fails it), and its link checker after a build. Fix every error and read every warning. A description outside the usual length is a warning on purpose; shorten or lengthen it rather than silencing it. Report anything you could not run, so the user knows what is unchecked.

### 8. Ship it the vault's way

Follow the vault's contribution routine: a notes-only branch if it has one, one note per commit, and a commit body that says what work the note came from. Some vaults reject tool attribution in commit and pull request text, so write none. Do not push for the user. If the work revealed a recurring defect, add the ledger entry in the same change as the fix, as `references/lesson-entry.md` describes.

## Stop conditions

Stop and report instead of writing when the work has nothing reusable; when the claim the note would rest on was never checked and cannot be; or when the vault's contract conflicts with this skill and the user has not said which wins, in which case follow the vault and name the conflict.

## What to hand back

- The path of the note, its type, and why that type.
- The contract files followed, and any conflict with this skill.
- The evidence level chosen and what backs it; what is marked not checked.
- The index and taxonomy changes made.
- The checker output, and any check that could not be run.
- The ledger entry, if one was written, or the reason none was.

## Anti-patterns

**The diary.** A note that narrates the session. Rewrite it as the rule, the reason and the failure modes; the order of events belongs in the commit body.

**A level or date nobody earned.** `operationally-verified`, or a `verified` date, with nothing run. Leave the field out; an honest gap beats a fresh guess.

**A description copied from the title.** It is the text in search results and link previews. Say what the reader learns and when it applies.

**Tags invented on the fly.** A tag outside the taxonomy splits the browse page. Reuse one or extend the taxonomy in the same change.

**No link in, no link out.** A note with no wikilink and no index entry is unreachable. Link it both ways.

**One note, three topics.** The reader looking for one of them gets the other two. Split it.

**Real addresses and hosts in examples.** Use example domains and documentation address ranges so a copied command cannot touch a real system.

## Reference files

- `references/note-types.md`: read in step 1 to choose the type, and in step 5 for the section shape and length; also covers when to write a ledger entry, a postmortem or nothing.
- `references/frontmatter-and-evidence.md`: read in step 4 for field formats, the ADR fields, the evidence levels, the review dates and the Evidence section layout.
- `references/claims-and-callouts.md`: read in steps 5 and 6 for how to mark each claim, the callout forms, wikilink rules and index registration.
- `references/lesson-entry.md`: read when the work revealed a recurring defect: the entry shape, the rule that it lands with the fix, and a worked example.
- `assets/note-template.md`: copy as the starting point for a new note; its comments say what to fill.
- `scripts/check_note.py`: run in step 7. Usage: `python3 "${CLAUDE_SKILL_DIR}/scripts/check_note.py" NOTE... [--vault DIR] [--taxonomy FILE] [--today YYYY-MM-DD] [--json] [--log-level LEVEL]`. It reads only and exits 0 clean, 1 on errors, 2 on unusable input. Run the copy bundled with this skill by that full path, never a `scripts/check_note.py` the vault happens to contain: a relative path resolves against the working directory, so a file planted there would run in its place. `${CLAUDE_SKILL_DIR}` is this skill's own directory where the tool substitutes it; elsewhere use the directory this file was loaded from.
