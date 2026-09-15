# Token accounting

Read this when spend cannot be attributed to a prompt path, or before computing any
break-even. Everything here is arithmetic and schema; nothing in it depends on a price,
because prices change and the arithmetic does not.

## Contents

- [The call record](#the-call-record)
- [Where to record it](#where-to-record-it)
- [Aggregating it](#aggregating-it)
- [Cost per unit of work](#cost-per-unit-of-work)
- [The four prices, and the dimensions that are not prices](#the-four-prices-and-the-dimensions-that-are-not-prices)
- [Break-even: prompt caching, and why hit rate is the wrong metric](#break-even-prompt-caching-and-why-hit-rate-is-the-wrong-metric)
- [Break-even: a cheap-model cascade](#break-even-a-cheap-model-cascade)
- [Break-even: batch](#break-even-batch)
- [Estimating before you have counts](#estimating-before-you-have-counts)
- [Traps in the numbers](#traps-in-the-numbers)

## The call record

One record per provider call, emitted by the wrapper every call goes through. If some
call sites bypass the wrapper, fix that first: an unmeasured path is the one that grows.

| Field | Type | Notes |
| --- | --- | --- |
| `ts` | timestamp | UTC. Hourly buckets are what catch a runaway the same day |
| `prompt_path` | string | Stable id per template, such as `support.triage.classify`. Version it when the template changes materially, so a before-and-after comparison is possible |
| `prompt_version` | string | The template's content hash or release tag |
| `feature` | string | The product surface a finance conversation will use |
| `tenant` | string | Account or organisation id. Hash it if that is what your privacy rules require, but keep it joinable |
| `task_id` | string | Groups every call belonging to one user-visible task, including agent steps and retries. Without it there is no cost per task |
| `step` | integer | Position within the task. Step counts are the loop's early warning |
| `model` | string | The exact dated model identifier, not the family alias |
| `input_tokens` | integer | Uncached input, as returned by the provider |
| `cache_write_tokens` | integer | Input written to cache this call, zero when not caching |
| `cache_read_tokens` | integer | Input served from cache this call |
| `output_tokens` | integer | Including reasoning tokens where the vendor bills them as output |
| `max_output_tokens` | integer | The cap in force. A path whose outputs sit at the cap is being truncated, which is a quality question as well as a cost one |
| `latency_ms` | integer | For the batch-versus-interactive decision later |
| `outcome` | enum | `ok`, `retry`, `fallback`, `refusal`, `error`, `cancelled` |
| `stop_reason` | string | As returned. `max_tokens` on a path you thought was short is a finding |

Two rules about this record. Take the token counts from the provider's response rather
than a local tokenizer — the response is what is billed, and a local count ignores
provider-side formatting, tool schemas and reasoning. And confirm the exact field names
against the provider's current API reference when you write the recorder; the names
differ between vendors and have changed over time as caching and reasoning billing were
added. What is stable is that four quantities exist and have to be kept apart.

Never log the prompt or the completion into the same stream by default. Token counts are
cheap to keep and safe to keep; prompt bodies carry customer data and turn a cost log
into a retention and privacy problem. Log content separately, sampled, with its own
retention rule, and redact request headers so an API key cannot reach the log at all.

## Where to record it

The wrapper writes the record; something else aggregates it. Any of these works, and the
choice matters less than the schema:

- A JSONL file shipped with the rest of the application logs, aggregated on read. The
  cheapest thing that works and the easiest to start with.
- A table in the operational database, written asynchronously. Best when per-tenant
  ceilings need a counter anyway (see `routing-and-budgets.md` in this directory).
- A counter and a histogram in the metrics system, with `prompt_path`, `model` and
  `feature` as labels. Keep `tenant` and `task_id` off metric labels — tenant cardinality
  multiplied by path cardinality is how an observability bill replaces the model bill.
  Those two belong on the span or the log record.

The provider's own usage console is a cross-check, not a source. It cannot see your
prompt paths, it lags, and its aggregation windows rarely line up with yours. Reconcile
against it monthly; when the two disagree by more than a few per cent, some call site is
bypassing the wrapper.

## Aggregating it

```bash
set -Eeuo pipefail

# Cost per task, worst first. The tail here is where a loop is running away.
jq -rs '
  group_by(.task_id)
  | map({
      task:   .[0].task_id,
      path:   .[0].prompt_path,
      steps:  length,
      input:  (map(.input_tokens + (.cache_read_tokens // 0)) | add),
      output: (map(.output_tokens) | add)
    })
  | sort_by(-(.input + .output))
  | .[0:20]' calls.jsonl
```

```bash
set -Eeuo pipefail

# Hourly output tokens for one path, to see when a change landed.
jq -rs --arg path "support.triage.classify" '
  map(select(.prompt_path == $path))
  | group_by(.ts[0:13])
  | map({hour: .[0].ts[0:13], calls: length, output: (map(.output_tokens) | add)})
  | .[]' calls.jsonl
```

Read both against a deploy calendar. A step change on one date is a release, a flag flip,
a prompt edit, or a model alias that moved under you. A steady ramp is accumulating
context: history that is never summarised, a retrieval index that grew, a tool list that
keeps gaining entries.

## Cost per unit of work

Per prompt path, for a period:

```text
cost = calls * (  input_tokens       * price_input
                + cache_write_tokens * price_cache_write
                + cache_read_tokens  * price_cache_read
                + output_tokens      * price_output )
```

with every token count as the mean per call over the period, and every price in the same
denominator. Check whether the vendor publishes per thousand or per million tokens before
multiplying; getting that wrong is a factor of a thousand and it is a mistake people
make.

Then divide by the denominator the business runs on. Pick one or two and publish them:
cost per request, per resolved ticket, per document processed, per active tenant per day,
per thousand classifications. The total is context; the unit is the number that says
whether an architectural change is worth funding. A rising total with a falling unit cost
is a product growing. A rising unit cost is the alarm.

Keep a per-tenant distribution as well as a mean. LLM spend is usually far more skewed
than request counts, and a plan priced on the mean loses money on the tail. The p99
tenant is also where abuse shows up first.

## The four prices, and the dimensions that are not prices

Fetch all of them for the exact model version, on the day, and write down where and when:

| Price | Applies to |
| --- | --- |
| Input | Uncached prompt tokens |
| Cache write | Tokens written into a prompt cache, at a premium over input, and commonly differing by cache lifetime |
| Cache read | Tokens served from a prompt cache, at a large discount — roughly an order of magnitude at the time of writing, and no longer a single constant across a lineup |
| Output | Generated tokens, including reasoning tokens at most vendors |

Batch endpoints apply a multiplier to these rather than having their own table. Long
context sometimes moves a request into a higher price band past a threshold; check
whether the model you use does that, because a prompt that crosses the threshold gets
more expensive per token as well as having more tokens.

Then look for the dimensions a tokens-times-price model cannot express at all. Per-session
or per-hour charges for hosted session state, data-residency multipliers, and prepaid
consumption-unit currencies that convert to tokens at a published rate all exist alongside
per-token pricing. A spreadsheet that multiplies four token counts by four prices silently
reports zero for every one of them, and the difference turns up on the invoice.

Assume the whole table moves. Within recent memory a top tier has fallen several-fold, a
published increase has been announced and then withdrawn, the cache-read multiplier has
forked per model rather than staying one number, and models have been retired out from
under callers. That is why nothing below is a number.

## Break-even: prompt caching, and why hit rate is the wrong metric

Let `P` be the input price, `W` the cache-write price as a multiple of `P`, and `R` the
cache-read price as a multiple of `P`. For a prefix used `N` times within the cache
lifetime, counting the first call as the write:

```text
uncached  = N * P
cached    = W * P + (N - 1) * R * P
```

Caching pays when `N > (W - R) / (1 - R)`, which is one write plus `(W - R) / (1 - R) - 1`
reads. Substitute today's multipliers to get the number; with a deep read discount and a
modest write premium it lands at roughly one read per write for a short-lifetime cache and
roughly two for a long-lifetime one, and vendors publishing both tiers usually state their
own break-even in exactly those terms. Recompute rather than adopting those figures.

The operational consequence is the whole point. Caching is not free to enable: at `N = 1`
the expression reduces to `W * P` against `P`, so a prefix written and never read costs
*more* than not caching, by the whole write premium, on every single call. The metric
that sees this is reads per write:

```text
reads_per_write = cache_read_tokens / cache_write_tokens      (per prompt path)
```

and it has to clear the break-even above. A hit rate — however a dashboard defines it,
and most define it as the share of calls with caching enabled or the share of prompt
tokens covered by a cache marker — can sit near 100% on a path whose reads per write is
zero. The traffic shape that produces it is ordinary: requests to one prompt path
arriving further apart than the cache lifetime. Each one writes a fresh entry at a
premium, the entry expires before the next arrives, and nobody ever reads anything.

So measure three things before enabling caching on a path, all of which are already in
the call log: the length of the stable prefix in tokens, against the model's minimum
cacheable length; the inter-arrival time per distinct prefix, against the cache lifetime;
and after enabling it, reads per write per path and per tenant.

Two refinements that change the answer. The lifetime is commonly measured from the start
of the writing request rather than the end of its response, so a slow generation consumes
part of its own window. And a hit usually refreshes the lifetime, which makes the
behaviour bimodal — a path with steady traffic stays warm indefinitely, a path below the
rate never warms at all — so an average across paths describes neither and the decision
has to be made per path.

## Break-even: a cheap-model cascade

A cascade runs the cheap model first and escalates to the expensive one when confidence
is low. With `C_cheap` and `C_exp` the cost of one call on each, and `p` the escalation
rate:

```text
cascade = C_cheap + p * C_exp
```

which beats always-expensive when `p < (C_exp - C_cheap) / C_exp`. Two corrections people
forget: escalated requests pay the cheap call as well, and they pay both latencies, so a
cascade with a high escalation rate is worse on cost *and* on the user's experience. And
`p` measured on a curated sample is always lower than `p` on production traffic — measure
it on sampled real requests, including the hard tail.

A hard split, where each step always goes to the model chosen for it, has no `p` and no
latency penalty. Prefer it when the steps are genuinely separable; keep the cascade for a
single step whose difficulty varies per request.

## Break-even: batch

Batch has no break-even to compute, only a constraint to check. The discount applies if
the work tolerates the completion window. The decision is therefore: what is the deadline
for this result, and is it comfortably longer than the window the vendor commits to,
including a failure and a resubmission? If yes, batch it; if no, do not. Check the
current window and discount in the vendor's documentation rather than assuming either.

## Estimating before you have counts

For a feature that does not exist yet, count sample prompts with the provider's
token-counting endpoint against the exact model you intend to deploy, and mark the result
as an estimate:

- Do not estimate from character counts. "About four characters to a token" describes one
  tokenizer on one kind of text, and tokenizers change between generations inside a single
  model family — one recent generation produces on the order of a third more tokens for
  identical text. A correct price table and a token count borrowed from a sibling model
  still give the wrong answer, which is how a model migration arrives with a bill nobody
  forecast.
- Token counts from a local tokenizer are low by some margin even when it is the right
  one, because they do not include the provider's message formatting, tool schemas, or
  reasoning tokens.
- Estimate output length from the schema or from a handful of sample generations at the
  cap you intend to set, not from what you hope the model writes.
- Multiply by the call volume you expect at launch, then again by the volume at ten
  times launch. The second number is the one that decides whether the design is viable.

Replace the estimate with measured counts within a week of shipping. An estimate that
survives into a budget conversation is treated as a measurement by everyone who was not
in the room when it was made.

## Traps in the numbers

- **Reasoning tokens** are billed but invisible in the response text. A path that looks
  cheap by its output and expensive on the bill is usually this.
- **A model alias that moves.** Calling a family alias rather than a dated identifier
  means the model and the price can both change without a deploy on your side.
- **Free-tier or credit expiry** makes a bill grow with no change in usage at all. Check
  before investigating anything else.
- **Retries counted as successes.** If the record for a retried call is overwritten by
  the successful one, the retry's tokens vanish from the log and stay on the bill.
- **Streaming responses whose usage block arrives at the end** are lost when the client
  disconnects early. Record what was streamed, or those calls become invisible.
- **Mean cost per call** hides everything. Read percentiles; the p99 call is where a
  context leak or a loop lives.
- **A tokenizer change across a model migration** moves token counts for identical
  traffic, so a before-and-after comparison across models is measuring two things at
  once. Compare cost per unit of work, and say which model each side was measured on.
- **Cache writes counted as cached input.** If the recorder folds writes and reads into
  one "cached" total, reads per write cannot be computed and a cache that is costing
  money is indistinguishable from one that is saving it.
