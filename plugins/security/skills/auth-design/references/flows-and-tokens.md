# Flows and tokens

Read this when choosing a flow for a client, integrating with a specific identity
provider, or writing the code that validates a token. It is the depth behind steps 2, 3
and 6 of `SKILL.md`.

Every source named here is given with a number and a date so you can check it. Where a
document is revised continuously rather than published once, that is said explicitly and
you should read the revision date on the page rather than trusting this file's summary.

## Contents

- The sources, and what each one settles
- The authorization request, parameter by parameter
- Per-client-type detail
- Redirect URI registration
- Token endpoint and client authentication
- Refresh token rotation and reuse detection
- The JWT validation checklist, in order
- Keys, `kid` and JWKS caching
- Revocation, and what each option costs
- Integration checks against a provider

## The sources, and what each one settles

| Document | Date | What to take from it |
| --- | --- | --- |
| RFC 6749, The OAuth 2.0 Authorization Framework | October 2012 | The grants and the endpoints. Read it alongside RFC 9700, not on its own — parts of it are superseded in practice. |
| RFC 6750, Bearer Token Usage | October 2012 | How a bearer token is presented, and the `WWW-Authenticate` error responses. |
| RFC 7636, Proof Key for Code Exchange | September 2015 | PKCE: `code_challenge`, `code_challenge_method`, `code_verifier`. |
| RFC 8252, OAuth 2.0 for Native Apps | October 2017 | System browser rather than embedded webview; loopback and private-scheme redirects. |
| RFC 8628, Device Authorization Grant | August 2019 | The input-constrained flow, including the polling rules. |
| RFC 8705, Mutual-TLS Client Authentication and Certificate-Bound Tokens | February 2020 | Sender-constrained tokens via client certificates. |
| RFC 8725, JSON Web Token Best Current Practices | February 2020 | Algorithm verification, why `alg: none` and algorithm confusion happen, and what to do. |
| RFC 9068, JWT Profile for OAuth 2.0 Access Tokens | October 2021 | `typ: at+jwt` and the claims a resource server validates. |
| RFC 9126, Pushed Authorization Requests | September 2021 | Sending the authorization request through the back channel. |
| RFC 9207, Authorization Server Issuer Identification | March 2022 | The `iss` response parameter that closes the mix-up case. |
| RFC 9449, DPoP | September 2023 | Sender-constrained tokens without client certificates. |
| RFC 9700, OAuth 2.0 Security Best Current Practice | January 2025 | The current consolidated guidance: exact redirect matching, PKCE, no implicit, no password grant, refresh rotation or sender-constraining. |
| OpenID Connect Core 1.0 | Published with errata; check the errata set on the copy you read | `nonce`, the ID token and its validation steps, and the distinction between an ID token and an access token. |
| OAuth 2.1 draft (`draft-ietf-oauth-v2-1`) | Draft, not an RFC | Consolidates the above into one document. Useful as a summary; cite the RFCs, not the draft. |

Two things to note when citing. RFC 9700 is a best current practice rather than a
standards-track protocol change, which is why it can say "must not" about a grant defined
in RFC 6749. And OAuth 2.1 is still a draft; treating it as settled is a common error in
design documents, even though its content is drawn from documents that are.

## The authorization request, parameter by parameter

| Parameter | Value | Why |
| --- | --- | --- |
| `response_type` | `code` | The only value still in use. `token` and `id_token token` are the implicit responses. |
| `client_id` | Your registered id | Public, not a secret, even for a confidential client. |
| `redirect_uri` | The exact registered string | Send it even when the provider allows omitting it; it is checked against the registration. |
| `scope` | The minimum for this operation | Scope creep in the request is the authorization-side version of a wildcard IAM policy. |
| `state` | Unguessable, per request, stored in the browser session | Cross-site request forgery on the callback, plus wherever the return-to path lives. |
| `nonce` | Unguessable, per request, stored in the browser session | ID token replay binding (OpenID Connect Core). |
| `code_challenge` | Base64url SHA-256 of the verifier | PKCE (RFC 7636). |
| `code_challenge_method` | `S256` | `plain` exists for constrained devices and gives up the property PKCE was added for. |
| `prompt`, `max_age` | Set when you need a fresh authentication | Step-up and re-authentication depend on these, and on checking `auth_time` in the response. |

