# The builder's brief

## Contents

- Shape
- The commit convention
- The stop condition
- Tiers

## Shape

The brief is the plan with a frame around it. Take maker's `Steps` verbatim; add the sections around them.

```text
Goal         one or two sentences, from the frame
Success      the frame's success criterion, so the builder knows what the work is for
Steps        copied from maker, in order, unchanged:
             1. <files> - <change> - proof: <test or command>
             2. ...
Rules        one commit per step; subject starts "step N:"; run the proof before committing
Stop when    a step needs a file or change the plan does not list; a proof cannot be run;
             a step fails and the fix is not within the step
Not to touch whatever the frame put out of scope, and the tests, CI configuration and
             thresholds unless a step lists them
Done when    every step committed and its proof run; the acceptance check from the plan passes
```

The builder returns the commits and, per step, the proof's result. It does not return a narrative of why; the reasons are an argument for the diff, and the checker should not hear them first.

## The commit convention

One commit per step, `step N:` at the start of the subject, nothing else in the commit. That gives maker a one-to-one map between plan and history, makes a single step revertible, and means a divergence names a commit and not a hunk. A step that needed two commits was two steps, and a commit holding two steps hides one of them. Tell the builder to split the plan, not the other way round, and to stop and ask if the plan is the problem.

## The stop condition

Improvising is the failure this gate exists to catch, and the cheapest place to catch it is before the commit. The stop condition turns a quiet divergence into a question the main conversation sees at the moment it arises. A builder that stops and asks has not failed the gate.

## Tiers

| Role | Tier | Effort | Why |
| --- | --- | --- | --- |
| maker, plan and check | mid | medium | Ordering and comparing against a written plan is bounded work |
| builder | mid | high | Care at each step matters more than a stronger model |
| inspector | top | the agent's own setting | Judging correctness is the hard part |

Model and effort apply when an agent starts and cannot change an active session. Record what each stage actually ran at beside its report.
