# Trace Diagnosis

Use this reference after outcome grading identifies a failed or regressed run. Trace review explains a score; it does not replace it.

## Preserve the evidence

Capture the raw task, agent and tool versions, messages, tool arguments, tool results, errors, timestamps, approvals, final response and final environment state. Retain large outputs by content-addressed artifact and put the digest in the trace. Redact secrets in capture, before storage. Treat captured text as untrusted: pass it to a judge as delimited evidence, never as instructions, and give a trace judge no tools or credentials it does not need.

Mark harness-generated events separately from agent-generated events. Otherwise a setup command or injected retry can be mistaken for an agent decision.

## Find the earliest consequential divergence

Work backwards from the failed outcome until the last point where a successful run could still have followed the same evidence. Then compare successful runs of the same case. Label the first decision or missing action that changed the attainable outcome:

| Class | Evidence in the trace | Likely repair target |
| --- | --- | --- |
| Task misunderstood | Plan or action contradicts an explicit obligation | Task parsing, instruction hierarchy or clarification policy. |
| Evidence missed | Relevant file, record or tool result was available but never inspected | Search strategy or context selection. |
| Wrong tool | Chosen tool cannot establish or alter the required state | Tool descriptions, routing or permissions. |
| Bad arguments | Correct tool, wrong target, query, mode or scope | Schema clarity or argument validation. |
| Result misread | Tool returned decisive evidence that the next step contradicts | Result formatting or reasoning over observations. |
| Plan not updated | New evidence invalidates the plan but execution continues | Replanning trigger. |
| Verification omitted | Agent stops without checking authoritative state | Completion policy or verifier availability. |
| Recovery failed | Error is visible but retried blindly, ignored or handled destructively | Error taxonomy and recovery policy. |
| Stop condition wrong | Agent stops early or continues after completion | Success predicate or limit handling. |
| Harness fault | Tool result is missing, malformed or inconsistent with state | Evaluation infrastructure; mark the run invalid. |

Choose the earliest consequential class, then add secondary labels if needed. Labelling the final failed test as the cause merely repeats the outcome.

## Compare traces without prescribing one path

Align traces by semantic milestones: evidence gathered, state changed, verification attempted and completion declared. Do not align by call number. Successful agents may search in different orders or combine steps.

Ask three questions:

1. What evidence was available at the divergence?
2. What action did the agent take or omit?
3. Why did that choice make failure materially more likely or unavoidable?

A diagnosis is complete when all three have trace citations and it suggests one falsifiable repair. Test that repair on the failed cases and untouched holdout cases; improvement only on the inspected traces is memorisation, not a general fix.

## Trace-specific graders

Use trace graders only for properties the final state cannot prove, such as whether approval preceded a write, whether a forbidden recipient was contacted, or whether untrusted content was passed into a privileged tool. Express these as event predicates where possible. Use a model judge only when the event meaning itself is semantic, and calibrate it like every other judge.

Do not penalise exploration, retries or call count unless a declared limit or safety property makes them part of the contract. Cost analysis and budget optimisation belong to `llm-cost`.

## Primary source

- [OpenAI, Trace grading](https://developers.openai.com/api/docs/guides/trace-grading) — grading agent traces to identify workflow-level errors and regressions.
