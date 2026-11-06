# Call chain budget: <chain name>

<!-- One document per synchronous call chain. Fill it in before adding a retry. -->

## Chain

Entry point and the caller's own deadline: <entry, deadline>.

| Hop | Callee | Timeout | Deadline source | Attempts | Retries here? | Backoff | Retry budget (% of first attempts) | Idempotency key |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | <callee> | <ms> | <propagated absolute deadline or measured p99 tail latency> | <n> | <yes or no, exactly one layer> | <capped full jitter: base, cap> | <about 10%> | <key or not needed> |

## Amplification

Product of attempts for the deepest dependency: <number>, from <attempts per hop multiplied>.

## Proof

Fault-proxy run that proved the chain (100 percent 503, and accepts then hangs): <link or file>.
Amplification ratio measured: <ratio, target at most about 1.1>.

Date: <YYYY-MM-DD>
Owner: <name or team>
