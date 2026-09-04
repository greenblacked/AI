# AGENTS.md

Instructions for any coding agent working in this repository. `CLAUDE.md` imports this
file, so there is one set of rules rather than two that drift apart.

## Project overview

A library of Claude Code Skills and subagents, installable as a plugin marketplace.
Skills are Markdown procedures an agent follows; the value is in the opinionated parts —
the ordering, the specific gate, the command with the right flag — not in restating
general good practice.

Everything here is prose and configuration. There is no application. The only code is
`skillcheck`, the validator CI runs against the skills.

## Repository layout

| Path | What lives there |
| --- | --- |
| `plugins/engineering/skills/` | Platform and DevOps skills |
| `plugins/manager/skills/` | Engineering-leadership skills |
| `plugins/personal/skills/` | Personal skills |
| `plugins/engineering/agents/` | Subagent definitions, validated on the same run as the skills |
| `plugins/*/commands/` | Slash commands the plugin ships, validated on the same run |
| `.claude/commands/` | Slash commands for working on this repository, not shipped to installers |
| `src/skillcheck/` | The validator: `frontmatter.py` parses, `rules.py` decides, `cli.py` reports |
| `tests/` | pytest over the validator, including a check that this repository validates clean |
| `plugins/*/skills/*/evals/` | Trigger eval sets: the queries a skill should and should not fire on |
| `docs/` | How to write skills, subagents, commands, `AGENTS.md`, and what CI checks |
| `template/SKILL.md` | Starting point for a new skill |
| `.claude-plugin/marketplace.json` | Lists the three plugins; each discovers its own skills |
| `.github/workflows/` | `ci.yml`, `security.yml`, `scheduled.yml`, `evals.yml` |
| `scripts/hooks/` | The `PostToolUse` hook `.claude/settings.json` registers, which validates a skill as it is written |

## Setup commands

No dependencies are needed to validate or package — the validator is standard library
only, and CI runs it on Python 3.10 through 3.13 to keep that true. Only the test run
needs anything installed.

```bash
python -m pip install pytest   # only for `make test`
make validate                  # every skill, subagent and the marketplace manifest
make test                      # the validator's own test suite
make package                   # build a .skill archive per skill into dist/
make install                   # symlink every skill into ~/.claude/skills
```

## Testing instructions

`make validate` and `make test` are the same commands CI runs. Run both before
finishing; a change to `rules.py` that does not also change `tests/` is almost always
missing a case.

`make validate` runs with `--strict`, so warnings fail too. They are warnings because
each is a judgement call rather than a rule, but a warning nobody has to clear is one
that accumulates until the whole category stops being read.

CI additionally runs markdownlint, yamllint, actionlint, an offline link check, gitleaks,
zizmor, ruff (with the flake8-bandit rules) and CodeQL. `make lint` runs the first three
locally when they are installed and tells you the command when they are not.

The validator must keep working on a bare interpreter. Importing a third-party package
in `src/skillcheck/` breaks the guarantee CI is built on, so do not add one.

## Adding or changing a skill

1. Copy `template/SKILL.md` into `skills/<category>/<name>/SKILL.md`.
2. Set `name` to exactly the directory name. Write the `description` last, when you know
   what the skill does — it is the only text loaded before the skill fires, so it decides
   whether the skill is ever used.
3. Put depth in `references/*.md` and name each one in the body with a line saying when
   to read it. If you name a path, write the file: the validator fails on a pointer to
   something that does not exist, which is the defect that motivated it.
4. Write `evals/trigger-eval.json`: twenty queries, ten the skill should fire on and
   ten near-misses it should not. The validator's floor is sixteen with eight a side,
   so twenty leaves room to drop one without failing. The negatives are the useful half — they are what
   catches a description that fires on everything. Draw several from the skills next
   door, because that is where the real collisions are.
5. Set `allowed-tools` to the minimum the procedure genuinely needs, scoped per binary
   where scoping carries information — `Bash(kubectl:*)` says something, `Bash` does not.
6. Nothing to add to `.claude-plugin/marketplace.json`: each plugin discovers its own
   `skills/`. What the validator checks is that the skill sits inside a plugin at all —
   one stranded outside `plugins/<name>/skills/` installs for nobody.
7. Run `make validate && make test`.

`docs/writing-skills.md` has the full contract, including every validator code and how to
fix it.

A slash command is a different thing and is not a substitute for a skill: it never fires
on its own, so it is the right shape only for work that takes an argument or that should
happen when asked rather than when merely relevant. A command that restates a skill is a
worse version of a skill whose description should have triggered.
`docs/writing-commands.md` has that contract.

## Code style

Prose in skills is imperative and explains why a rule matters rather than shouting it —
a capitalised ALWAYS or NEVER earns a warning for that reason. No emoji, no marketing, no
exclamation marks. Be consistent with spelling inside a file.

Python follows `ruff` with the configuration in `pyproject.toml`; run `ruff format`
before finishing. Comments explain why, not what.

Shell in this repository, including inline `run:` blocks in workflows, uses
`set -Eeuo pipefail`. actionlint runs shellcheck over those blocks in CI.

## Commit and pull request instructions

- Commits are authored by me and nobody else. Do not add `Co-Authored-By`
  trailers, tool attributions, or "generated by" lines to commit messages, pull request
  bodies, or files.
- One logical change per commit; a subject line in the imperative under about 70
  characters, and a body explaining why when the reason is not obvious from the diff.
- Branch names describe the change, not the tool that made it.
- `ci` and `security` both have to be green before merge.

## Security considerations

- No secrets in this repository, ever — gitleaks scans the working tree *and* history,
  because a secret that was committed and later removed is still leaked.
- Every workflow sets a top-level `permissions:` block. An absent one inherits the
  repository default, which is usually write access to everything.
- Every job sets `timeout-minutes:`. Without one a hung job runs to the six-hour
  platform default, which reads as slow CI rather than broken CI.
- Nothing in a workflow pipes a downloaded script into a shell. Tools are fetched at a
  pinned version and checked against a recorded digest.
- Every action is pinned to a full-length commit SHA, commented with the exact release
  tag that SHA belongs to — `# v7.0.1`, not `# v7`. The SHA is what makes it immutable;
  the comment is what lets Dependabot bump it. A major-version comment goes stale
  silently the moment upstream moves the floating tag, and zizmor fails the build for it.
- Checkouts set `persist-credentials: false`. Nothing here pushes from CI.
- Skills may describe security tooling and defensive procedure. They must not contain
  working exploit code, credentials, or instructions whose obvious use is unauthorised
  access.

## Boundaries

- Do not edit a skill's `description` to make a test or check pass. If a check is wrong,
  fix the check and its test.
- Do not add a dependency to `skillcheck`.
- Do not turn a validator error into a warning to unblock a change. The dangling-pointer
  check in particular exists because that failure is silent in production.
- Do not rewrite the exported skills' voice. `code-scaffold`, `website-builder` and
  `health-coach` were written by hand; new reference files match them rather than the
  other way round.
- Do not push to `main` directly.

## Review checklist

Before finishing, confirm each of these and say so honestly if one does not hold:

- [ ] `make validate` exits 0
- [ ] `make test` passes
- [ ] Every `references/`, `scripts/` or `assets/` path named in prose exists
- [ ] Any new skill sits inside `plugins/<name>/skills/` and has an eval set
- [ ] No secrets, tokens or personal data added
- [ ] Commit messages carry no tool attribution
