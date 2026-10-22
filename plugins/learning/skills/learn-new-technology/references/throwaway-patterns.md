# Throwaway patterns

## Contents

- [Choosing the throwaway](#choosing-the-throwaway)
- [What to measure](#what-to-measure)
- [Rules](#rules)

## Choosing the throwaway

| Kind of tool | Hardest requirement often is | Throwaway |
| --- | --- | --- |
| Database | Query shape at realistic size, or behaviour on failover | Load realistic row counts, run the real query with the planned index, kill the primary once |
| Queue or stream | Ordering, delivery guarantee, lag | Produce a numbered sequence, restart a broker and a consumer, check for gaps and duplicates |
| Web framework | A request lifecycle quirk: auth, streaming, background work | One endpoint that does the awkward thing, tested with the real client |
| Language | Concurrency model, interop with existing code | The smallest service that calls the existing library or shares state across tasks |
| Library | Behaviour on the worst input | Feed it the ugliest real file you own and malformed variants |
| Infrastructure tool | State handling and rollback | Apply, change, destroy and re-apply against a scratch environment |

## What to measure

Whatever the requirement states: latency percentile, throughput, memory, loss count, recovery
time, lines of code you had to write to get correct behaviour. Record the machine, version and
data size beside every number, or the number cannot be reused.

## Rules

- Under about 100 lines; if it needs more, the requirement was too large to test in one go, so split it.
- Realistic data, not generated rows that all look the same.
- Include the failure: restart, timeout, malformed input.
- Hand the code back with the measurements and notes, then throw it away; it was never meant to ship.
