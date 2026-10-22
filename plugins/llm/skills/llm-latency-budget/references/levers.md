# Levers, and when each one fails

| Lever | Helps which stage | Fails when | Test |
| --- | --- | --- | --- |
| Shrink output | Decode (total) | Output is already short; quality needs the detail | Compare output tokens and eval score |
| Stable cached prefix | Prompt processing | Prefix is below the provider's minimum cacheable length, or content near the top varies per call | Cache-read tokens rise on the second call |
| Parallel tools | Tool time | Calls depend on each other's results | Wall time of the tool phase falls toward the slowest single call |
| Speculative retrieval | Retrieval, queue | Most speculations are discarded and load or cost rises | Hit rate of used speculative results |
| Smaller model | TTFT and decode | The step needs the larger model's quality | Eval per step, not overall |
| Streaming | Perceived first progress | The first token itself is slow | First paint time, not total |
| Hedging | Tail of idempotent reads | Call has side effects; provider limits are tight | p95 falls, request count rises by the hedge rate |

## Perceived-latency design

Show a status line for each tool phase ("Searching your documents"), render partial structured results as they arrive, and keep the layout stable so streamed text does not shift controls. A visible tool-call indicator buys patience; a blank screen does not.

## Order of attack

Start with output length and the cached prefix because they cost no new infrastructure and move the stages that dominate most chat and agent traffic. Parallelism comes next for agents with several tool calls. Model downsizing and hedging come last because each needs its own eval or carries a cost.
