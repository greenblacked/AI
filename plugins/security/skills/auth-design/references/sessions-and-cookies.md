# Sessions and cookies

Read this when writing session or cookie code, designing logout, adding a
backend-for-frontend, or working out why a cookie is missing on a cross-site request. It
is the depth behind steps 4 and 5 of `SKILL.md`.

Browser behaviour moves faster than the specifications that describe it. Where something
here depends on a browser's current behaviour rather than on a written rule, that is said
plainly; verify it against the browsers you support rather than against this file.

## Contents

- What the session is, and what it is not
- Every point at which the identifier rotates
- Session identifier properties
- Cookie attributes in full
- Where SameSite does not reach
- Timeouts, idle and absolute
- Logout, and sign out everywhere
- The backend-for-frontend pattern
- Binding a session to a device
- Verification

## What the session is, and what it is not

A session is a server-side record that a particular browser has proved who it belongs to,
plus an opaque identifier the browser presents to reference that record. Three properties
follow from that shape, and they are the reasons to prefer it for browser-facing traffic:
the identifier carries no information, so leaking it reveals nothing beyond itself; the
record is a row you can delete, so revocation is immediate; and the browser can be made
unable to read the identifier from script.

A self-contained token in the browser has none of the three. That is a legitimate trade
for service-to-service traffic where the verifier has no shared store and lifetimes are
minutes. It is rarely the right trade for a browser, and the tell of a design that has not
thought about it is a refresh token in `localStorage` with a multi-week lifetime.

The relevant requirements live in OWASP ASVS, Session Management chapter — version 4.0.3
(October 2021) numbers it V3. Chapter numbering changed in the 5.x line, so cite the
requirement text rather than the number if your copy is newer, and check which version you
are reading before quoting a number at a reviewer.

## Every point at which the identifier rotates

Rotation means: create a new identifier, copy the authenticated state onto it, invalidate
the old record server-side, and set the new cookie. Invalidating the old record is the half
that gets missed; without it, rotation issues a second valid session rather than replacing
one.

| Event | Why |
| --- | --- |
| Login | Session fixation. An identifier the browser held before authentication and keeps after it is an authenticated session for whoever planted it. |
| Step-up or re-authentication | The session's privilege level has changed, so the artefact that represents it should change too. |
| Entering an impersonation or support-view mode | The elevated session and the ordinary one should not share an identifier, so revoking one does not depend on remembering the other. |
| Leaving impersonation | Same reason, in reverse. |
| Password change, MFA enrolment, MFA removal | Rotate this session and terminate every other session for the user. This is the moment a user acts on a suspected compromise. |
| Email address change | The recovery path just changed owner. Treat it like a credential change. |

How fixation is set up in practice, so you can recognise the preconditions: an application
that accepts a session identifier from a URL or a request parameter, a cookie set for a
parent domain by a host the attacker controls, or any place the application echoes an
identifier it was given rather than one it generated. Closing those helps; rotating on
login closes the class.

## Session identifier properties

- Generated from a cryptographically secure random source. A counter, a hash of the user
  id, or anything derived from user data is guessable in a way nobody notices.
- At least 128 bits of entropy is a comfortable target; ASVS sets its floor at 64 bits,
  and there is no reason to sit on the floor.
- Opaque. It carries no user id, no role, no timestamp — anything the server needs is on
  the record.
- Never in a URL, a referrer, a log line or an error report. Cookie only. A session in a
  URL leaks through every link the user shares and every referrer header the browser sends.
- Framework-generated. Use the platform's session mechanism rather than a hand-rolled one;
  this is another instance of the first hard gate.

## Cookie attributes in full

```http
Set-Cookie: __Host-session=OPAQUE_VALUE; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=28800
```

| Attribute | Effect | The reason |
| --- | --- | --- |
| `Secure` | Sent only over HTTPS | One plaintext request — an old bookmark, a hardcoded `http://` link, a captive portal — otherwise puts the session on the wire. HSTS narrows this but does not cover the first request to a host that is not preloaded. |
| `HttpOnly` | Not readable from `document.cookie` | Limits theft under cross-site scripting. It does not prevent injected script from issuing authenticated requests with the cookie attached, so treat it as reducing the blast radius of an injection, not as a defence against one. |
| `SameSite=Lax` | Withheld on cross-site subresource requests and cross-site form posts; sent on top-level GET navigation | Removes most cross-site request forgery without breaking inbound links. The gap is the state-changing GET, which is a reason not to have one. |
| `SameSite=Strict` | Withheld even on inbound top-level navigation | The user arrives from an external link logged out. Right for an administrative console; a bug report generator for a consumer product. A two-cookie pattern — a `Strict` cookie for sensitive operations alongside a `Lax` session — gets both, at the cost of explaining it. |
| `SameSite=None` | Sent cross-site; requires `Secure` | Only when you genuinely serve an embedded or cross-site client. Write down what that client is, because this is also the value that appears when someone was making a third-party embed work. |
| `Path=/` | Scope | Path is not a security boundary — another path on the same origin can read the cookie through script. Do not use it as one. |
| No `Domain` | Host-only cookie | Setting `Domain=example.com` shares the session with every subdomain including the ones run by other teams or by a vendor. Host-only is the default; leaving it alone is the decision. |
| `__Host-` prefix | Browser enforces `Secure`, no `Domain`, `Path=/` | Stops a sibling or compromised subdomain from setting a cookie your application will accept — cookie-forcing, which is fixation's cousin and defeats the double-submit variety of anti-forgery token. |
| `__Secure-` prefix | Browser enforces `Secure` | The weaker prefix, for when you genuinely need a `Domain` attribute. |
| `Max-Age` / `Expires` | Persistence | Omit both for a session cookie that dies with the browser. Server-side expiry is the authority either way; the client-side value is a hint the browser may ignore. |

