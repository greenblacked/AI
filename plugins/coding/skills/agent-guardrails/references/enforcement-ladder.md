# The enforcement ladder

Read this when you have a checkable rule and need to decide which mechanism should hold
it: what each rung can and cannot see, a worked example for each, and how to choose
between two rungs that could both express the rule.

## Contents

- [How to read the ladder](#how-to-read-the-ladder)
- [Rung 1: type system or compiler](#rung-1-type-system-or-compiler)
- [Rung 2: linter or static rule](#rung-2-linter-or-static-rule)
- [Rung 3: test](#rung-3-test)
- [Rung 4: CI check](#rung-4-ci-check)
- [Rung 5: git hook](#rung-5-git-hook)
- [Rung 6: agent tool hook](#rung-6-agent-tool-hook)
- [Rung 7: permission or sandbox setting](#rung-7-permission-or-sandbox-setting)
- [Rung 8: instruction text](#rung-8-instruction-text)
- [Choosing](#choosing)

## How to read the ladder

The rungs are ordered by cost to the people and agents working in the repository, not by
strength. A lower rung gives feedback earlier, needs less maintenance, and runs for every
contributor and every tool, so it is preferred whenever it can express the rule. A rung
higher up exists because something the lower ones cannot see matters.

Every rung shares one weakness: it is a file or a setting, and whatever can edit the file
can weaken the rung. That is handled once, in the protected-path list in
[the messages and calibration reference](messages-and-calibration.md#protected-paths),
rather than repeated under each rung.

Examples below use widely known tools. They illustrate the shape of each rung; the stack
decides the exact spelling, and the principle holds when the tool differs.

## Rung 1: type system or compiler

**Can enforce.** Shape: which values may be combined, which cases must be handled, which
states exist at all. A rule that is a property of data can often be made impossible to
violate instead of detected after the fact.

**Cannot see.** Runtime values, behaviour, ordering, anything crossing a boundary the
types do not cover, and any place an escape hatch (`any`, a cast, `unsafe`, an ignore
comment) is used. The escape hatch is the agent's cheapest route round this rung, so a
rule enforced here still needs the suppression detector described in the protected-path
section.

**Worked example.** The agent keeps passing an account identifier where a user identifier
is expected, and both are strings. Give them distinct types so the compiler rejects the
swap:

```typescript
type UserId = string & { readonly __brand: "UserId" };
type AccountId = string & { readonly __brand: "AccountId" };

function closeAccount(id: AccountId): void { /* ... */ }

declare const user: UserId;
closeAccount(user); // compile error: UserId is not assignable to AccountId
```

The same idea in other stacks is a newtype, a wrapper class or an opaque alias. Pair it
with the compiler's strictest settings, and with a rule against escape hatches, or the
agent will cast its way to green.

## Rung 2: linter or static rule

**Can enforce.** A forbidden or required construct visible in the source: a banned import
or call, a missing argument, a naming pattern, a structural pattern. Fast, local, and it
points at the exact line.

**Cannot see.** Behaviour, data flow across functions, intent, or anything that depends on
what runs rather than what is written. A rule that tries to approximate those with
patterns produces both misses and false positives, which is the signal to move up a rung.

**Worked example.** The agent keeps calling a function the project has deprecated. A banned
API entry in ruff, a Python linter, makes the call a lint error with a message naming the replacement:

```toml
[tool.ruff.lint]
select = ["TID251"]

[tool.ruff.lint.flake8-tidy-imports.banned-api]
"datetime.datetime.utcnow".msg = "utcnow returns a naive timestamp; use datetime.now(timezone.utc)."
```

Running `ruff check .` over a file that calls it exits 1 and prints the rule code, the file
and line, and that message. ESLint's `no-restricted-imports` and `no-restricted-syntax`,
and Semgrep's pattern rules, fill the same role elsewhere. The message text is the
interface, so write it by the standard in the messages reference.

## Rung 3: test

**Can enforce.** Behaviour, and also structure, because a test can read source files. A
test is the right rung when the rule needs to run code, or when no linter expresses the
rule but a short scan of the tree does.

**Cannot see.** What it does not exercise. A passing suite says nothing about a path no
case reaches. It is also the most edited file in an agent's session, since a test is the
cheapest thing to change to reach green, so a guard that lives in a test lives in a
protected path or it is advice.

**Worked example.** The same rule as above, written as a structural test for a stack with
no linter hook available. It reports the location and the fix, and does not print the
offending line:

```python
import pathlib
import re

FORBIDDEN = re.compile(r"\bdatetime\.utcnow\(")


def test_no_naive_utc_timestamps():
    offenders = []
    for path in pathlib.Path("src").rglob("*.py"):
        for number, text in enumerate(path.read_text().splitlines(), start=1):
            if FORBIDDEN.search(text):
                offenders.append(f"{path}:{number}")
    assert not offenders, (
        "naive UTC timestamps at " + ", ".join(offenders) + ". "
        "Why: utcnow() carries no timezone, so comparing it with an aware value raises, "
        "and treating it as local time shifts it by the offset. "
        "Fix: use datetime.now(timezone.utc)."
    )
```

Run against a tree that contains a violation, pytest ends with `1 failed` and the
assertion text above; run against the corrected tree it passes. That pair is the evidence
step 3 of the procedure asks for.

## Rung 4: CI check

**Can enforce.** Properties of the whole repository or of the whole change, on a machine
the contributor does not control: a diff-level rule, a coverage floor, a lockfile that must
match its manifest, a required file, a protected-path rule. It is the backstop for every
rung below it, because local hooks and local configuration can be skipped.

**Cannot see.** Anything before the push, so feedback is slow. It also runs whatever the
pull request's own copy of the pipeline definition says unless that definition is itself
protected, which makes the CI configuration the first path to guard.

**Worked example.** A rule about the change rather than the tree: no added line may carry a
suppression comment. The script reads a unified diff on stdin and reports file and line
only:

```bash
#!/usr/bin/env bash
# Reads a unified diff on stdin and exits 1 when it adds a suppression comment.
set -Eeuo pipefail

# A file header is only a header outside a hunk: inside one, an added line that reads
# "++ b/x" is content and looks identical. So the hunk's line counts decide which it is.
# Git quotes a path holding a newline or special bytes as +++ "b/..." with escapes, and
# appends a tab to a path holding a space; both are normalised before the name is kept.
hits=$(awk '
  left_old > 0 || left_new > 0 {
    if (/^\+/)      { left_new--; line++
                      if ($0 ~ /(noqa|type: ignore|eslint-disable|@ts-ignore|nolint)/) {
                        print file ":" line
                      } }
    else if (/^-/)  { left_old-- }
    else if (/^ /)  { left_old--; left_new--; line++ }
    next
  }
  /^\+\+\+ /      { file = substr($0, 5); sub(/\t.*$/, "", file)
                    sub(/^"/, "", file); sub(/"$/, "", file); sub(/^b\//, "", file); next }
  /^@@ /          { split(substr($2, 2), o, ","); split(substr($3, 2), n, ",")
                    left_old = (o[2] == "" ? 1 : o[2]); left_new = (n[2] == "" ? 1 : n[2])
                    line = n[1] - 1 }
')

if [ -n "$hits" ]; then
  echo "guard no-new-suppressions: this change adds a check suppression at:"
  echo "$hits" | sed 's/^/  /'
  echo "Why: a suppression hides a finding instead of resolving it, so the check stops protecting that line."
  echo "Fix: correct the code the check reports. If the finding is wrong, stop and ask a maintainer."
  exit 1
fi
```

It expects git's default `a/` and `b/` path prefixes, so run it on output made without
`--no-prefix` or a `diff.noprefix` setting. In CI, feed it `git diff origin/main...HEAD`. Locally, against a change that adds
`# noqa: F401` it exits 1 and prints `src/b.py:1`; against a change that adds nothing of
the kind it exits 0 and prints nothing. The `/agent-diff-audit` command runs the same
class of detector, plus test-count and dependency checks, as a mechanical pass before
review; use the script above when the check has to run in CI and in tools that do not have
that command.

## Rung 5: git hook

**Can enforce.** A fast check on what is about to be committed or pushed: staged files,
the commit message, a quick scan. Feedback arrives before the change leaves the machine.

**Cannot see.** Anything on another machine. A git hook is local and client-side, a clone
does not install it, and a flag such as `--no-verify` skips it, so it is a convenience for
the contributor and never the only enforcement. Treat any rule that matters as needing a CI
twin; the hook exists to shorten the feedback loop to the same check.

**Worked example.** Keep the hook in the repository so it is reviewed like any other
code, and keep it a thin call to the same script CI runs:

```bash
#!/usr/bin/env bash
# .githooks/pre-commit: run the same diff check CI runs, on what is staged.
set -Eeuo pipefail
git diff --cached | ./guard/no_new_suppressions.sh
```

Pointing git at the directory is the registration step: `git config core.hooksPath
.githooks`. Hand that command to a human to run. Do not run it, and do not edit git
configuration, from this skill: a hook executes on every commit, so enabling one is the
decision of whoever owns the clone.

## Rung 6: agent tool hook

Claude Code and Codex support this rung. Availability and event/tool coverage depend on
the host and installed version. Keep rungs 1 to 5 as the portable default and use an
agent hook as an extra local layer; on unsupported hosts, rely on the portable rungs
and the available permission or sandbox controls.

**Can enforce.** A rule about the agent's own actions: which path it just wrote, which
command it ran. Rungs 1 to 5 see the result of a change; this one sees the act, so it is
the only rung that can notice an edit to a protected path at the moment of the edit
instead of at review.

**Cannot see.** Changes made outside the agent's tool calls, such as a person's edit or
another tool's, and any session where the hook is not registered. It runs code on every
matching action, so it is reviewed like code: read-only where possible, no network, a
bounded runtime, and nothing in its output that echoes a secret.

**What to rely on.** Check coverage, event names, exit-code behaviour and how results
reach the agent against the current [Claude Code hooks documentation](https://code.claude.com/docs/en/hooks)
or [Codex hooks documentation](https://learn.chatgpt.com/docs/hooks#tool-coverage)
before proposing a hook. Availability does not establish that one is enabled locally.

In Claude Code, hooks are configured in a settings file as a `hooks` block naming an
event, a matcher and a command, and the path in `command` is the only thing that matters:
nothing scans a `hooks` directory, so a script dropped into one never runs. A `PostToolUse`
hook fires after the tool has run, so it reports on the write rather than preventing it.

**Worked example (Claude Code).** Design the hook, then hand the registration to a human. The design is
a short specification: the event and matcher, the single script path, what the script
reads, the exact condition it flags, the message it returns, and its privileges. The
registration is the settings fragment. A settings fragment registering a `PostToolUse` hook
on `Write|Edit` looks like this:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR/scripts/hooks/guard_hook.py\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

The `timeout` is in seconds and keeps a hung script from stalling every write; confirm the
unit and the key name against the current documentation. Put the script and that fragment
in the proposal and stop. Editing the settings file is
registering a hook, which this skill does not do.

## Rung 7: permission or sandbox setting

**Can enforce.** Capability rather than behaviour: which tools an agent may call, which
paths it may write, whether it has a network, which credentials are present. A denied
action cannot happen, which no check after the fact can promise.

**Cannot see.** Intent, and anything the agent is legitimately allowed to do that is
still wrong. Permissions are blunt, so a rule that needs to distinguish a good edit to a
file from a bad one cannot be expressed here. The settings file that holds project
permissions is itself a file in the checkout; in Claude Code a managed policy outranks
every project and user setting, which is the level an agent working inside the project
cannot edit.

**Worked example.** Rule: the agent may not write to the directory holding the guard's own
configuration. A path-deny entry in the agent's permission settings expresses that
directly, spelled in the tool's own syntax, or in the tool's own sandbox or approval settings, where
it has them. Pair it with a CI check that fails any
change touching that directory, so the rule survives a session where the permission was
never applied. As with a hook, changing a permission is a human decision: propose the
entry, name the file it belongs in, and do not loosen or edit it to get a change through.

## Rung 8: instruction text

**Can enforce.** Nothing. An instruction in `AGENTS.md`, `CLAUDE.md` or a skill shapes what
the agent proposes; it cannot stop a violation, and it is the first thing lost when
context fills.

**What it is for.** The rule's reason, the judgement a check cannot make, and the pointer
to the mechanism that does the enforcing. Write the instruction after the guard exists, as
one line saying why the rule is there and where it is enforced, so an agent that reads it
can predict the failure message instead of discovering it. A rule that exists only as
instruction text is a candidate for the rungs above, not a finished guardrail.

## Choosing

Ask what the rule is about, then take the lowest rung that can see it.

| The rule is about | Lowest rung that can see it |
| --- | --- |
| The shape of data or which states are legal | Type system or compiler |
| A forbidden or required construct in the source | Linter or static rule |
| What the code does when it runs | Test |
| The whole repository or the whole change, on every contributor | CI check |
| What is about to be committed, with fast feedback | Git hook, with a CI twin |
| What the agent just did, such as the path it wrote or the command it ran | Agent tool hook where the host/version supports it, or permission |
| What the agent is able to do at all | Permission or sandbox setting |
| Judgement, taste or reasoning | Instruction text, plus review |

Three tie-breakers when two rungs both fit:

- **Prefer the rung that runs for everyone.** A guard only the agent's tool enforces leaves
  every human and every other tool unguarded, and teaches a team that the rule is about the
  agent rather than the codebase.
- **Prefer the rung that can be shown failing on a real violation.** If you cannot build a
  small input that trips it, you cannot do step 3 of the procedure, and you do not yet
  have a guardrail.
- **Pair a fast rung with an authoritative one.** A git hook or an agent hook for feedback,
  a CI check for the verdict. The fast one may be skipped; the authoritative one has to run
  where the agent cannot edit it.

Stop climbing at the first rung that expresses the rule with an acceptable false-positive
rate. Going higher spends more review effort for a check that sees less of what the lower
rung already saw, and an instruction in text is the last resort rather than the safe
default.
