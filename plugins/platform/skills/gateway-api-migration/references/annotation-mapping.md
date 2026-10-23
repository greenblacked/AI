# Annotation and default mapping

Read this at step 3, before writing any route. It maps the ingress-nginx annotations and
controller-wide defaults that most often decide behaviour to their Gateway API
counterparts. Annotation keys below drop the `nginx.ingress.kubernetes.io/` prefix.

Support levels are Gateway API's own: **Core** every conformant implementation supports,
**Extended** an implementation may support and its conformance report says whether it
does, **none** means there is no Gateway API field and the behaviour needs an
implementation-specific policy or a decision to drop it. Field availability also depends on
the Gateway API release and channel of the installed CRDs; check both before relying on
anything outside Core.

## Contents

- Behaviour the controller applies without an annotation
- Routing and paths
- Redirects and rewrites
- Traffic splitting and session affinity
- Limits, timeouts and buffering
- Authentication and access control
- Backends and protocols
- Snippets
- Recording the decision

## Behaviour the controller applies without an annotation

These are the rows a converter cannot see, because nothing on the Ingress object mentions
them. Check the old controller's ConfigMap for any value overriding the default.

| Old behaviour | ingress-nginx default | What to write on the new side |
| --- | --- | --- |
| HTTP to HTTPS redirect for hosts with TLS | On (`ssl-redirect`) | An HTTP listener plus an `HTTPRoute` with a `RequestRedirect` filter, `scheme: https`, status 301 or 302 (Core); ingress-nginx redirects with 308 by default and Gateway API's redirect filter cannot express it, so record in the mapping table whether any client relied on the method being preserved |
| Request body limit | 1 MiB (`proxy-body-size`) | Implementation policy; Gateway API has no body-size field. The new default may be larger, smaller or unlimited |
| Upstream read and send timeouts | 60 s each | `HTTPRoute` `timeouts.request` and `timeouts.backendRequest` (Extended); semantics differ, since these bound the whole request rather than the gap between reads |
| Regex path matching | Case-insensitive | `RegularExpression` path match is implementation-specific in syntax and case handling; test mixed case explicitly |
| `ImplementationSpecific` paths | Plain string prefix, so `/api` also matches `/apiv2` | `PathPrefix` matches whole path elements and will not; decide whether the looser match was relied on |
| Requests for an unknown host | Default backend, usually a 404 page | Whatever the implementation returns for no matching route; add a catch-all route if clients depend on the old page |
| `X-Forwarded-*` handling | Trusted only with `use-forwarded-headers` | Implementation setting for trusted proxies; a wrong value changes client IPs in logs and rate limits |

## Routing and paths

| Annotation | Gateway API | Notes |
| --- | --- | --- |
| `use-regex` | `path.type: RegularExpression` (implementation-specific) | Regex flavour differs between data planes; re-test every pattern |
| `app-root` | `RequestRedirect` on an `Exact` match for `/` with `path.replaceFullPath` | Core redirect, Extended path modifier |
| `server-alias` | Add the alias to `HTTPRoute.spec.hostnames` | Also needs a listener whose hostname covers it |

## Redirects and rewrites

| Annotation | Gateway API | Notes |
| --- | --- | --- |
| `rewrite-target` without capture groups | `URLRewrite` with `replacePrefixMatch` (Extended) | Replaces the matched prefix only |
| `rewrite-target` with `$1`, `$2` | none | Capture-group rewrites have no field. Restructure the paths, or use an implementation policy |
| `permanent-redirect`, `temporal-redirect` | `RequestRedirect` with `statusCode` and `hostname` or `path` | Core |
| `upstream-vhost` | `URLRewrite` with `hostname` (Extended) | |
| `x-forwarded-prefix` | `RequestHeaderModifier` adding the header (Core) | |

## Traffic splitting and session affinity

| Annotation | Gateway API | Notes |
| --- | --- | --- |
| `canary`, `canary-weight` | Weighted `backendRefs` on one route (Core) | Simpler than the two-Ingress canary pattern; delete the second Ingress rather than porting it |
| `canary-by-header`, `canary-by-cookie` | A second rule with a `headers` match, pointing at the canary backend | Cookie matching is a header match on `Cookie`, which is fragile; prefer a dedicated header |
| `affinity: cookie` | `sessionPersistence` | Experimental channel at the time of writing; check the installed release before relying on it |
| `upstream-hash-by` | none | Implementation policy |

## Limits, timeouts and buffering

| Annotation | Gateway API | Notes |
| --- | --- | --- |
| `proxy-body-size` | none | Implementation policy. Carry the old value across explicitly, including `0` meaning unlimited |
| `proxy-read-timeout`, `proxy-send-timeout`, `proxy-connect-timeout` | `timeouts.backendRequest` covers part of it (Extended) | No per-phase timeouts in Gateway API |
| `proxy-buffering`, `proxy-buffer-size` | none | Implementation policy; streaming responses are where this shows |
| `limit-rps`, `limit-connections` | none | Implementation policy, or move rate limiting to a dedicated layer |

## Authentication and access control

| Annotation | Gateway API | Notes |
| --- | --- | --- |
| `auth-url`, `auth-signin`, `auth-response-headers` | none | External authorisation is implementation policy; port it before the route takes traffic, because a missing auth filter fails open |
| `auth-type: basic`, `auth-secret` | none | Implementation policy |
| `whitelist-source-range`, `denylist-source-range` | none | Implementation policy, or a cloud load-balancer or firewall rule. Fails open if forgotten |
| `enable-cors` and the `cors-*` keys | CORS filter in recent releases, otherwise implementation policy | Check the release and channel |

The rows that fail open are the ones to block on. A forgotten body limit produces errors; a
forgotten auth filter or allow-list produces a route that works for everybody.

## Backends and protocols

| Annotation | Gateway API | Notes |
| --- | --- | --- |
| `backend-protocol: HTTPS` | `BackendTLSPolicy` | Check the release and the implementation's support |
| `backend-protocol: GRPC` | `GRPCRoute` | Standard channel since Gateway API v1.1 |
| `ssl-passthrough` | `TLSRoute` on a listener with `mode: Passthrough` | `TLSRoute` support varies; check conformance |
| `service-upstream` | none | Implementation setting for routing to the Service IP rather than endpoints |

## Snippets

`configuration-snippet`, `server-snippet` and `stream-snippet` have no mapping by
construction: they are raw nginx configuration. For each one, write down what it does in
one sentence, then map that intent using the tables above. Typical contents and where they
go:

| Snippet usually does | Where it goes |
| --- | --- |
| Adds or removes a response header | `ResponseHeaderModifier` (Extended) |
| Adds a request header | `RequestHeaderModifier` (Core) |
| Returns a fixed response for a path | Implementation policy, or a tiny backend |
| `if` blocks on headers or arguments | Rule-level `headers` or `queryParams` matches |
| Anything with `lua` or `more_set_headers` | Re-express the intent; nothing ports directly |

## Recording the decision

One row per annotation per route, kept with the migration:

| Namespace/Ingress | Annotation | Value | Decision | Target field or policy | Agreed by |
| --- | --- | --- | --- | --- | --- |
| shop/checkout | `proxy-body-size` | `20m` | Policy | implementation body-size policy at 20 MiB | team owner |
| shop/checkout | `configuration-snippet` | adds `X-Frame-Options` | Field | `ResponseHeaderModifier` | team owner |
| blog/www | `rewrite-target` | `/$2` | Blocked | paths restructured first | team owner |

A route with any row still marked Blocked does not move.
