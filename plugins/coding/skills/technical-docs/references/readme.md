# The README

Read this when writing a README from scratch or trimming one that has absorbed everything
with no other home. The governing constraint is a newcomer's first hour: nothing in the
file should fail to help them run the thing or decide where to read next.

## Contents

- [The order that works](#the-order-that-works)
- [Section by section](#section-by-section)
- [The skeleton](#the-skeleton)
- [What to move out, and where](#what-to-move-out-and-where)
- [Verifying a README](#verifying-a-readme)

## The order that works

Readers arrive with one of three questions, in this sequence: is this the thing I am
looking for, can I run it, and where do I go next. The order below answers them in that
order, and every departure from it costs the reader a scroll.

1. What this is, in one sentence.
2. Whether it is for them: who uses it, what it is not.
3. Getting it running, verified.
4. Running the tests and checks.
5. The handful of commands used weekly.
6. Where to go next, as links.
7. Ownership and the last-verified date.

The ownership line may sit at the top instead; what it may not do is be absent.

## Section by section

**What this is.** One sentence, no adjectives, naming the users and what they get. If it
takes three sentences, the repository does more than one thing and the extra sentences are
a sign worth acting on.

**Who it is for and what it is not.** Two lines. The second prevents the most expensive
kind of reader error, which is spending an hour on the wrong repository in a set of six
similarly named ones.

**Getting it running.** Prerequisites as commands with expected output, then the shortest
path to something observable — a server responding, a test passing, a row written. State
the expected wall-clock time, because a reader who does not know a build takes eight
minutes assumes at four minutes that it has hung.

**Tests and checks.** The exact commands CI runs, so that a contributor can get the same
verdict locally before pushing. If they differ from CI, that difference is the first thing
to fix.

**Weekly commands.** Five to ten, no more. The test is frequency, not completeness: a
command used once a quarter belongs in reference where it can be looked up.

**Where to go next.** Each link with one line saying what the reader would go there for. A
bare list of filenames is a directory listing, and the reader opens three before finding
the one they wanted.

**Ownership and verification.** Team or rota, channel, and the date the setup steps were
last executed on a clean machine.

## The skeleton

```markdown
# <name>

<One sentence: who uses this and what they get.>

**Owner:** <team or rota> · **Contact:** <channel> · **Setup last verified:** <YYYY-MM-DD>

## Is this what you want
<What it does. What it deliberately does not do, and what does that instead.>

## Run it locally
<Prerequisites as commands with expected output.>
<The shortest path to something observable, with expected timings.>

## Tests and checks
<The exact commands CI runs.>

## Common commands
<Five to ten, each with one line on when it is used.>

## Where to go next
<Link — one line on what the reader would go there for.>
```

## What to move out, and where

| Currently in the README | Move it to |
| --- | --- |
| Every configuration option | A reference page, generated from the config schema where one exists. |
| The architecture, in prose | An explanation document, linked from "where to go next". |
| The contribution process, branching and review rules | A contributing guide. |
| Release notes and version history | The releases page or a changelog file. |
| A full API listing | Generated reference from the schema; the README links to it. |
| Troubleshooting that has grown past three items | A how-to, titled by the symptom the reader searches for. |
| The operational procedure for when it breaks in production | A runbook; see the `runbook` skill, which has its own contract. |
| Screenshots of terminal output | Paste the text. It is searchable, diffable and readable by assistive technology. |

Moving something out means leaving a one-line link behind, not a summary. A summary beside
the real document is the two-documents-that-disagree failure in miniature.

## Verifying a README

The only verification that counts is executing it on a machine that has never built the
project, in the order written, changing nothing. A container image with nothing installed
is the cheapest approximation and takes minutes.

Three things fail almost every time, so check them first: a tool the author has globally
installed and never thought about, a credential or repository access the author already
holds, and a service the author happens to have running. Each of these is invisible from
the author's machine and fatal on anyone else's.

Record the date of that run in the header. That date, and not the file's modification
time, is what a reader needs — a typo fix last week says nothing about whether the build
command still works.
