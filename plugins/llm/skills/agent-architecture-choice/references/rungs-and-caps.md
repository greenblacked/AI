# Rungs and caps

## Contents

- Before leaving rung one
- Workflow patterns
- Cap template
- Approval tiers

## Before leaving rung one

Failures that look like a need for more structure are often fixed cheaper:

| Symptom | Try first |
| --- | --- |
| Wrong or missing facts | Retrieval or supplying the data in the prompt |
| Format errors | Structured output with a schema |
| Misses a rule | A clearer instruction and two or three worked examples |
| Reasoning slips | Allowing reasoning before the answer, or a stronger model |
| Too many instructions at once | Splitting into a fixed chain of two prompts (this is already rung two) |

Record what was tried and the measured effect on the task set, so the climb is traceable.

## Workflow patterns

| Pattern | Use when | Control flow in code |
| --- | --- | --- |
| Prompt chain | A task decomposes into ordered steps and each is easier alone | Step output passes through a validation gate to the next |
| Router | Inputs fall into distinct kinds needing different handling | Classify, then dispatch by label; see `llm-classifier-design` |
| Parallel fan-out | Subtasks are independent, or several votes raise reliability | Run concurrently, merge by rule |
| Evaluator-optimiser | A clear quality criterion exists and revision helps | Generate, critique, revise, with a fixed round cap |

Each step is a single call with its own tests. Where a step needs a lookup, call the tool from code and pass the result in.

## Cap template

```yaml
max_steps: 12            # model turns
max_tool_calls: 20
max_input_tokens_total: 200000
max_wall_clock_seconds: 120
max_cost_per_task: 0.50  # in the billing currency, enforced from usage counters
on_exhaustion: return_partial_with_reason   # or escalate_to_person
```

The numbers are examples; set them from the 95th percentile of successful runs on the task set plus headroom, and alert when runs approach them. The harness counts usage from API responses, not from the model's own claims. Tool results that are large should be shaped before they enter the loop (see `tool-result-shaping`) and long loops need a compaction plan (see `context-compaction`).

## Approval tiers

| Tier | Examples | Rule |
| --- | --- | --- |
| Read-only | Search, fetch, list | Run without approval, log the call |
| Reversible write | Create a draft, add a label | Run, log, and make undo possible |
| Irreversible or external | Send email, charge, delete, deploy | Pause for a person's approval with the exact action shown |

Assign every tool to a tier when it is added. A tool that mixes tiers should be split.
