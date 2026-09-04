@AGENTS.md

## Claude Code

`AGENTS.md` above is the whole contract; this file exists because Claude Code reads
`CLAUDE.md` rather than `AGENTS.md`, and an import keeps them from drifting apart. Two
Claude-specific notes:

- The subagents in `plugins/engineering/agents/` are the intended way to do the heavy reading in this
  repository. Delegate a CI log or a Terraform plan rather than pulling it into the main
  context — that is what they exist for. `docs/writing-agents.md` explains when a
  subagent beats doing the work inline.
- Use plan mode for anything that touches `src/skillcheck/` or `.github/workflows/`.
  Those two decide whether every other change is allowed to merge, so a mistake there is
  more expensive than it looks.
