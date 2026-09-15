# Routing and budgets

Read this when planning a split between a cheap and an expensive model, or when building
the ceilings that stop one request, one task or one tenant from spending without bound.
Model capabilities and prices both move, so nothing here names a model or a figure: it is
the procedure for deciding with today's numbers and the controls that hold whatever you
decide.

## Contents

- [Classify the steps before comparing models](#classify-the-steps-before-comparing-models)
- [Build the eval set from production](#build-the-eval-set-from-production)
- [State the bar before you run the comparison](#state-the-bar-before-you-run-the-comparison)
- [Hard split, cascade, or neither](#hard-split-cascade-or-neither)
- [Fallbacks are a routing decision too](#fallbacks-are-a-routing-decision-too)
- [The wrapper that enforces ceilings](#the-wrapper-that-enforces-ceilings)
- [Choosing degrade, queue or refuse](#choosing-degrade-queue-or-refuse)
- [Spend alerts that arrive in time](#spend-alerts-that-arrive-in-time)
- [Agent loop caps](#agent-loop-caps)
- [Retry policy](#retry-policy)
- [Rolling a routing change out safely](#rolling-a-routing-change-out-safely)

## Classify the steps before comparing models

A pipeline is not one decision. Break it into steps and label each by what it requires:

| Step type | Examples | Usual answer |
| --- | --- | --- |
| Mechanical | Reformatting, field extraction against a fixed schema, deduplication, language detection | Often no model at all — a parser or a regex is free and deterministic |
| Classification | Intent, routing, sentiment, triage, relevance filtering, safety pre-checks | Small model, measured against a labelled set |
| Retrieval-shaped | Query rewriting, reranking, summarising one passage | Small model, or a dedicated embedding or reranking model |
| Judgement | Ambiguous cases, conflicting evidence, multi-constraint planning, trade-off explanations | Large model |
| User-visible prose | Anything a customer reads verbatim | Large model, unless measured otherwise |

Doing this first commonly removes calls entirely, which is a larger saving than any
routing change: the cheapest token is the one not generated, and a surprising share of
production LLM calls are doing work a function could do.

Route on the step, not on the input. Prompt length is not difficulty; routing on it
produces a system whose behaviour changes when a user pastes a long signature block.

## Build the eval set from production

- Sample from real traffic over a period long enough to include the weekly shape, not
  from examples someone wrote to demonstrate the feature.
- Stratify: include the hard tail deliberately — the long inputs, the ambiguous cases,
  the tenants with unusual data, the languages you did not design for.
- A few hundred cases, labelled, is the working minimum for a routing decision. Twenty
  hand-picked examples measure the examples.
- Label the outcome that matters, which is rarely "good answer": the extracted field, the
  correct route, whether a human had to intervene, whether the user asked again.
- Keep the set versioned beside the prompt, and re-score it when either changes.

If no such set exists for the path you want to make cheaper, building it is the first
deliverable and it is not optional. The alternative is a change whose quality effect is
discovered by customers.

## State the bar before you run the comparison

Write the acceptance criterion down, with its tolerance, before seeing any results. A bar
chosen afterwards is chosen to fit the answer you already like.

```text
Step:        support.triage.classify
Metric:      macro F1 over the 7 intent labels
Bar:         within 1.0 point of the current model, no single label below 0.80
Guardrails:  refusal rate not higher; p95 latency not higher; escalation to human not higher
Sample:      612 labelled production cases, stratified by tenant size
Decision:    switch if the bar and all guardrails hold; otherwise keep and record the gap
```

The guardrails are the part people skip and the part that catches the expensive failure:
a cheaper model that is equally accurate but refuses more often, or that is accurate and
slower, has moved the cost somewhere the model bill cannot see. Count the downstream
consequences in the comparison — a retry, a human escalation and a support ticket all
have a price, and any of them can be larger than the inference saving.

## Hard split, cascade, or neither

A **hard split** sends each step to the model chosen for it. Prefer it: no escalation
rate to measure, no double payment, no added latency, and the behaviour is easy to
reason about.

A **cascade** runs the cheap model first and escalates on low confidence. It fits a
single step whose difficulty varies per request. It costs both models on every escalated
request and adds the cheap model's latency to those, so it pays only when the escalation
rate is low — the arithmetic is in `token-accounting.md` beside this file. Two
requirements: a confidence signal that actually predicts correctness, validated on the
eval set, and a measured escalation rate on production traffic rather than on a curated
sample.

**Neither** is the answer when the step is mechanical (remove the call), when the volume
is too low for the saving to matter (spend the effort elsewhere), or when the cheap model
misses the bar and the gap is not closable by prompting.

Fine-tuning or distilling a small model onto a narrow step is the next lever when a split
fails its bar. Price the training runs, the labelled data, the re-evaluation on every
base-model change, and the operational burden of another artefact to version — then
compare that against the inference saving over a realistic horizon.

## Fallbacks are a routing decision too

A fallback path that promotes to a larger or costlier model on any error is a standing
invitation to a surprise bill: one bad hour upstream, one rate limit, one malformed
response, and every request is taking the expensive route. Cap it explicitly.

- Fall back on availability errors only, not on quality judgements.
- Put a rate limit on the fallback path itself, so it cannot become the main path.
- Emit a metric for fallback share and alert when it crosses a few per cent.
- Record `outcome: fallback` on the call so the cost report can separate it.

## The wrapper that enforces ceilings

Every provider call goes through one wrapper. That is the only place a ceiling can be
enforced, the only place a call record can be guaranteed, and the thing that makes every
later change a single edit.

```text
call(prompt_path, messages, *, task_budget, tenant):
    reject if estimated_input_tokens > path.max_input
    reject if task_budget.spent >= task_budget.limit
    reject if tenant_spend_today(tenant) >= tenant.daily_limit
    set max_output_tokens = path.max_output          # never unset
    set timeout            = path.timeout
    response = provider.call(...)                    # key read from the environment
    record(usage, prompt_path, tenant, task_id, step, outcome)
    task_budget.spent += cost(usage)
```

Details that matter:

- The output cap is set on every path. A path without one has no upper bound on what one
  call can spend.
- The estimate before the call uses a local tokenizer and is deliberately conservative;
  it exists to refuse an obviously oversized request before paying for it.
- The credential is read from the process environment or a secret manager. It never
  appears in a command-line argument, a URL, a log line or an error message — argument
  lists are visible to any process on the host and logs outlive the incident.
- Counters for tenant and task spend need to be shared across processes; a per-process
  counter enforces nothing behind a load balancer.

## Choosing degrade, queue or refuse

Decide per feature, in advance, and write it in the runbook with the exact user-facing
message.

| Feature shape | Behaviour at the ceiling | Notes |
| --- | --- | --- |
| Has a cheaper form: smaller model, less context, a heuristic, a cached answer | Degrade | Say it is reduced. A silently degraded answer presented as a full one is worse than a refusal |
| Batch or background work | Queue | Return an acknowledgement and an expected time; drain when the window resets |
| Correctness-critical, or spend that looks like abuse | Refuse | An explicit, explained error with a path to a human |
| Free-tier or trial traffic | Refuse or degrade, by plan | This is where a ceiling earns its keep; make the limit visible in the product |

Three rules regardless of choice. The behaviour is exercised in a test, because an
untested exhaustion path is a stack trace in a user's face. The message is written by
someone who writes product copy, not generated at 02:00. And the ceiling itself is
adjustable without a deploy, so raising it deliberately during an incident is one action
rather than a release.

## Spend alerts that arrive in time

A monthly budget threshold notifies you after the money is gone. Alert on rate:

- Spend per hour per feature against the same hour last week, alerting on a multiple.
- Tokens per task, p99, per prompt path — the first place a loop regression shows.
- Reads per write on every path that has caching enabled, alerting when it falls below
  the break-even — that is the point at which caching has started costing money.
- Fallback and retry share.
- Cost per unit of work, tracked weekly, reviewed like any other unit economic.

Route to the team that owns the path, with the prompt path in the alert payload, and give
each alert a documented response. `alert-design` covers why an alert with no action
decays exactly like an unactioned page, and `instrumentation` covers how to emit these
without a cardinality explosion — keep `tenant` and `task_id` off metric labels and on
spans.

## Agent loop caps

Every one of these is a hard stop with a defined outcome, not a warning:

| Cap | Why |
| --- | --- |
| Max steps per task | The basic bound. Choose it from the p99 of successful tasks, not from the maximum ever seen |
| Max total tokens per task | A step cap alone does not bound spend; one step can carry an enormous context |
| Max cost per task | The bound a finance conversation understands, and the only one that survives a price change |
| Max wall clock per task | Catches a loop that is slow rather than large |
| No-progress detector | The same tool call with the same arguments twice, or a repeated assistant turn, means it is not converging |
| Max fan-out | Sub-agents multiply context; bound both the count and the context each receives |
| Per-step context ceiling | Summarise or drop old tool output rather than carrying everything forward |

When a cap trips, return the partial result with an explicit statement that the task was
stopped, and record it as an outcome so the rate is visible. A cap that silently returns
a plausible answer is how a truncated agent run becomes a wrong answer nobody questions.

Tool results are usually the largest contributor to loop growth. A tool that can return
megabytes should return a summary plus a handle the agent can use to fetch a slice, which
is the same discipline that makes a subagent worth using in the first place.

## Retry policy

A retried call pays for the whole input again, so retries are a cost control as much as a
reliability one.

- Cap attempts, and use exponential backoff with jitter. A retry storm against a rate
  limit is both expensive and counterproductive.
- Retry only what can plausibly succeed on a second attempt: a timeout, a rate limit, an
  overloaded or unavailable response, a truncated stream.
- Do not retry a deterministic failure — a schema violation, a content refusal, a
  context-length error. It will fail identically and be billed identically. Fix the input
  or fail the request.
- On a schema violation, repair the request before retrying: ask for the missing field
  alone rather than regenerating the whole response.
- Count retries separately in the cost report, per path. A retry rate that doubled is a
  cost regression and usually an upstream reliability signal too.
- Watch the combination: a retry inside a step inside a fan-out multiplies three ways.
  Bound the product, not just each factor.

## Rolling a routing change out safely

1. Shadow first where you can: run the cheap model alongside the current one on a sample
   of live traffic, log both, serve the current one. This measures the real escalation or
   disagreement rate with no user risk.
2. Ramp by percentage, holding the guardrail metrics from the bar, not just the cost
   metric.
3. Keep the switch a runtime flag. A routing change that needs a deploy to revert will be
   left in place through the incident it caused.
4. Re-run the eval set on any base-model change, alias move or prompt edit. A routing
   decision is measured against a model version, and it expires when that changes.
   Re-price it at the same time: the split was chosen against one price table, and both
   the prices and the tokenizer can move with the model, so a decision that was correct
   in March can be inverted by June without anything in your code changing.
5. Record the decision, the bar, the measured result and the date. The next person to ask
   "why is this step on the expensive model" deserves the number rather than an opinion.