The `code_verifier` is generated fresh per request with a cryptographic random source, at
least 43 characters of the unreserved set, and held where only this client instance can
read it — the server-side session for a confidential client, memory for a browser client.
Persisting it somewhere shared between users or tabs removes the binding it exists for.

On the callback, in this order: check `state` matches and consume it; check `iss` if the
provider sends it; exchange the code with the verifier; validate the ID token including
`nonce`; only then create the session. Creating the session before the ID token validates
is how a partially validated login becomes a full one.

## Per-client-type detail

**Server-side web application.** Confidential client. Authenticate to the token endpoint
with `private_key_jwt` or mutual TLS where the provider supports it, a client secret
otherwise. Tokens stay on the server, keyed by the session. The browser receives a cookie
and nothing else.

**Single-page application.** Public client, so there is no client secret to protect —
anything shipped to the browser is readable. Authorization code with PKCE is the minimum.
The better shape is a backend-for-frontend: a small server-side component that completes
the flow, holds the tokens, and exposes a cookie session to the browser. That converts
"where do we store the token" from an unanswerable question into a non-question.

**Native and mobile.** System browser through `ASWebAuthenticationSession` on iOS or
Custom Tabs on Android, never an embedded webview — the host application can read what is
typed into a webview, the platform credential manager and passkeys are unavailable, and
single sign-on with other applications does not work. Redirect to a claimed HTTPS scheme
(universal links, App Links) where possible, because a private-scheme redirect can be
registered by another application on the same device; RFC 8252 covers both, and PKCE is
what keeps a hijacked private-scheme redirect from being redeemable.

**Machine-to-machine.** Client credentials, and prefer a key over a secret:
`private_key_jwt` or mutual TLS (RFC 8705). Before any of that, check whether the platform
can issue a workload identity instead, in which case there is no credential to store,
distribute or rotate. Where a static credential is unavoidable, its rotation is
`secret-rotation`'s problem, and the design should say who owns it.

**Device and input-constrained.** RFC 8628. Respect the `interval` when polling and back
off on `slow_down`; a client that polls tightly gets rate-limited and looks broken. Show
the user code in a font where the ambiguous characters are distinguishable, and keep the
code short-lived.

## Redirect URI registration

Exact string comparison, per RFC 9700. The narrow exception is a native application's
loopback redirect, where the port is assigned by the operating system and therefore varies
(RFC 8252); the host and path still match exactly.

Patterns that come up, and what to do instead of relaxing the match:

| Need | Do this |
| --- | --- |
| Preview or per-branch deployments | Register each host if the provider has an API for it, or route every preview through one stable callback host that redirects internally to a destination bound to `state`. |
| Several environments | A separate client registration per environment. Sharing one client across production and staging means a staging compromise mints production codes. |
| Several tenants on subdomains | One registration per tenant, generated by the same automation that provisions the tenant. |
| A mobile app and a web app | Separate client registrations. Different client types have different flows and different secrets. |

Then audit the registered endpoints themselves. A registered callback that forwards to a
location taken from a query parameter reintroduces everything exact matching prevented,
and it will pass every review that only reads the registration list.

## Token endpoint and client authentication

Ranked by what a stolen artefact costs you:

1. **Mutual TLS or `private_key_jwt`** — the private key never leaves the client, so
   interception of a request yields nothing reusable.
2. **Client secret over TLS** — a shared secret that lives in the client's configuration
   and in the provider's database, with all the copies that implies.
3. **No client authentication** (public clients) — PKCE is doing all the work, which is
   exactly why it is not optional.

Pushed authorization requests (RFC 9126) move the request parameters to a back-channel
call, so the front-channel URL carries only a reference. Worth taking where the provider
supports it, particularly for high-value flows: it removes the parameter tampering surface
entirely rather than validating it.

## Refresh token rotation and reuse detection

The mechanism: each refresh returns a new refresh token and invalidates the presented one.
Presenting an already-used token means two parties hold that token, so the provider revokes
the whole family — every token descended from that grant — and the user re-authenticates.

Three implementation details decide whether this works in production:

- **Grace window.** A client that sent a refresh, lost the response to a timeout and
  retried will present the old token in good faith. Accept the immediately preceding token
  for a few seconds and return the same new token, rather than treating every race as an
  attack. Longer than that and the window becomes the vulnerability.
- **Concurrency.** Two tabs or two threads refreshing at once produce the same pattern.
  Serialise refresh in the client — one in-flight refresh, others wait on it — which is a
  client-side fix for a server-side alarm.
