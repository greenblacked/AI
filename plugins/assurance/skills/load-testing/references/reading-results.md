# Reading results

How to decide whether a run can be believed, and how to report one so someone can act on it.

## Contents

- [Coordinated omission in detail](#coordinated-omission-in-detail)
- [Is the run valid](#is-the-run-valid)
- [Client against server latency](#client-against-server-latency)
- [Reading the distribution](#reading-the-distribution)
- [Comparing against a baseline in CI](#comparing-against-a-baseline-in-ci)
- [Report template](#report-template)

## Coordinated omission in detail

A closed-model generator sends a request, waits for the response, then sends the next. Suppose
the service stalls for two seconds. Each virtual user records one two-second request and sends
nothing else during the stall. In production, requests keep arriving at the same rate during
those two seconds and every one of them waits. The generator has recorded one slow sample where
production would have produced a whole stall's worth, so the slow tail is under-represented and
p99 looks far better than any user would experience.

An open model keeps sending on schedule, so the queue builds and the stall shows up across
every request that arrived during it. Some tools also correct the recorded latency to measure
from the intended send time rather than the actual one; wrk2 does this, which is why it insists
on a target rate.

The practical test: if p99 barely moves while throughput stops rising, suspect a closed model or
a saturated generator before believing the service is fine.

## Is the run valid

Check these before reading any latency number. If one fails, the run is void, not "mostly
fine":

| Check | How | Fails when |
| --- | --- | --- |
| Offered rate achieved | Achieved requests per second during the hold against the configured rate | Achieved is materially below offered |
| No dropped iterations | k6 `dropped_iterations` | Any non-zero count during the hold |
| Generator had headroom | Generator host CPU, memory, network, ephemeral ports | CPU near full, network near line rate, port exhaustion |
| Errors read first | Error rate by status and by type (timeout, reset, 5xx) | Error rate high while latency looks good: slow requests became errors |
| Right target | Requests spread across the fleet behind the load balancer | One node took everything because the generator pinned one address |
| Production-shaped | Environment and data checklist from the skill | Any difference not listed in the report |

## Client against server latency

For the hold phase, compare the generator's percentiles with the service's own request-duration
histogram for the same window and route.

- **Client close to server.** Time is in the service. Hand the slow route to profiling or, for a
  query, to SQL tuning.
- **Client well above server.** Time is spent before the service sees the request: load
  balancer queueing, the accept queue, TLS handshakes without connection reuse, or the generator
  itself. Check connection reuse and generator headroom first.
- **Server above client.** Usually clock or window misalignment, or the server metric includes
  work after the response was sent. Fix the measurement before interpreting it.

Record the utilisation of each candidate bottleneck at the hold rate: CPU per instance, pool
in-use against size and wait time, database CPU and IO, downstream latency and rate-limit
responses. The answer to "what runs out first" is the one closest to its limit, stated with its
number.

## Reading the distribution

Look at the histogram, not only the summary. A bimodal shape (most requests fast, a cluster at
exactly the timeout value) means some requests are hitting a timeout or retry path; a uniformly
shifted distribution means general contention. Both can produce the same p99.

Percentiles cannot be averaged. Averaging the p99 of four nodes, or of sixty one-minute
intervals, gives a number that is not the p99 of anything. Merge the raw samples or the
histograms and compute the percentile over the merged data; keep the raw output for this reason.

Report max alongside p99. With hundreds of thousands of requests, p99 still leaves thousands of
requests above it, and the max shows whether that tail is 600 ms or 30 seconds.

## Comparing against a baseline in CI

A short, smaller load test in CI catches regressions, not capacity:

- Run the same script, same rate, same environment size and same data on every comparison;
  any of those changing makes the comparison meaningless.
- Compare against a stored baseline from the main branch, not against the SLO; the question is
  "did this change make it worse".
- Run-to-run noise on shared CI hardware is large. Measure it by running the baseline several
  times, and set the regression threshold above that noise, or the job becomes the flaky check
  everyone reruns.
- Keep the full-scale, production-shaped run as a scheduled job; CI-sized runs do not answer
  launch questions.

## Report template

```markdown
## Question and answer
Question: [one sentence with numbers]
Answer: [yes/no], because [threshold results in one line]

## Run
Date, script revision, environment, data snapshot, generator hosts, raw output location.
Load model: open (arrival rate) | closed, with reason.

## Thresholds
| Metric | Threshold | Source (SLO or agreed) | Result |

## Load delivered
| Phase | Offered rps | Achieved rps | Dropped iterations | Generator CPU peak |

## Results per route (hold phase)
| Route | Share | p50 | p95 | p99 | max | Error rate | Errors by type |

## Bottleneck
Resource, its utilisation at the hold rate, and the evidence. Client against server gap.

## Differences from production
Environment, data, stubbed dependencies, anything that narrows the claim.

## Next
What would change the answer, and who owns each follow-up.
```
