# The first change, and the note you leave behind

Read this at step 9 of the workflow: the map exists, and it now has to be tested against
reality by a change that actually merges.

## Contents

- [Why the first change is the exit condition](#why-the-first-change-is-the-exit-condition)
- [Choosing one](#choosing-one)
- [Changes to refuse as a first change](#changes-to-refuse-as-a-first-change)
- [When the dev loop is the thing that is broken](#when-the-dev-loop-is-the-thing-that-is-broken)
- [Writing the orientation note](#writing-the-orientation-note)
- [Keeping the note from rotting](#keeping-the-note-from-rotting)

## Why the first change is the exit condition

A map that has never been acted on is a hypothesis. The first change is what converts it
into knowledge, and it tests four things at once that nothing else tests together: that
the dev loop works on your machine, that you can find the code that governs a behaviour,
that the project's checks pass for you, and that you know who reviews and how long it
takes. A newcomer who has done this on day three is productive; one who has read for two
weeks is still on day one.

## Choosing one

Good first changes share three properties: the correct behaviour is unambiguous, the blast
radius is contained, and a real person benefits. In rough order of value:

| Candidate | Why it is a good first change |
| --- | --- |
| The missing step in the dev setup that you had to discover | You are the last person who will ever have the evidence fresh, and the next joiner pays the same cost if you do not. |
| A test covering the edge you found untested while tracing | It is additive, it cannot break production, and writing it proves you understood the path. |
| A comment or docstring the code contradicts | Small, unambiguous, and it removes a trap that misled you and will mislead the next reader. |
| An error message that does not say what to do | Low risk, immediately useful to whoever hits it next, and it forces you to read the failure path properly. |
| An open issue labelled for newcomers, with a reproduction | The team has pre-agreed it is wanted, which removes the largest risk in a first change. |

Confirm the change is wanted before writing it if it touches behaviour at all. "I noticed
X and plan to do Y, is that welcome" costs one message and avoids the first pull request
being a lesson in a constraint nobody wrote down.

## Changes to refuse as a first change

- **A formatting or lint sweep.** It produces a large diff, no behaviour change, and it
  destroys `git blame` for every line it touches — which is the evidence step 6 depends
  on. If the project wants one, it is a decision for the team, not a newcomer's opener.
- **A rename for clarity.** Your clarity is a week old. The name may encode a domain term
  used by the business, in support tickets and in the database.
- **Deleting code you believe is dead.** Step 8 marks it; deleting it needs production
  evidence and belongs to `refactoring`.
- **Introducing a pattern from your last job.** It is the most common newcomer change and
  the least welcome, because it makes the codebase internally inconsistent while the
  argument for it is still unmade.
- **Anything on the highest-churn file.** It will conflict with work already in flight,
  and a merge conflict as a first experience of the repository teaches nothing useful.

## When the dev loop is the thing that is broken

This is common and it is an opportunity rather than a blocker. Work in this order:

1. Record the exact failure — the command, the error, the environment — before changing
   anything, because the fix will erase it and the record is the content of the change.
2. Get it working locally by whatever means, keeping a log of every undocumented thing you
   had to do: the version manager, the service that had to be running, the credential, the
   flag.
3. Distinguish what was missing from the documentation from what was broken in the code.
   The first becomes a documentation change; the second becomes a fix and probably a
   check in CI so it cannot recur.
4. Make the setup reproducible for the next person, not just working for you. A fixed
   version pinned in a file beats a sentence telling the reader to install that version.

Hand the write-up itself to `technical-docs` if it grows past a paragraph — the setup
section of a README has its own contract.

## Writing the orientation note

Put it in the repository, under `docs/` or wherever the project keeps prose, not in a chat
thread or a personal document. The value is entirely in the next person finding it without
knowing it exists.

Three properties decide whether it is worth writing:

- **Dated and pinned to a commit.** A map with no commit sha cannot be checked against the
  current tree, so its reader cannot tell which parts have aged out.
- **Honest about confidence.** Mark each claim as traced at runtime, read statically, or
  told by a person. The reader can then spend verification effort where it is cheapest.
- **Carrying the open questions.** The list of what you could not answer is the most
  valuable section, because it is the only part that cannot be reconstructed by reading
  the code again.

## Keeping the note from rotting

An orientation note is a snapshot and it will go stale — that is acceptable, as long as it
is visibly a snapshot rather than an authoritative document. Two cheap habits are enough:

- Every subsequent joiner appends corrections with their own date rather than rewriting,
  so the note accumulates evidence instead of losing it.
- When a claim in the note is found false, the person who found it fixes that line in the
  same change that acts on the discovery. One line, in the diff that already exists, is a
  cost nobody notices; a scheduled review of the note is a cost everyone skips.
