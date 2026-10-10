# Divergence

## Contents

- What counts
- What is tolerated
- Recording a return to architect
- After the ruling

## What counts

A divergence is any difference between the diff and the plan that a reader of the plan would not have predicted:

- A file changed that no step lists, or a listed file left untouched.
- A step done differently from its one-line change: a different mechanism, a different interface.
- Two steps merged into one commit, or one step spread across several.
- A step missing, added or reordered so the tree no longer works after each step.
- A step with no proof run, or a proof replaced by a weaker one.
- Tests, CI configuration or thresholds changed when no step lists them.

Maker names each with the step it belongs to, so the response can be per step.

## What is tolerated

- Formatter-only changes inside a listed file, when the formatter is part of the repository's commands.
- A lockfile or generated file that the listed change regenerates by itself.
- A rename of a local variable inside a listed change.

If in doubt, it is a divergence. Maker reports; the main conversation decides what is tolerated, and a tolerated case is written down so the next check does not re-argue it.

## Recording a return to architect

The record is short, and sits with the plan:

```text
Divergence   step N: <what differs from the plan>
Cause        <why the plan could not be followed>
Returned to  architect, with the frame, the plan and this divergence
Ruling       approach holds, revert the step | approach changes, plan revised to <version>
```

The gate is satisfied by the record, not by the conversation about it. If architect rules that the approach changes, maker writes a revised plan and the build covers only the delta. The check then runs against the revised plan.

## After the ruling

- **Approach holds:** revert the divergent commit and rebuild the step from the plan, then check again.
- **Approach changes:** revised plan, delta build, check against the revised plan, then inspector.
- **Architect returns `NEEDS FRAME` or `BLOCKED`:** the run leaves this gate; `family-relay` routes it.

A second `DIVERGED` on the same step is not another round with architect. It goes one stage further back, as `family-relay` sets out.