Cookie prefixes and the `SameSite` attribute are specified in the ongoing revision of
RFC 6265 (April 2011) rather than in RFC 6265 itself. The revision is a draft, so cite it
as one if you cite it at all; browser support for the prefixes and for `Lax` defaults is
the practical authority, and it is broad.

## Where SameSite does not reach

The single most consequential detail: **`SameSite` is scoped to the registrable domain, not
to the origin.** A cookie on `app.example.com` is same-site with `blog.example.com`,
`status.example.com` and anything else under `example.com`, including a host running
vendor software, a host serving user-uploaded content, and a subdomain whose DNS record
outlived the service it pointed at. Where subdomains are numerous or not all yours,
`SameSite` is a good default and anti-forgery tokens are still required on state-changing
requests.

Three further limits worth knowing:

- It does nothing about cross-site scripting. Same-origin script gets the cookie attached
  to its requests regardless of the attribute.
- It does nothing for a non-browser client. An attacker's own HTTP client sets whatever
  headers it likes; `SameSite` is a browser behaviour protecting a user's browser.
- Browsers have carried compatibility exceptions to `Lax` for recently created cookies on
  top-level cross-site POST. Check the current behaviour of the browsers you support before
  either relying on the exception or assuming it is gone.

## Timeouts, idle and absolute

Both, for different threats. The idle timeout bounds an unattended browser and a session
left open on a shared machine; the absolute timeout bounds a stolen identifier, because it
is the only one an active attacker cannot keep resetting.

| Application | Idle | Absolute |
| --- | --- | --- |
| Consumer product, low value | Hours to days | 7 to 30 days with a persistent cookie the user opted into |
| Business application with customer data | 30 minutes to a few hours | 8 to 24 hours |
| Administrative console, payments, anything with bulk access | 10 to 30 minutes | One working day, plus step-up at the dangerous action |

The alternative to a punishing timeout is step-up authentication at the operation that
matters — re-authenticate before changing a payout account, exporting the customer table,
or disabling logging — which gives you the protection where it counts without training
users to keep a tab refreshing to stay logged in.

## Logout, and sign out everywhere

Logout deletes the server-side record first, then clears the cookie. Clearing the cookie
alone logs out a cooperative browser and leaves every copy of the identifier working,
which is the opposite of what the user asked for.

Clear the cookie with the same attributes it was set with — same path, same prefix, same
host-only scoping — or the browser keeps the original and the user stays logged in in a way
that is very hard to reproduce.

"Sign out everywhere" needs a session record per user that can be listed: identifier,
creation time, last seen, source address, user agent, and a label the user can recognise.
Offer it in account settings, invoke it automatically on password change, and make it
available to support, because it is the control a user reaches for during their own
incident. It is also what makes your incident response possible at all: without it,
containing a compromised account means waiting for tokens to expire.

Where sessions come from a federated provider, front-channel and back-channel logout
propagate the provider's logout to you. Both are worth implementing, and neither removes
the need to delete your own records — the provider's notification tells you to act, it does
not act for you.

## The backend-for-frontend pattern

For a single-page application, put a small server-side component in front:

1. The browser calls your backend-for-frontend, never the identity provider directly.
2. It completes the authorization code flow with PKCE and holds the access and refresh
   tokens server-side, keyed by the session.
3. It sets an opaque, `HttpOnly`, `Secure`, `SameSite=Lax`, `__Host-` prefixed cookie.
4. It proxies API calls, attaching the access token server-side and refreshing as needed.

What this buys: the browser never holds a bearer token, so "where do we store the token"
stops being a question with no good answer; revocation is a row delete; refresh rotation
happens somewhere with a real place to store state. What it costs: a component to run, a
proxy hop, and anti-forgery handling on the proxy's own endpoints, since it is now
cookie-authenticated. For most products that is the better trade, and it is worth stating
explicitly in the design so nobody relitigates it.

## Binding a session to a device

Record the source address and user agent per session and surface them in the session list
and in security notification emails. Do not hard-bind the session to them: mobile networks
change address mid-request, corporate proxies rotate, and user agent strings change on
browser update, so hard binding produces support load and unexplained logouts while an
attacker on the same network is unaffected.

The mechanism that does bind is cryptographic rather than heuristic — DPoP or
mutual-TLS-bound tokens for APIs, and platform device-bound session credentials where the
browser offers them. Treat the address and user agent as material for detection and alerts,
not as an access control.

## Verification

- The session cookie changes value across login, and the pre-login identifier is rejected
  afterwards.
- The cookie carries `Secure`, `HttpOnly`, a `SameSite` value you chose deliberately, and
  the `__Host-` prefix where nothing requires a `Domain`.
- No `Set-Cookie` for the session anywhere without `HttpOnly` — grep the responses rather
  than the code, since frameworks set cookies you did not write.
- Logout: keep the cookie value, replay an authenticated request, confirm it fails.
- Password change terminates other sessions. Log in from two browsers and check.
- No session identifier appears in any URL, access log, or error report.
- A state-changing request with no anti-forgery token fails, in the subdomain-heavy case
  where `SameSite` is not sufficient on its own.
