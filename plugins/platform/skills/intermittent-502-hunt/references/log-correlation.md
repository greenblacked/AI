# Log correlation

Read this at step 6: how to pull the failing requests out of the balancer's log, what
each proxy writes for each failure, and how to confirm a reset when the logs cannot.

## Contents

- [Carry one id through every hop](#carry-one-id-through-every-hop)
- [AWS Application Load Balancer](#aws-application-load-balancer)
- [nginx and ingress-nginx](#nginx-and-ingress-nginx)
- [Envoy and Istio](#envoy-and-istio)
- [Google Cloud load balancing](#google-cloud-load-balancing)
- [Confirming a reset on the wire](#confirming-a-reset-on-the-wire)

## Carry one id through every hop

Correlation needs one identifier present in every log. An ALB adds `X-Amzn-Trace-Id`,
ingress-nginx generates `$req_id`, Envoy generates or forwards `x-request-id`. Pick the
one created furthest upstream, forward it, and log it in the application on the first
line that sees the request, before any handler runs. A request that fails before the
handler is exactly the one this skill is hunting, so logging the id only at the end of a
request misses it.

## AWS Application Load Balancer

Access logs are off by default; enable `access_logs.s3.enabled` and the bucket
attributes on the load balancer, and expect several minutes of delivery delay. The
fields that matter:

| Field | Meaning for this hunt |
| --- | --- |
| `elb_status_code` | What the client received |
| `target_status_code` | What the target returned; `-` when the target sent no response |
| `target_processing_time` | `-1` when the target closed the connection or the request could not be dispatched |
| `target_ip` and `target_port` | Which target, to group failures by instance or pod |
| `trace_id` | The `X-Amzn-Trace-Id` value for the join |

With the Athena table AWS publishes for ALB logs (column names as in that definition):

```sql
SELECT target_ip, target_status_code, target_processing_time = -1 AS no_response,
       count(*) AS failures, min(time) AS first_seen, max(time) AS last_seen
FROM alb_logs
WHERE elb_status_code IN (502, 504)
  -- add the partition filter for the window you are reading
GROUP BY 1, 2, 3
ORDER BY failures DESC;
```

Failures spread evenly across targets point at configuration shared by all of them
(keepalive, health check). Failures concentrated on targets that were being replaced
point at the deploy path. Then take a sample of `trace_id` values and look each one up in
the application's logs.

## nginx and ingress-nginx

The error log names the failure directly:

| Error log text | Status | Meaning |
| --- | --- | --- |
| `upstream prematurely closed connection while reading response header from upstream` | 502 | Upstream closed the connection: keepalive race or process exit |
| `recv() failed (104: Connection reset by peer) while reading response header from upstream` | 502 | Upstream reset the connection |
| `connect() failed (111: Connection refused) while connecting to upstream` | 502 | Nothing listening: target gone or not yet started |
| `no live upstreams while connecting to upstream` | 502 | Every upstream marked failed |
| `upstream timed out (110: Connection timed out) while reading response header from upstream` | 504 | Upstream too slow for `proxy_read_timeout` |

ingress-nginx's default access-log format ends with `$upstream_addr`,
`$upstream_status` and `$req_id`, so a failing line carries the pod address it tried and
the id to search for. By default nginx does not pass a non-idempotent request such as a
POST to the next upstream after a failure, which is correct; leave `non_idempotent` out
of `proxy_next_upstream`.

## Envoy and Istio

Envoy reports the keepalive race as a 503, not a 502, with the body
`upstream connect error or disconnect/reset before headers` and a response flag in the
access log (`%RESPONSE_FLAGS%`):

| Flag | Meaning |
| --- | --- |
| `UC` | Upstream connection termination: the upstream closed or reset a connection mid-request; the keepalive race shows here |
| `UF` | Upstream connection failure: could not connect |
| `UH` | No healthy upstream |
| `UT` | Upstream request timeout (504) |
| `URX` | Retry or connect-attempt limit reached |

Add `%UPSTREAM_TRANSPORT_FAILURE_REASON%` and `%REQ(X-REQUEST-ID)%` to the access-log
format if they are missing. A `UC` count that drops to zero after the sidecar's upstream
idle timeout is set below the app's keepalive confirms the mechanism.

## Google Cloud load balancing

The load balancer's request log carries `jsonPayload.statusDetails`, which names the
cause in words, for example `backend_connection_closed_before_data_sent_to_client`,
`failed_to_connect_to_backend` or `backend_timeout`.

```bash
gcloud logging read \
  'resource.type="http_load_balancer" AND httpRequest.status>=502' \
  --freshness=1d --limit=200 \
  --format='value(timestamp,httpRequest.status,jsonPayload.statusDetails,httpRequest.requestUrl)'
```

`backend_connection_closed_before_data_sent_to_client` in volume is the keepalive race:
compare the backend's keepalive with the load balancer's.

## Confirming a reset on the wire

When the logs on both sides are inconclusive, capture resets on the target for a period
that includes failures, then match timestamps against the balancer's log:

```bash
tcpdump -nn -i any 'tcp[tcpflags] & tcp-rst != 0 and tcp port 8080'
```

On Kubernetes, run it from an ephemeral debug container sharing the pod's network
namespace. A reset sent by the application's port to the balancer's address shortly
after the connection went idle is the keepalive race, observed directly. Capture only
headers, keep the capture short, and delete it afterwards: a full packet capture holds
request bodies and credentials.
