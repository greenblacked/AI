# Messages and calibration

Read this when a guardrail exists and needs to be made usable and trustworthy: writing its
failure message, replaying it over recent merged changes before it blocks anyone, handling
a false positive, and listing the paths the agent must not be able to edit.

## Contents

- [The failure message](#the-failure-message)
- [Replay](#replay)
- [False positives](#false-positives)
- [Protected paths](#protected-paths)
- [Turning review comments into rules](#turning-review-comments-into-rules)

## The failure message

An agent that hits a guardrail has one turn to correct itself, and the message is all it
reads. A message that only says something is wrong sends it guessing, and the cheapest
guess is to make the check stop complaining. Write every message with four parts, in this
order:

1. **What failed.** The rule's name and the exact location, as `file:line` where there is
   one.
2. **Why the rule exists.** One sentence naming the consequence, so the agent can tell
   whether its case is a real violation or a legitimate exception.
3. **The smallest fix.** The concrete change, with the replacement named, not a pointer to
   a document.
4. **What not to do, and who decides exceptions.** One line: do not suppress or skip the
   check; if the finding looks wrong, stop and report it to a person.

A secret never appears in the message. Report the rule and the location and say the value
was withheld. A message that echoes the matched text turns the log, the transcript and any
issue the failure is pasted into into a second copy of the secret.

**A message an agent can act on.**

```text
guard no-raw-sql: src/billing/report.py:42 builds a query by string formatting.
Why: interpolated values reach the database as SQL, so a customer name can change the query.
Fix: pass the values as parameters, for example db.execute("... WHERE id = %s", (invoice_id,)).
Do not add a suppression. If this query is genuinely static, stop and ask a maintainer to
add it to the guard's allowlist.
```

**A message that gets worked around.**

```text
Error: policy violation (code 17)
```

It names no rule, no location, no reason and no fix. The agent cannot distinguish a real
defect from a misfire, so it will try the nearest thing that turns the check green, and
that is usually a suppression or an edit to the check.

**A message that leaks.**

```text
secret scan failed: found token ending in <last four characters shown> in config/prod.env line 12
```

Even a fragment is more than the log needs. Say instead that the `generic-api-key` rule
matched at `config/prod.env:12`, that the value is not shown, and that the fix is to move
it to the secret store and rotate it. Rotation belongs in the fix because a committed
secret is exposed whether or not the commit lands.

Test the message the way you test the rule: read it with no other context and ask whether
a stranger could fix the violation in one step. If not, the message is unfinished.

## Replay

A guardrail that blocks legitimate work gets bypassed, and a bypassed guardrail is worse
than none, because everyone now believes the rule is enforced. Before a guardrail is
allowed to block anything, run it over changes that have already merged and look at what it
would have done.

1. **Choose the window.** The most recent merged changes on the integration branch: as many
   as it takes for the rule's legitimate cases to have had a chance to appear, and all of
   them if the history is short. State the number you used, and the date range it spans,
   in the report so it can be reproduced.
2. **Run it report-only.** The replay must not change the repository. Run the guard against
   each change's diff, or against a throwaway checkout of each commit for a guard that reads
   the tree, and record the verdict without blocking or fixing anything.
3. **Classify every block by hand.** For each change the guard would have stopped, open it
   and decide: a real violation, a legitimate change the rule wrongly caught, or unclear.
   Count each class. A block you cannot classify is a finding about the message or the
   rule, not a number to round away.
4. **Check the other direction.** Look at changes the guard let through that the review
   comments flagged for the same problem. A guard that blocks nothing and misses the
   known cases is not calibrated, it is silent.

A replay loop for a guard that reads a unified diff on stdin and exits non-zero to block:

```bash
set -Eeuo pipefail
guard="$1"   # command that reads a unified diff on stdin and exits non-zero to block
n="$2"       # how many merged changes to replay, newest first
base="$3"    # the integration branch, for example origin/main

total=0
blocked=0
while read -r sha; do
  # A root commit has no parent to diff against; skip it rather than report an error.
  git rev-parse --verify --quiet "$sha^" >/dev/null || continue
  total=$((total + 1))
  if ! git diff "$sha^" "$sha" | "$guard" >/dev/null; then
    blocked=$((blocked + 1))
    echo "would block: $(git log -1 --format='%h %an %s' "$sha")"
  fi
done < <(git log --first-parent --format=%H -n "$n" "$base")
echo "replayed $total, would block $blocked"
```

Pass the guard as a path to an executable. Walking `--first-parent` makes each merge commit
or squashed commit one change, which is what a pull request was; a shallow clone has too
little history to replay, so fetch more before drawing a conclusion. A guard that needs the
tree rather than the diff is run the same way inside a worktree checked out at each commit.

What the replay cannot tell you: how an agent will behave under the rule, since the history
is mostly human work, and anything that only appears in code not yet written. Treat it as a
floor on how noisy the guard is, not a ceiling.

Read the counts as counts. Do not turn them into a percentage and compare it with a
threshold from somewhere else; what matters is whether the specific changes the guard
would have blocked were ones you would have wanted blocked.

## False positives

Each false positive is evidence about the rule, and the rule is what you change.

- **Record it.** Keep the change, the line that tripped the guard, and why it was
  legitimate. This is the evidence, and it stays as found.
- **Tune the rule, never the evidence.** Narrow the pattern, add a precondition, or move up
  a rung to one that can see the distinction. Do not edit the replayed history, drop the
  inconvenient change from the window, or reclassify it to make the count look better.
- **Keep both kinds of case as the guard's own tests.** Each real violation becomes a
  fixture that must trip it, and each false positive becomes one that must not. Put them
  where the guard is tested, which is a protected path. A tuned rule that regresses is then
  caught by the next change to the guard.
- **Do not add a blanket exemption.** An allowlist entry is a decision a person makes for
  one named case, with a reason, in a protected file. An agent that can add its own entry
  has found the suppression route again.
- **Re-run the replay after tuning.** The tuned rule has to pass over the same window it
  was tuned on, and then over a different window, so you know it was not fitted to one
  month of history.

If a rule cannot reach an acceptable false-positive rate at any rung, say so and leave the
rule as instruction text with a named owner. A noisy check that blocks legitimate work is
a worse outcome than an honest one that does not exist.

Move a guard from report-only to blocking only once the replay is clean enough that you
would be comfortable explaining each block to the person it stopped. Never advise
`--no-verify`, disabling the check, or loosening a permission to get a particular change
past it; if the guard is wrong for this change, the answer is a person deciding an
exception, recorded in the rule's own allowlist.

## Protected paths

A guardrail the agent can edit is advice. The agent that is blocked by a rule can satisfy
it by changing the rule, so the rule's own files must sit where the agent cannot write, or
where a change to them cannot merge without a human. List these for the repository you are
working in:

| Path class | Why it matters |
| --- | --- |
| The guard's own configuration: linter rules, type-checker strictness, banned-API lists | Loosening a rule is cheaper than fixing the code |
| The guard's scripts, hook scripts and their fixtures | A guard that can be edited can be made to pass |
| The tests, snapshots and golden files | The cheapest route to green is changing the expectation |
| The CI definition and any required-check configuration | A pipeline step can be removed, skipped or made non-blocking |
| Coverage floors, quality thresholds and the lockfile | A lowered floor passes a change nobody improved |
| The agent's settings and permission files | A permission the agent can widen is not a restriction |
| Ownership and branch-protection definitions, such as a code-owners file | They decide who must approve a change to everything above |
| The replay corpus and its recorded false positives | Editing the evidence defeats the calibration |

Protect them in layers, because each layer sees something the others do not:

- **Where the agent writes.** A permission or sandbox setting denying writes to those paths
  (rung 7), and in Claude Code an agent tool hook that reports an edit to one (rung 6). Both
  are local, and both sit in files the agent might otherwise reach, so neither is
  authoritative alone.
- **Where the change merges.** A required review from a person who owns those paths, and a
  CI check that fails any change touching them without that approval. Run the check from a
  definition the pull request cannot edit: the integration branch's copy, or a required
  check configured outside the repository (a ruleset or an organisation-level required
  workflow on GitHub, and the equivalent elsewhere).
- **Suppressions and skips are themselves a finding.** Detect them in the diff: an added
  `noqa`, `type: ignore`, `@ts-ignore`, `eslint-disable`, `nolint` or `#[allow(`; a newly
  skipped or expected-to-fail test; a test count that shrank; an edit to lint
  configuration, a coverage floor or a workflow file. The `/agent-diff-audit` command is the
  diff-level detector for exactly this and hands the flagged list to `code-review`; the
  CI script in the ladder reference is the portable version for a pipeline or a tool
  without that command.

When the agent needs to change one of these paths for a genuine reason, it stops and
reports the reason to a person. It does not work around the protection, and the person
decides.

## Turning review comments into rules

Recurring review comments are the best source of rules, because a human has already
decided each one was worth saying, and said it more than once. The `review-comment-miner`
subagent reads an exported pile of comments and returns clusters with an independent-
instance count, one verbatim quote and candidate destinations. It counts independent pull
requests or authors, not raw comments, and reports anything under three as an anecdote.
Respect that bar: a rule built from one memorable comment is a rule for a case that may
never recur. Where that subagent is not available, do the same cluster-and-count by hand
on the exported comments.

Route each cluster to a rung by asking what the comment is about, using the table in the
ladder reference:

| Recurring comment | Likely rung |
| --- | --- |
| "Wrong type of id passed here" | Type system |
| "Do not call this deprecated helper" | Linter |
| "This path has no test for the error case" | Test, or a CI coverage check |
| "You added a dependency without asking" | CI check on the manifest diff |
| "Do not edit the generated files by hand" | Permission, plus a CI check |
| "Please explain why in the commit message" | Instruction text and review; a message-format hook only if the format is mechanical |

A comment that needs judgement every time stays a comment. Mechanise only what a check can
decide, and then apply the whole procedure to it: the checkable statement, the lowest rung,
red before green, a message, protection, and a replay before it blocks anyone.