- **What the alarm means.** After the grace window, a reuse event is a report that a
  refresh token exists in two places. You cannot tell which presenter is legitimate, which
  is precisely why the response is to revoke both. Route it to alerting with the user, the
  client and both source addresses; a family revocation that only appears in a log is a
  compromise you detected and did not read.

Sender-constraining (DPoP, RFC 9449, or mutual-TLS binding, RFC 8705) is stronger than
rotation because it makes a stolen token unusable rather than detectable after the fact.
Take it where the provider and the client stack both support it, and keep rotation as well.

## The JWT validation checklist, in order

Order matters: every step after the first is meaningless if the first is skipped.

1. **Parse without trusting.** Treat the header and payload as attacker-controlled input
   until the signature verifies.
2. **Select the key yourself.** From your cached JWKS for the expected issuer, by `kid`.
   Reject a token whose header names a key source — `jku`, `x5u` — or embeds a key (`jwk`),
   rather than following it. RFC 8725 is explicit here.
3. **Verify the signature with an algorithm you passed in.** Not one read from the token.
   The allowlist is usually one entry: whatever your issuer signs with, typically `RS256`,
   `PS256` or `ES256`. Reject `none` unconditionally. Reject an HMAC algorithm on a token
   expected to be asymmetric, which is the algorithm-confusion case — an attacker signs
   with `HS256` using the issuer's public key as the shared secret, and a verifier that
   selects its algorithm from the header accepts it, because the public key is published.
4. **`iss`** equals the exact expected issuer string, compared byte for byte.
5. **`aud`** contains this service's identifier. Without this, a valid token minted for
   another service or another tenant of the same provider passes. It is the most commonly
   missing check in code that appears to work.
6. **`exp`**, and `nbf` if present, with a clock skew allowance of about a minute.
7. **`typ`** where the profile defines one: `at+jwt` for an access token under RFC 9068.
   This is what stops an ID token being presented at a resource server.
8. **`azp`, `sub`, `scope` and any authorisation claims** last, after the token is known to
   be genuine and addressed to you. These decide what the caller may do, which is a
   different question from who they are.

For an ID token, add the `nonce` comparison against the value stored in the session, and
`auth_time` where you asked for a maximum age. OpenID Connect Core sets out the full ID
token validation sequence; follow it rather than a subset.

## Keys, `kid` and JWKS caching

Fetch the JWKS URL from the provider's discovery document, not from configuration typed by
hand, and cache the result with a TTL of minutes to hours. On an unknown `kid`, re-fetch
once, rate-limited — an unbounded re-fetch on unknown `kid` turns any forged token into a
request amplifier against your own provider. Keep the previous key valid through a rollover
window, because the provider publishes the new key before it starts signing with it, and a
verifier that only holds one key fails during every rotation.

If you are the issuer, rotate signing keys on a schedule, publish the new key ahead of
first use, and keep the retired key published for at least the longest token lifetime.

## Revocation, and what each option costs

| Option | Latency | Cost |
| --- | --- | --- |
| Short access token, revoke the refresh token (RFC 7009, August 2013) | One access token lifetime | The default. Requires you to actually keep access tokens short. |
| Introspection at the edge (RFC 7662, October 2015) | Immediate | A network call per request, or a cache that reintroduces the same latency you were removing. |
| Deny list of revoked identifiers at the gateway | Immediate | A shared store, which is the session store you avoided, plus the operational question of when entries expire. |
| Back-channel logout (OpenID Connect Back-Channel Logout) | Provider-driven | Only covers sessions the provider knows about; your own session records still need deleting. |

Whichever you pick, write the resulting revocation latency into the design as a number.
"How quickly can we cut off a compromised account" is asked during an incident, and the
answer is a property of this decision made months earlier.

## Integration checks against a provider

Run these against your own registration in a test tenant before the design is signed off.

- The discovery document lists the algorithms you expect, and your allowlist matches.
- A request with a redirect URI differing by one character is rejected.
- A code redeemed twice is rejected the second time, and the provider revokes the grant.
- A code redeemed with the wrong `code_verifier` is rejected.
- A refresh token replayed after rotation revokes the family and the event is visible.
- Access tokens carry the audience your resource servers check for, and ID tokens do not.
- Token lifetimes in the issued tokens match the configured values you wrote down.
