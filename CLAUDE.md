@AGENTS.md

## Claude Code

`AGENTS.md` above is the whole contract; this file exists because Claude Code reads
`CLAUDE.md` rather than `AGENTS.md`, and an import keeps them from drifting apart. Five
Claude-specific notes:

- The subagents under `plugins/*/agents/` are the intended way to do the heavy reading in this
  repository. Delegate a CI log or a Terraform plan rather than pulling it into the main
  context — that is what they exist for. `docs/writing-agents.md` explains when a
  subagent beats doing the work inline.
- For a change to this repository, `/ship` runs `explorer` — beside `investigator` in
  parallel when the change rests on an outside claim — then `implementer`, then
  `reviewer`, all from `.claude/agents/`: survey what already exists, write it and run
  the gates, judge the result on a fresh context with no editing tools, then open and
  merge one pull request once review, `ci` and `security` pass. Each runs on the tier its
  stage needs. Use it for anything more than a one-line edit, and keep the decision about
  what to write in the main conversation — that is the part that depends on the session
  and does not survive a cold prompt.
- Use plan mode for anything that touches `src/skillcheck/` or `.github/workflows/`.
  Those two decide whether every other change is allowed to merge, so a mistake there is
  more expensive than it looks. Enter it in the main conversation before delegating, and
  leave it before the first delegation to `implementer` — a subagent inherits the
  permission mode, so an `implementer` delegated while plan mode is still on would be
  read-only and could not write. The survey stage that delegates to `explorer` and
  `investigator` runs inside that same plan mode, before any brief exists to approve —
  which costs no editing, since neither agent holds an editing tool to lose — though a
  non-read-only command such as `make validate` may still prompt.
- The models follow `.claude/agents/`, not the Codex split in `AGENTS.md`: Sonnet at
  medium effort researches (`explorer`, `investigator` — `/ship` runs two of these in
  parallel, `explorer` and `investigator` when the change rests on an outside claim,
  otherwise two `explorer`s on disjoint questions), Sonnet at high effort implements
  (`implementer`), Fable reviews (`reviewer`). When a model or effort changes, change the
  agent's `model:` or `effort:` line, this sentence, and `docs/writing-agents.md`'s tier
  tables together. Claude Code's documentation says an agent file change applies from
  the next delegation without a restart; in a cloud session a newly added file has been
  seen to take a while to appear, so if an agent is not found yet, check again later or
  start a new session. The Agent tool has no per-call effort either way.
- Review guidance lives in `AGENTS.md`'s Review guidelines section and, for the managed
  GitHub code review, in `REVIEW.md`. The local `/code-review` command reads `CLAUDE.md`
  as project context but not `REVIEW.md`, so run it with `REVIEW.md`'s severity
  redefinition and skip rules in mind rather than assuming it applies them for you.
