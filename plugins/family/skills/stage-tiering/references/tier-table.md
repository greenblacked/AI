# The tier table

## Contents

- What each tier means
- Why each stage sits where it does
- Where the setting lives
- Which setting wins
- Opting out

## What each tier means

Tiers are relative, so this file names none of a tool's models. Map them once, in the place your tool keeps its model aliases, and keep the mapping next to the agents.

- **Mid tier.** The capable, economical model: strong enough to read a codebase or a thread and report accurately, cheap enough to throw the reading away.
- **Top tier.** The most capable model the tool offers. Spent where the answer is the product of the stage and another stage will not redo it.
- **Effort.** How long the model reasons before it answers. Medium for stages that read and organise; the tool's default for the two that judge, raised only when a stage keeps returning shallow answers on hard input.

## Why each stage sits where it does

The question for each stage is what an error costs and who would notice it.

- **Framer, mid, medium.** It turns a request into a frame. A wrong frame is expensive, but it is checked by the person who owns the frame and again when Architect finds it unusable, which returns `NEEDS FRAME`.
- **Maker, mid, medium.** It plans the build and checks a diff against the plan. A poor plan shows up as a diverged diff or a failed Inspect, before anything ships.
- **Launcher, mid, medium.** It assesses readiness against three written things, a release path, a signal and a rollback. The gate is owned and can be waived only in writing. Raise it when the migration cannot be reversed and nobody else reads the plan.
- **Yielder, mid, medium.** It writes a retro. An error here costs the next slice a little, and the next retro corrects it.
- **Architect, top.** It names the one decision that is hard to reverse. Nothing downstream re-derives it; the build is made on it. This is where a weak model costs the most per token spent.
- **Inspector, top.** It is the independent check. A weak inspector passes defects through and nothing after it looks, since Launch assumes inspection happened.

## Where the setting lives

In the agent's own file, in its frontmatter:

```text
---
name: framer
model: <your mid-tier alias>
effort: medium
---
```

Check the file before assuming a setting applies: an agent with no `model` line inherits the main conversation's model and runs on whatever that is.

## Which setting wins

In Claude Code from v2.1.251, a subagent's model resolves in this order, first match winning: the per-invocation argument, the agent file's `model`, the `CLAUDE_CODE_SUBAGENT_MODEL` environment variable, then the main conversation's model. The frontmatter beating the environment variable is what lets the tiering survive a user who set that variable for another reason. Before that version the variable won. Other tools differ; read yours before relying on the order.

## Opting out

Three ways, from narrowest to widest:

1. **One delegation.** Pass a model in that delegation. It wins over the file for that call only.
2. **One agent.** Delete its `model` and `effort` lines. It inherits from then on.
3. **Every agent.** In Claude Code, set `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` so the environment variable takes precedence over agent files again, and set `CLAUDE_CODE_SUBAGENT_MODEL` to the one model you want.

Each of these turns the tiering off without an error. If you take one, write it down where the team will see it, because the first sign otherwise is a bill or a weak architecture note.
