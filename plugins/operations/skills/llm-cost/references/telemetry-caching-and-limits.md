# Telemetry, caching and limits

Read this when wiring token usage into OpenTelemetry, when turning provider usage fields
into a cost record, when a cache, batch or retry policy needs the provider's actual numbers
rather than the symbolic ones in `token-accounting.md`, or when putting a gateway budget in
front of several callers. The other references keep every multiplier symbolic on purpose.
This one names the figures the Anthropic and OpenTelemetry documentation publish, because
the traps are in the details: which field excludes cached tokens, which 429 must not be
retried, which spend limit returns a 400.

Every figure below was read from the source named beside it on 2026-10-19. Prices,
multipliers, minimums and limits change, in both directions and without a deploy on your
side. Treat each number as a value to re-check on the day you use it, and write the fetch
date next to the number you carry into an analysis.

## Contents

- [OpenTelemetry GenAI conventions and their status](#opentelemetry-genai-conventions-and-their-status)
- [Mapping provider usage onto the attributes](#mapping-provider-usage-onto-the-attributes)
- [Anthropic usage accounting](#anthropic-usage-accounting)
- [Caching multipliers, lifetimes and breakpoints](#caching-multipliers-lifetimes-and-breakpoints)
- [Batch discount and limits](#batch-discount-and-limits)
- [Rate limits and what each 429 means](#rate-limits-and-what-each-429-means)
- [Spend limits at the provider](#spend-limits-at-the-provider)
- [Gateway budgets](#gateway-budgets)

## OpenTelemetry GenAI conventions and their status

Source: the `open-telemetry/semantic-conventions-genai` repository, which the main
semantic-conventions repository now points to for everything GenAI (its `docs/gen-ai/`
pages are stubs that say the conventions have moved). The pages read were `README.md`,
`gen-ai-spans.md`, `client-inference.md`, `gen-ai-token-metrics.md` and `anthropic.md`
under `docs/gen-ai/`.

**Stability.** The GenAI document set, its spans and its metrics are marked Development,
not Stable, and so is every `gen_ai.*` attribute I read in them. Only attributes borrowed
from the core conventions, such as `server.address`, `server.port` and `error.type`, are
marked Stable. In practice this
means names and shapes can still change between releases, and a dashboard or alert built on
a metric name is built on something that has already been renamed once.

**The rename that matters.** An earlier revision (v1.37.0 of the main repository) defined
one histogram, `gen_ai.client.token.usage`, with a required `gen_ai.token.type` attribute
(`input` or `output`). The current text does not define that name. It defines instead:

| Instrument | Type | Use it for |
| --- | --- | --- |
| `gen_ai.client.inference.usage.input_tokens` | Counter | Spend: input tokens including cached ones |
| `gen_ai.client.inference.usage.output_tokens` | Counter | Spend: output tokens |
| `gen_ai.client.inference.usage.cache_read.input_tokens` | Counter | A subset of the input counter |
| `gen_ai.client.inference.usage.cache_write.input_tokens` | Counter | A subset of the input counter |
| `gen_ai.client.inference.usage.reasoning.output_tokens` | Counter | A subset of the output counter |
| `gen_ai.client.inference.operation.input_tokens` and `.output_tokens` | Histogram | Percentiles per call, never totals or cost |

The text says the usage counters track consumption over time and "serve as a proxy for
cost approximation", and that the per-operation histograms "should not be used for total
usage or cost calculations". Take cost and unit cost from the counters or from your own
call log. Take p95 and p99 tokens per call from the histograms. Which names your
instrumentation library emits depends on its version, so look at what actually arrives in
the collector before building a panel; the same dashboard can see the old name from one
service and the new names from another.

**Opting in to the new shapes.** The earlier revision's transition note said existing
instrumentations should keep emitting the old conventions by default and offer an
`OTEL_SEMCONV_STABILITY_OPT_IN` value, `gen_ai_latest_experimental`, to emit the latest. Whether a given
library implements that switch is a property of the library. Check its documentation, and
pin the library version so a dependency bump does not silently rename a metric.

**Spans.** An inference span is a `CLIENT` span named `{gen_ai.operation.name}
{gen_ai.request.model}`, with `gen_ai.operation.name` and `gen_ai.provider.name` required.
For Anthropic the provider name is `anthropic`. The convention says the span should cover
the logical operation including automatic retries, so one span can hide several billed
attempts; keep the retry count on the call record. Agent work uses further operation
names: `invoke_agent`, `execute_tool`, `plan`, `retrieval` and others, all Development as
well. `gen_ai.conversation.id` ties the calls of one conversation together, which is the
span-side counterpart of the `task_id` field in `token-accounting.md`.

**Content stays out by default.** Prompt and completion bodies (`gen_ai.input.messages`,
`gen_ai.output.messages`, `gen_ai.system_instructions`, `gen_ai.tool.definitions`) are
Opt-In attributes, and the text warns they may contain sensitive information, user data
included. For related
attributes the conventions give an environment variable named
`OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` as an example of the opt-in gate.
Leave content capture off in the default telemetry pipeline and enable it per environment
with a retention limit, because a span store outlives the incident that justified turning
it on.

**Cardinality.** The usage counters carry operation, provider, model and modality. Keep
`tenant`, `task_id` and user identifiers on spans and in the call log, not as metric
attributes on these counters, for the reason `routing-and-budgets.md` gives. Per-path cost
comes from joining the call log, not from a metric with an unbounded label.

## Mapping provider usage onto the attributes

This is the trap with the largest effect on a number. The OpenTelemetry attribute
`gen_ai.usage.input_tokens` is defined to include cached tokens: it "SHOULD include all
types of input tokens, including cached tokens". Anthropic's `usage.input_tokens` does the
opposite, and the Anthropic page of the conventions says so: "Anthropic `input_tokens`
excludes cached tokens", with the computation spelled out. Copying the provider field
straight across reports a cached prompt as a few dozen tokens.

```python
def to_genai_attributes(usage: dict) -> dict:
    """Map an Anthropic Messages usage block to GenAI span attributes."""
    fresh = usage.get("input_tokens", 0)  # only tokens after the last breakpoint
    read = usage.get("cache_read_input_tokens") or 0
    write = usage.get("cache_creation_input_tokens") or 0
    attrs = {
        "gen_ai.usage.input_tokens": fresh + read + write,
        "gen_ai.usage.output_tokens": usage.get("output_tokens", 0),
    }
    # The cache attributes are Recommended when available and non-zero.
    if read:
        attrs["gen_ai.usage.cache_read.input_tokens"] = read
    if write:
        attrs["gen_ai.usage.cache_write.input_tokens"] = write
    return attrs
```

The cache attributes are subsets of the total, so a cost query that adds all three of
total, read and write double counts. Compute the uncached share as total minus read minus
write, then price each part at its own rate. The conventions also say that when a system
reports both used and billed tokens, instrumentation must report the billed ones, which
matters for any provider whose response carries both.

## Anthropic usage accounting

Source: the prompt-caching page of the Claude API documentation ("Tracking cache
performance" and the FAQ), 2026-10-19.

- `input_tokens` is the count of tokens after the last cache breakpoint, not all input.
- `cache_creation_input_tokens` is tokens written to the cache by this request.
- `cache_read_input_tokens` is tokens served from the cache.
- Total input is the sum of the three. The documentation's example is 100,000 read, 0
  written and 50 fresh, for 100,050 processed.
- With a 1-hour lifetime in use, the response also carries a `cache_creation` object with
  `ephemeral_5m_input_tokens` and `ephemeral_1h_input_tokens`, and the older total field
  equals their sum. Record the split, because the two writes are priced differently.
- If both cache fields are 0 on a prompt you marked cacheable, nothing was cached. The
  documentation names the minimum length as the likely cause.
- The fields sit in `usage` on the response, or in the `message_start` event when
  streaming. Confirm against the streaming reference which event carries the final output
  count before relying on one event for it.

Two further consequences for cost records. Thinking blocks cannot be marked with
`cache_control`, but when they appear in earlier assistant turns they can be cached with
the rest of the content and then count as input tokens on a read. And a server-side tool
such as web search can produce 5-minute writes you did not request, so a cost record that
assumes every write came from your own breakpoints will not reconcile.

## Caching multipliers, lifetimes and breakpoints

Source: the prompt-caching page, "Pricing", "Cache limitations", "Explicit cache
breakpoints" and "1-hour cache duration" sections, and the pricing page's prompt caching
section, 2026-10-19. Re-fetch before use.

**Multipliers on the base input price.**

| Item | Multiplier |
| --- | --- |
| 5-minute cache write | 1.25 |
| 1-hour cache write | 2 |
| Cache read, standard | 0.1 |
| Cache read, a few current models | 0.05 or 0.025 |

The 0.05 and 0.025 reads are per-model exceptions called out in footnotes to the pricing
table on the date above, which is the "read multiplier has forked" point in `SKILL.md`
made concrete. The documentation states these stack with the batch discount, with
long-context pricing and with data residency, and that for a model priced by prompt
length, cache reads and writes count toward the prompt length that selects the band.

**Break-even from those multipliers.** Using `N > (W - R) / (1 - R)` from
`token-accounting.md`, where `N` counts the writing call:

| Write | Read | Threshold | Whole calls needed | Reads per write |
| --- | --- | --- | --- | --- |
| 1.25 | 0.1 | 1.28 | 2 | 1 |
| 2 | 0.1 | 2.11 | 3 | 2 |
| 1.25 | 0.025 | 1.26 | 2 | 1 |
| 2 | 0.025 | 2.03 | 3 | 2 |

The read multiplier barely moves the answer, because the write premium dominates it. What
moves it is the lifetime you pay for: a 1-hour write earns its premium only when the
prefix is read at least twice within the hour, and a 5-minute write only when something
reads it again inside the window. This is why the reads-per-write ratio, not the read
discount, decides whether caching pays.

**Lifetime.**

- The default lifetime is 5 minutes, and a read refreshes it at no extra charge.
- The lifetime runs from the start of the request that wrote or read the entry, not from
  the end of its response. The documentation's example: a 4-minute stream leaves about one
  minute for a follow-up to start.
- The 1-hour option is requested with `"ttl": "1h"` inside `cache_control`. Use it when
  requests for a prefix arrive less often than every 5 minutes but more often than hourly,
  or when responses are long. For traffic that arrives more often than every 5 minutes the
  documentation says to stay on the 5-minute lifetime, since it refreshes for free.
- In one request, 1-hour entries must come before 5-minute entries. Billing then splits the
  prompt into read tokens up to the highest hit, 1-hour writes up to the last 1-hour
  breakpoint, and 5-minute writes after that.
- A cache entry becomes available only after the first response begins. Parallel
  requests that need a shared prefix should wait for the first response, or they all
  write it.
- There is no way to clear the cache manually.
- Caches are isolated per workspace on the Claude API, Claude Platform on AWS and
  Microsoft Foundry, and per organisation on Bedrock and Google Cloud. Splitting tenants
  across workspaces therefore splits their caches, and reads per write has to be measured
  per workspace.

**Minimum cacheable length.** On the date above the published minimums ranged from 512 to
4,096 tokens depending on the model, and were not ordered by tier. A shorter prompt is
processed uncached with no error. Look up the figure for the exact model in the "Cache
limitations" section rather than reasoning from the family.

**Breakpoints.**

- Up to 4 explicit breakpoints per request. Breakpoints themselves cost nothing; only
  tokens written and read are charged.
- Prefix order is tools, then system, then messages. A write happens only at a breakpoint,
  so a breakpoint placed on a block that changes every request (a timestamp, the incoming
  message) writes a fresh entry each time and never reads one. Put it on the last block
  that stays identical across requests.
- A read looks backwards from the breakpoint for an entry an earlier request wrote, over
  a window of 20 blocks. A conversation that adds 20 or more blocks between requests
  falls outside the window with no error, so add a second breakpoint closer to the
  earlier write before you need it. A run of consecutive `tool_use` blocks counts as one
  position, and so does a run of consecutive `tool_result` blocks.
- Top-level automatic caching (`cache_control` on the request) takes one of the 4 slots
  and moves its breakpoint to the last cacheable block each turn. It is the right default
  for a growing conversation and the wrong one for a prompt whose last block varies, for the
  reason in the second point.
- Changing tool definitions invalidates everything. Toggling web search or citations
  invalidates system and messages. Changes to `tool_choice`, images, thinking settings and
  the effort setting invalidate the message blocks, and on some models also the system
  and tool caches. The documentation also warns that Swift and Go randomise key order when
  serialising, which silently breaks a cache.
- The documentation describes a cache diagnostics feature that compares consecutive
  requests and reports where the prefix diverged. Use it before reading hashes by eye.

## Batch discount and limits

Source: the batch-processing page of the Claude API documentation and the rate-limits
page, 2026-10-19.

- All usage in a batch is charged at 50% of standard prices, input and output alike. It
  stacks with caching, but fast mode is not available with batch.
- A batch is limited to 100,000 requests or 256 MB, whichever comes first.
- Most batches finish within an hour. The hard window is 24 hours; a request not sent to
  the model by then is `expired`. Demand can slow processing and raise the number of
  expiries.
- Results can be downloaded for 29 days from creation, measured from creation and not from
  completion.
- `errored`, `canceled` and `expired` results are not billed. Only `succeeded` ones are,
  so a cost record built from submitted counts overstates the bill; build it from results.
- Each request needs `max_tokens` of at least 1. `max_tokens: 0` cache pre-warming is not
  supported inside a batch.
- Cache hits inside a batch are best effort. The documentation says users typically see
  hit rates from 30% to 98% depending on traffic, and suggests identical `cache_control`
  blocks in every request, a steady stream of requests and, because batches can take
  longer than 5 minutes, the 1-hour lifetime for shared context.
- Batches have their own rate limits: a requests-per-minute limit on the batch endpoints
  and a ceiling on batch requests waiting in the queue, which is 200,000 on the Start
  tier, 300,000 on Build and 500,000 on Scale. The per-batch ceiling is 100,000 on all
  three.
- Batches "may go slightly over" a workspace spend limit because of concurrent
  processing. A spend limit is therefore not a precise ceiling for batch work; size the
  batch against the remaining budget before submitting it.

## Rate limits and what each 429 means

Source: the rate-limits and errors pages of the Claude API documentation, 2026-10-19.

**The limiter.** Limits are requests per minute, input tokens per minute (ITPM) and output
tokens per minute (OTPM) for each model class, enforced as a token bucket: capacity is
replenished continuously up to the maximum rather than reset at fixed intervals. A limit of
60 requests per minute may be enforced as one per second, so a short burst can trip it
while the minute average is well inside. A sharp rise in traffic can also trigger
acceleration limits, which return 429; ramp up gradually.

**What counts.**

- ITPM counts `input_tokens` and `cache_creation_input_tokens`. For most models
  `cache_read_input_tokens` does not count. The documentation's example: 2,000,000 ITPM at
  an 80% cache hit rate processes about 10,000,000 input tokens per minute. The same table
  footnotes name a model that does count cache reads, so read the row for yours.
- ITPM is estimated when the request starts and adjusted as it runs.
- OTPM counts tokens actually generated. `max_tokens` is not part of the calculation, so
  lowering it does not buy rate-limit headroom. It remains the cost and latency ceiling
  described in `SKILL.md`.
- Rate limits are shared across `inference_geo` values.

**Headers to read.** `retry-after` gives seconds to wait, and earlier retries fail. The
`anthropic-ratelimit-requests-*`, `-input-tokens-*` and `-output-tokens-*` families give
limit, remaining and reset time (RFC 3339). The remaining token counts are rounded to the
nearest thousand, and the combined `anthropic-ratelimit-tokens-*` headers show whichever
limit is most restrictive at that moment, a workspace limit included. A client that paces
itself on the remaining and reset values avoids most 429s, and costs one header read.

**Classify before retrying.**

| Response | Meaning | Retry? |
| --- | --- | --- |
| 429 with `retry-after` | A rate limit or acceleration limit | Yes, after at least that many seconds, with jitter |
| 429, `error.details.error_code` of `enforced_spend_limit_reached`, no `retry-after` | The organisation reached its tier's monthly spend cap | No. It keeps failing until access resumes, so alert a human and take the exhaustion path |
| 400 `invalid_request_error`, message beginning "You have reached your specified API usage limits" | A spend limit you set yourself, or for a workspace | No. Raise the limit or wait for the reset the message states |
| 500 `api_error`, 529 `overloaded_error` | Provider-side, transient | Yes, with exponential backoff |
| Other 4xx | The request is wrong | No |

The spend-cap 429 is the dangerous one. It shares the status and error type of an
ordinary rate limit and differs in the error code and the missing header, so a retry rule
written as "429 means back off and try again" will hammer an endpoint that refuses
everything until the first of the next month, and the SDK's own automatic retries will do
the same. Key the classification on `error_code` and on whether `retry-after` is present,
not on the status alone. Likewise a rule that treats every 400 as a malformed request and
tries to repair the prompt will loop on a self-imposed spend limit.

The official SDKs retry transient failures twice by default, honouring `retry-after`, and
the retry count is configurable. A wrapper that adds its own retry loop on top multiplies
the two, so set the SDK's maximum explicitly and own the policy in one place. The product of
attempts is what the provider and the bill see.

## Spend limits at the provider

Source: the rate-limits page, "Spend limits" and "Setting lower limits for Workspaces",
2026-10-19.

- Each of the Start, Build and Scale tiers carries a monthly spend cap ($500, $1,000 and
  $200,000 at the time of writing). Reaching it pauses usage until 00:00 UTC on the first
  of the next month unless the tier is raised. The Custom tier has no cap.
- You can set your own limit below the tier cap in the Console billing page, and a limit per
  workspace. Neither can exceed the tier cap, workspace limits cannot be set on the default
  workspace, and organisation limits always apply on top of workspace ones.
- Set the provider-side limit below the number you can tolerate, and treat it as the last
  line of defence behind the in-process budgets in `routing-and-budgets.md`, not a
  substitute. It returns an error rather than degrading, it is monthly, and a batch can
  overshoot it.
- A provider-side limit has no per-tenant meaning unless each tenant has its own workspace,
  which splits caches as noted above. Per-tenant ceilings belong in your wrapper or gateway.

## Gateway budgets

An LLM gateway centralises the wrapper from `routing-and-budgets.md`. The example here is
LiteLLM's proxy. Its documentation site was not reachable when this was written, so what
follows comes from the project's source on its `main` branch as read on 2026-10-19. Confirm
field names and defaults against the documentation for the version you run.

- A virtual key or budget can carry `max_budget` (a USD figure), `budget_duration` (a
  string such as `1hr`, `1d` or `28d`), `tpm_limit`, `rpm_limit`, `max_parallel_requests`
  and a per-model budget map. `soft_budget` does not fail requests when exceeded; it only
  fires an alert, which makes it the early-warning half of a pair with `max_budget`.
- Counters have to live in shared storage. The rate limiter keeps its window counters in
  Redis when one is configured, and the budget checks read the spend counter from Redis
  first. A counter held per process enforces its limit per replica rather than per key, so
  configure Redis before running more than one replica, and test a limit by sending
  traffic through two of them.
- There is a setting, `fail_closed_rate_limit_enforcement`, that rejects requests when
  counters cannot be verified against Redis. Without it the limiter's failure mode is a
  decision you have not made. Choose fail-open or fail-closed per route and write it in the
  runbook next to the degrade, queue or refuse choice: a gateway outage that silently lifts
  every budget is the failure this section exists to prevent.
- The status code a budget rejection carries has changed between releases. The library
  default on `main` is 422, with a source comment saying to set it to 429 to restore the
  earlier behaviour. Whichever your version returns, classify budget exhaustion as not
  retryable in the client, using the same rule as the provider's spend-cap 429 above.
- Budgets are in money, computed from the gateway's price map. A price map that lags a
  provider price change under-counts spend while the provider bills the real figure, so put
  the map's update date in the cost report beside the prices fetched in step 1 of
  `SKILL.md`, and reconcile gateway-reported spend against the provider's usage and cost
  reporting at least monthly.

A gateway budget caps what one key or team spends. It does not know what a task is worth,
so keep the per-task step, token and cost caps from `SKILL.md` in the client; the gateway
is the backstop for the caller that skipped them.
