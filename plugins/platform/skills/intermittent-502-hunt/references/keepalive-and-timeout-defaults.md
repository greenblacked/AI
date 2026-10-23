# Keepalive and timeout defaults

Read this at step 2. It lists where each common hop sets its idle and keepalive
timeouts and what each defaults to, then applies the ordering rule to a full chain.
Defaults move between releases; treat a figure here as the place to look, and confirm it
against the version actually deployed.

## Contents

- [The rule](#the-rule)
- [Balancers and CDNs](#balancers-and-cdns)
- [Proxies and meshes](#proxies-and-meshes)
- [Application servers](#application-servers)
- [Applying it to a chain](#applying-it-to-a-chain)

## The rule

On each hop, the side that opens the connection and reuses it (the client: CDN,
balancer, proxy) must close an idle connection before the side that accepts it (the
server: proxy, app) does. When the server closes first, there is a window in which the
client picks the idle socket for a new request at the moment the server's FIN or RST is
in flight, and that request fails without the server ever reading it. Leave a margin of
several seconds rather than one, because neither side's timer is exact.

## Balancers and CDNs

These are client-side timeouts towards the next hop.

| Component | Setting | Default |
| --- | --- | --- |
| AWS Application Load Balancer | `idle_timeout.timeout_seconds` load balancer attribute | 60 s |
| AWS Classic Load Balancer | connection idle timeout | 60 s |
| AWS Network Load Balancer | TCP idle timeout | 350 s |
| Google Cloud external Application Load Balancer | backend keepalive | About 600 s; Google's documentation asks for a backend keepalive longer than the load balancer's. Check the figure for your load balancer type. |
| Amazon CloudFront | origin keep-alive timeout | 5 s |
| Amazon CloudFront | origin response timeout | 30 s (a slower origin produces a 504 at the edge) |

```bash
aws elbv2 describe-load-balancer-attributes --load-balancer-arn "$LB_ARN"
aws elbv2 modify-load-balancer-attributes --load-balancer-arn "$LB_ARN" \
  --attributes Key=idle_timeout.timeout_seconds,Value=60
```

## Proxies and meshes

A proxy is a server towards the hop in front of it and a client towards the hop behind
it, so it has two settings, and both must satisfy the rule.

| Component | Server side (towards its client) | Client side (towards its upstream) |
| --- | --- | --- |
| nginx | `keepalive_timeout`, default 75 s | `keepalive_timeout` inside the `upstream` block, default 60 s; upstream keepalive is only used with `proxy_http_version 1.1` and an empty `Connection` header |
| ingress-nginx | ConfigMap `keep-alive`, default 75 | ConfigMap `upstream-keepalive-timeout`, default 60 |
| Envoy | HTTP connection manager `common_http_protocol_options.idle_timeout` | cluster `common_http_protocol_options.idle_timeout`, default 1 hour |
| Istio | as Envoy | `DestinationRule` `trafficPolicy.connectionPool.http.idleTimeout`, default 1 hour |
| HAProxy | `timeout http-keep-alive` | `timeout server` and the server's own keepalive behaviour |

The Envoy and Istio upstream default of one hour is longer than almost every application
server's keepalive, so a sidecar in front of an app server with a five-second keepalive
reproduces the race inside the pod. Set the sidecar's upstream idle timeout below the
app's keepalive, or raise the app's.

## Application servers

These are server-side keepalive timeouts: each must exceed the idle timeout of whatever
sits directly in front.

| Server | Setting | Default | Note |
| --- | --- | --- | --- |
| Node.js `http.Server` | `server.keepAliveTimeout` | 5 s | Also set `server.headersTimeout` above `keepAliveTimeout` |
| Gunicorn | `--keep-alive` | 2 s | The sync worker does not support persistent connections and ignores it |
| uvicorn | `--timeout-keep-alive` | 5 s | |
| Apache httpd | `KeepAliveTimeout` | 5 s | |
| Go `net/http` | `Server.IdleTimeout` | Falls back to `ReadTimeout`; no limit if both are zero | An unset `IdleTimeout` with a short `ReadTimeout` is the trap |
| Tomcat | `keepAliveTimeout` on the connector | Follows `connectionTimeout` (20 s in the stock `server.xml`) | |
| ASP.NET Core Kestrel | `KestrelServerLimits.KeepAliveTimeout` | 130 s | |

## Applying it to a chain

Write the chain left to right and fill a row per hop. Every row must read "client idle
shorter than server keepalive".

| Hop | Client idle | Server keepalive | Holds |
| --- | --- | --- | --- |
| CloudFront to ALB | 5 s (origin keep-alive) | 60 s (the ALB idle timeout applies to client connections too) | Yes |
| ALB to ingress-nginx | 60 s | 75 s (`keep-alive`) | Yes |
| ingress-nginx to Envoy sidecar | 60 s (`upstream-keepalive-timeout`) | sidecar's inbound idle timeout | Check |
| Envoy sidecar to Node.js app | 1 hour (Envoy default) | 5 s (Node.js default) | No: fix here |

The failing row is usually the last one, because it is the hop nobody configured. Change
that row only, then re-measure: a change to a row that already held adds risk and no
signal.
