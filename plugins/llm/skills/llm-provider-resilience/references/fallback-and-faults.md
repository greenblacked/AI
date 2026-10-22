# Fallbacks and fault injection

## Fallback admission checklist

- Ran the full eval set on the fallback; quality gap recorded against the primary.
- Structured output: schema validity rate re-measured, not assumed.
- Tool use: argument shapes, tool selection and parallel-call behaviour re-checked.
- Refusal and safety behaviour compared on the refusal cases in the eval.
- Context window, maximum output tokens and tokeniser differences handled.
- Prompt differences reviewed; a prompt tuned for one model is not neutral.
- Data handling and region terms of the second provider approved by whoever owns data privacy.
- Degraded mode chosen per feature: fallback model, cached answer, reduced feature or honest error.

## Mid-stream failure

| Feature | Rule | Reason |
| --- | --- | --- |
| Chat reply the user is reading | Surface partial with a marker and a retry control | Text already seen cannot be unseen |
| Background summary | Restart | Nobody saw the partial |
| Structured output | Restart | A truncated object does not parse |
| Tool-calling turn | Restart, with idempotency keys on tools | Half a tool call is unusable |
| Long generation with a checkpoint | Resume from the last complete unit | Saves tokens, only if continuation is safe |

## Fault matrix

| Fault | Inject | Pass when |
| --- | --- | --- |
| Rate limit with Retry-After | Return 429 and the header from a test proxy | Waits at least the header, budget holds |
| Rate limit without header | Return 429 | Full-jitter backoff, no synchronised retry |
| Overloaded | Return the provider's overloaded status | Breaker opens, fallback or degraded mode serves |
| Spend-cap 429 | Return the quota error body | No retry, alert raised |
| Slow first token | Delay first byte past the timeout | Times out, counts as retryable, budget holds |
| Dropped stream | Close the connection mid-output | The per-feature rule from the table runs |
| Full outage | Block the primary entirely | Fallback share rises, quality alert is quiet only if the eval allows it |
| Recovery | Remove the fault | Half-open probes close the breaker without a stampede |

## Alerts

Fallback share over a threshold, breaker open for more than a few minutes, retry-budget denials per minute, time to first token at p95, and the deterministic-error rate (a rise usually means a deploy, not the provider).
