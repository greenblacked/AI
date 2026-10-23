# Sending checklist

Read this when designing outbound webhooks for customers: it has the endpoint states and the schedule.

## Endpoint states

| State | Entered when | Behaviour |
| --- | --- | --- |
| active | Created and verified | Deliver normally |
| degraded | Recent failures, below the pause rule | Deliver with the normal schedule; show a warning in the dashboard |
| paused | Continuous failure beyond the pause rule | Stop attempts; keep events queued or recoverable; email the owner |
| disabled | Owner action | No delivery; events are not queued |

Resuming from paused should offer redelivery of events missed during the pause.

## Retry schedule (example, adjust to your customers)

| Attempt | Delay after previous |
| --- | --- |
| 1 | immediate |
| 2 | 30 seconds |
| 3 | 5 minutes |
| 4 | 30 minutes |
| 5 | 2 hours |
| 6 | 8 hours |
| 7 and later | 12 hours until about two days have passed |

Add jitter to each delay so a customer coming back from an outage is not hit by every queued event at the same second. Treat 2xx as success, 410 as a signal to disable, and everything else including redirects and timeouts as failure.

## Delivery log fields

Event id, endpoint id, attempt number, request time, status code or error class, latency, first 1 KB of the response body, next attempt time. Offer a manual redeliver that creates a new attempt for the same event id.

## Customer documentation

State: delivery is at least once, dedupe on the id header, ordering is not guaranteed, how to verify a signature with a code sample, the timestamp tolerance, how to rotate secrets, the source IP ranges if you publish them, and the response time you expect.

## SSRF checks for the URL field

- https only, no credentials in the URL, no unusual ports unless you allow them deliberately.
- Resolve the name, then reject every resolved address in loopback, private, link-local and unique-local ranges, including IPv4-mapped IPv6 forms.
- Connect to the address you validated, not to the name again.
- Do not follow redirects; a redirect is a second URL you have not validated.
- Re-check on every delivery, not only when the endpoint is saved, because DNS can change.
