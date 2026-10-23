---
name: csp-report-only-rollout
description: "Introduce a Content-Security-Policy without breaking the site: start with Content-Security-Policy-Report-Only and a hardened report endpoint, read about two weeks of violation reports grouped by directive, blocked source and page, move scripts to per-response nonces or hashes with strict-dynamic rather than a host allow-list, enforce path by path starting with the least risky, and keep a stricter report-only policy running beside the enforced one. Use when someone says \"add a CSP\", \"the scanner says we have no CSP\", \"the pentest flagged unsafe-inline\", \"CSP broke our analytics\" or \"is our long list of allowed domains actually protecting us\". Not for reviewing a diff for XSS or injection (security-review), server or TLS hardening (host-hardening), session and cookie design (auth-design), or a whole-site audit (website-builder)."
allowed-tools: Read, Grep, Glob
---

# CSP Report-Only Rollout

Done means an enforced policy under which a script injected into the page does
not run, no legitimate feature blocked, a report stream that is quiet enough to alert on,
and a stricter policy already collecting reports for the next step.

The usual failure runs the other way. A policy is written from memory and enforced, it
blocks checkout or analytics, it is rolled back in a hurry, and the team settles on
`script-src 'self' 'unsafe-inline'` plus every domain that complained. That policy passes
the scanner and stops almost nothing, because `'unsafe-inline'` lets an injected inline
script run and allow-listed domains usually host something an attacker can load.

This is defensive procedure for a site you operate. It is not a substitute for fixing
the injection itself, which is `security-review`.

## Scope

Use for: a first CSP, replacing an allow-list or `'unsafe-inline'` policy, triaging
violation reports, and adding third-party scripts under an existing policy.

Do not use for: reviewing a change for XSS or injection (`security-review`), TLS and
server configuration (`host-hardening`), cookie and session attributes (`auth-design`),
or a whole-site audit across performance, SEO and security (`website-builder`).

## Workflow

### 1. Inventory what the policy will meet

Record the current headers and every way script reaches the page.

```bash
curl -sIL https://www.example.com/ | grep -iE '^(content-security-policy|reporting-endpoints|report-to)'
```

`-L` matters because a home page often redirects to a locale or login path, and a policy
set only on the final HTML is absent from the redirect. The skill does not pre-approve
`curl`, because it also reads violation reports, which are text anyone can post; the user
approves each request.

In the codebase, look for: inline `<script>` blocks, inline event handler attributes
(`onclick="..."` in HTML or templates; a JSX `onClick={...}` is not one), `javascript`-scheme
URLs, `eval`, `new Function` and string arguments to `setTimeout`, tag managers and
other third-party loaders, and a `<meta http-equiv="Content-Security-Policy">` that would
combine with the header. List the page groups (marketing, sign-in, app, checkout, admin)
with their owners: enforcement goes group by group in step 6.

### 2. Stand up the report endpoint first

Browsers post reports to an unauthenticated public URL, so anyone can post anything to
it. Before pointing a policy at it:

- Accept both formats: `application/csp-report` from `report-uri`, and
  `application/reports+json` from the Reporting API (`report-to`).
- Cap body size, rate-limit per client, and sample if traffic is high.
- Store reports as data; escape every field before showing it in a dashboard, because
  report contents are attacker-controlled text.
- Strip query strings and fragments from page and blocked URLs before storage; they can
  carry tokens and personal data.

Declare both mechanisms, because support differs between browsers:
`report-uri /csp-reports; report-to csp` with a
`Reporting-Endpoints: csp="https://www.example.com/csp-reports"` response header.

### 3. Ship the target policy in report-only

Send the policy you intend to enforce, not a loose one, in
`Content-Security-Policy-Report-Only`. Its reports are the work list. Report-only has no
effect in a `<meta>` tag, so it must be a response header.

```text
Content-Security-Policy-Report-Only:
  script-src 'nonce-RANDOM' 'strict-dynamic' 'report-sample' https: 'unsafe-inline';
  object-src 'none'; base-uri 'none';
  report-uri /csp-reports; report-to csp
```

