---
description: Classify a failing CI run as a real failure, a flake, an infrastructure fault, a config or permission problem, or dependency drift, working from annotations rather than whole logs.
argument-hint: [run id, or blank for the latest failing run on this branch]
allowed-tools: Bash(gh:*), Bash(git:*), Read, Grep
---

Classify the failing run `$1`. If no run id was given, find the most recent failing run
for the current branch.

Check the default branch first. This is the highest-value minute in the procedure, and
skipping it is how someone spends an hour debugging a diff that never had a chance:

```bash
gh run list --branch=main --limit=20 --json conclusion,headSha,createdAt,displayTitle
```

If the default branch is also red, stop classifying this run and say so — it is a build
break, not a problem with the change under test.

Otherwise work from most-structured to least, and do not read a whole log:

```bash
gh run view "$1" --verbose                       # which step failed first
gh api repos/{owner}/{repo}/check-runs/{id}/annotations   # the pre-extracted error surface
gh run view "$1" --log-failed                    # only the failed steps
```

Land on exactly one class — real failure, flake, infrastructure, config or permission,
dependency drift — and quote the single log line that decided it. "Probably flaky but
possibly the change" is not a classification, it is a decision not yet made.

Then give the remediation at the altitude of the cause, and say explicitly whether a
re-run is safe: it is not, for any step that deploys, migrates, publishes or applies.

For the full procedure, including bisection and quarantine policy, use the `ci-triage`
skill.
