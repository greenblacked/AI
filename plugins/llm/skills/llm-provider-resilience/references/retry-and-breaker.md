# Retries, budgets and breakers

## Layers that retry

| Layer | Typical default | Action |
| --- | --- | --- |
| Provider SDK | Retries a small number of times on connection errors, 429 and 5xx | Set the SDK's max retries to zero when your wrapper owns retries, or leave it as the owner and set the others to zero |
| Your client wrapper | None until you add it | The recommended single owner |
| Agent step or tool loop | Often a loop that re-asks on failure | Remove retry on provider errors; keep re-asks for model-level problems |
| Fan-out worker | Per-item retry | Draw from the shared budget |
| Queue redelivery | Visibility timeout or nack | Make the consumer idempotent and let the budget decide |
| User retry button | Manual | Debounce, and show the cause |

Worked arithmetic: attempt limit 3 (one try plus two retries) at four nested layers gives up to 3 to the power 4, which is 81 calls per user action in the worst case. Attempts multiply across layers; they do not add.

## Full-jitter backoff

```python
import random
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone


def delay(attempt, base=0.5, cap=30.0):
    # attempt starts at 0 for the first retry
    return random.uniform(0, min(cap, base * 2**attempt))


def parse_retry_after(value):
    # Seconds ("12") or an HTTP date; None when absent or unparseable
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())


def wait_for(attempt, retry_after=None, spread=2.0):
    floor = parse_retry_after(retry_after)
    if floor is None:
        return delay(attempt)
    # The header is the floor; jitter goes on top so clients sharing a key do not retry together
    return floor + random.uniform(0, spread)
```

`Retry-After` is the floor, not a replacement for jitter: add a random amount on top when many clients share one key. It may be given in seconds or as an HTTP date; parse both.

## Global retry budget

Keep a sliding window (for example 10 seconds) of first attempts and retries. Permit a retry only if `retries + 1 <= 0.1 * first_attempts` plus a small minimum so a quiet service can still retry. When denied, return the error to the caller. The ratio is a starting point; tune it from the incident you are guarding against, and keep it per service rather than per request.

## Breaker settings

| Setting | Starting point | Why |
| --- | --- | --- |
| Scope | Provider and model | One degraded model should not close the others |
| Window | 30 to 60 seconds rolling | Short enough to react, long enough to smooth |
| Minimum requests | 20 | Two errors in a quiet period are not a trend |
| Open when | Failure rate over 50% of the retryable class | Deterministic errors must not trip it |
| Open for | 30 seconds, then half-open | Gives the provider room |
| Half-open probes | A few requests; close on success | Avoids a stampede on recovery |

## Concurrency partitions

Use a semaphore per (key, tenant) and a separate reserved pool for interactive requests. Batch work takes from the leftover. Expose queue depth and wait time per partition so starvation is visible.
