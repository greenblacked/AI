# Evaluation Design

Use this reference to turn an agent task collection into a reproducible comparison and release gate.

## Dataset record

Store one immutable manifest per dataset version. Each case needs:

| Field | Purpose |
| --- | --- |
| `case_id`, version and source lineage | Keeps results joinable and prevents related variants crossing splits. |
| Task text and adjudication note | Separates the user request from clarifications applied to every run. |
| Initial snapshot and setup command | Recreates the exact starting state. |
| Allowed and forbidden effects | Makes tool safety and scope machine-checkable. |
| Grader ids and versions | Shows which definition of success produced the result. |
| Tags | Supports task-family, risk, tool and difficulty slices. |
| Split | Development, regression or sealed holdout. |

Version any semantic change to a task, fixture, rubric or grader. Keep old results attached to their old version rather than silently recomputing history under a new definition.

## Grader ladder

Prefer the first grader that can establish the property:

| Property | Preferred grader | Common mistake |
| --- | --- | --- |
| Exact required value or identifier | Exact or structured-field comparison | Using a judge for equality. |
| Repository remains buildable | Build, test, typecheck or lint exit plus relevant assertions | Trusting the agent's report of success. |
| Required change exists | Behavioural test, schema validator or state query | Comparing with one golden diff. |
| Forbidden scope or effect | Diff allowlist, audit event or before/after state check | Searching only the final response for an admission. |
| Explanation quality | Rubric-bound human or calibrated model judge | Asking whether the answer is "good" without criteria. |

Exact-match checks are appropriate only when exactness is the contract. OpenAI's eval guidance documents exact string checks alongside model graders and recommends representative test data with human-provided ground truth. Use that separation: executable properties remain deterministic; judgement is reserved for semantic properties.

## Judge calibration record

For each rubric or judge revision, retain:

- the frozen calibration examples and independent human labels;
- criterion-level judge labels and rationales;
- agreement, false-accept and false-reject counts;
- disagreements adjudicated by a domain reviewer;
- the judge model, prompt and parameters;
- the task slices represented and absent.

Calibration is local to the rubric and distribution. Agreement on support summaries does not validate the same judge for code correctness or irreversible tool actions.

## Release-gate worksheet

Fill this before running the candidate:

```markdown
Candidate:
Baseline:
Dataset and holdout version:
Trials per case:
Primary outcome and allowed regression:
Critical slices and minimums:
Severe violations that force a hold:
Maximum invalid-run rate:
Judge-only decisions requiring review:
Decision owner:
```

When a gate fails, preserve the run and explain the failing clause. Changing the gate creates a new decision, so record the reason and rerun baseline and candidate under it.

## Primary sources

- [OpenAI, Working with evals](https://developers.openai.com/api/docs/guides/evals) — representative test data, human ground truth and deterministic string checks.
- [Anthropic, Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — agent evaluation design, graders, trials and evaluation harnesses.