Browsers that support nonces and `'strict-dynamic'` ignore `https:` and `'unsafe-inline'`
in this policy; those two are there only for old browsers that would otherwise block
everything. `'report-sample'` adds the first 40 characters of a blocked inline script to
the report, which is usually enough to find it in the code.

### 4. Move scripts to nonces or hashes

- **Nonces for server-rendered pages.** Generate a fresh value per response from a
  cryptographically secure generator, at least 128 bits, base64-encoded; put it in the
  header and on every `<script>` the server emits. A page with a nonce must not be
  stored in a shared cache and served to others, or the nonce becomes predictable.
- **Hashes for static or edge-cached pages.** Hash each inline script's exact content
  (`'sha256-...'`); the command is in `references/policies-and-reports.md`.
- **`'strict-dynamic'` for loaders.** A script trusted by nonce or hash may add further
  scripts with `document.createElement('script')`, and those are trusted too. Give the
  tag manager's or widget's loader the nonce rather than listing its domains.
  Parser-inserted scripts (`document.write`) do not inherit trust.
- **Refactor what no policy should allow.** Inline event handlers become
  `addEventListener`; `javascript`-scheme URLs become buttons; `eval` and `new Function` are
  removed, or `'unsafe-eval'` is recorded as a named, owned exception.

Do not replace `'unsafe-inline'` with a host allow-list. Allow-listed domains commonly
serve JSONP endpoints or old libraries that run attacker-chosen code within the policy;
Google's 2016 study of deployed policies, "CSP Is Dead, Long Live CSP!", found the large
majority of allow-list policies bypassable.

### 5. Read two weeks of reports

Two weeks covers two weekly cycles and gives rarely visited pages time to report;
extend it for a flow that only runs monthly, such as billing. Group by effective directive, blocked source without its query
string, and page group; the queries are in `references/policies-and-reports.md`. Drop
the noise first: reports whose source is a browser extension (`chrome-extension`,
`moz-extension`, `safari-web-extension`, often reported as the bare scheme) are about the
user's browser, not your site
(`references/noise-and-third-parties.md` lists the patterns).

Give every remaining group one decision: fix the code, add a nonce or hash, accept with a
written reason, or confirm it is an attack or noise. The gate for a page group is two
weeks with no unexplained reports after its last fix.

### 6. Enforce one page group at a time

Start where breakage is cheapest and coverage is simplest, usually marketing or
documentation pages, and finish with checkout and admin. For each group, move the policy
from the report-only header to `Content-Security-Policy`, keep `report-uri` and
`report-to` on it, and watch the report rate for that group for a full traffic cycle.
Roll back by changing the header in configuration, not by reverting code, so rollback
takes minutes.

### 7. Keep a stricter policy in report-only beside it

A response may carry both headers at once: the enforced policy and a stricter
report-only one. Use the second to measure the next step: dropping the `https:` and
`'unsafe-inline'` fallbacks, adding `require-trusted-types-for 'script'` where browser
support allows, `frame-ancestors`, `form-action`, or a `style-src` policy. Promote it
through steps 5 and 6 when its reports are clean.

## Output format

1. **Inventory** — page groups with owners, inline scripts, handlers, eval uses, third
   parties.
2. **Endpoint** — formats accepted, limits, storage and redaction.
3. **Policies** — the enforced and the report-only text, per page group.
4. **Report triage** — each group of reports with its decision and owner.
5. **Enforcement log** — group, date enforced, report rate before and after, rollback
   path.

## Anti-patterns

**Enforcing first.** It turns the policy into an outage, and the outage produces the weak
policy that ends up shipping.

**`'unsafe-inline'` with a nonce, read as a hole.** In a browser that supports nonces it
is ignored; the hole is `'unsafe-inline'` without one.

**A nonce in cached HTML.** One value shared by every visitor is a value an attacker can
read and reuse.

**Adding every complaining domain.** Each one is a place the policy can be bypassed from,
and the list never shrinks.

**Rendering reports unescaped.** The endpoint takes text from anyone; a dashboard that
renders it as HTML is a new injection point.
