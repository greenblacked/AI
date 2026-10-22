---
name: synthetic-monitoring-design
description: "Design synthetic probes and journey checks that find outages real-user metrics cannot, and triage the ones that page for no reason: probe journeys where silence costs money (login, checkout) asserting on content or a state change rather than a 200; at least three external locations with paging on a quorum; a dedicated test tenant, a recognisable header and a cleanup step; the prober treated as a service with its own success rate; at most one false page a month, with each failed run classified by cause before the check is touched. Use this skill whenever someone says \"set up uptime monitoring\", \"Blackbox exporter or Checkly checks\", \"monitor login and checkout from outside\", \"our uptime probe false alarms\" or \"the synthetic test is red but the site is fine\". Not for the objective itself (slo-design), burn-rate paging (alert-design), or pre-release browser tests (e2e-testing)."
allowed-tools: Read, Glob, Grep, Edit
---

# Synthetic Monitoring Design

Done means a small set of journey checks that fail when users cannot complete something that matters, page only when several locations agree, are excluded from business analytics and fraud rules, and produce at most one false page a month.

The usual failure is probing the homepage for a 200. The CDN answers it while login is down. The second failure is a check that pages on a single location's blip, gets muted after the third false alarm, and is then silent during a real outage. A muted check is worse than none, because the team believes it is covered.

## Scope

Use for: external probes (HTTP, TCP, DNS, TLS, scripted browser or API journeys), their placement, assertions, paging and false-alarm triage.

Do not use for: choosing the service's objective (`slo-design`, which mentions probes only for low-traffic services), burn-rate paging rules (`alert-design`), or tests that run before release (`e2e-testing`). CI flakiness belongs with `e2e-testing`.

## Workflow

### 1. Choose journeys by what silence costs

List the few paths where an unnoticed failure costs money or trust: sign in, search, add to basket and pay, the API call a partner depends on, password reset email arrival. Keep it to a handful; each check is something you operate. Real-user metrics cover everything that has traffic. A synthetic check earns its place where traffic is low (night hours, a rarely used region), where failure keeps users from ever producing a metric (DNS, certificate, edge outage, the login page not loading) or where the dependency is outside your telemetry.

Synthetics complement the real-user SLI. They do not replace it, and they should not define availability by themselves.

### 2. Assert on content or a state change

A status 200 proves that something answered. Assert what the user needs: a string or element only present on a working page, a JSON field with the right value, a record created and then readable, an email received. Check response time against a threshold, as a separate assertion with its own message so a slow success is distinguishable from a failure.

Tool choice follows the journey. The Blackbox exporter probes single requests (HTTP with body matching through `fail_if_body_not_matches_regexp` and `valid_status_codes`, TCP, ICMP, DNS) and exposes `probe_success`, `probe_duration_seconds` and `probe_http_status_code`; it cannot run a multi-step browser journey. Scripted browser or API checks (Playwright-based services such as Checkly, or a k6 script) cover multi-step flows. Read `references/probe-config-and-triage.md` for configuration shapes.

### 3. Run from several locations and page on a quorum

Run each check from at least three external locations, ideally on more than one provider, so that one provider's network problem is a single vote. Page when a majority fail within the same short window, and do the retry from a different location before counting a failure. A single-location failure goes to a ticket queue or a dashboard, not a pager. Label every result with its `location` so the alert can count them.

### 4. Make the probe a good citizen

- A dedicated test tenant and account, with limited rights and nothing that touches real customers or real money; pay with the payment provider's test mode where the journey allows, or stop one step before charging.
- A recognisable user agent or request header on every probe request, so analytics, rate limits, bot rules and fraud scoring can exclude or allow-list it. Agree the rule with the owners of each, in writing.
- A cleanup step that deletes or resets what the run created, and a unique run identifier in every created record, so a failed run does not leave data that breaks the next one.
- Credentials for the test account held in the checker's secret store and rotated like any other.

### 5. Monitor the prober

The prober is a service with its own success rate. Alert separately when a location stops reporting (`up` for the exporter, or no results for longer than twice the interval), when a location's failure rate departs from the others, and when a check's results disappear entirely. Without this, a dead prober looks like a healthy site.

### 6. Triage false pages by cause before touching the check

Set a target of at most one false page a month. Each failed run is classified before any change is made, using 30 days of results grouped by location, hour of day and failing step:

| Cause | Typical signature |
| --- | --- |
| One location or provider | Fails in one location only, often at a fixed hour |
| WAF or bot rules | HTTP 403 or a challenge page, started after a rule change |
| Third-party script timing out | Fails on a step that waits for a tag, chat widget or analytics script |
| Brittle selector or fixed sleep | Fails after a front-end release or on slow runs |
| Test data mutated by a previous run | Fails on the step that reads data created earlier |
| Genuine intermittent outage | Real errors visible in real-user metrics at the same time |

Fix the cause the table names: allow-list the probe, wait for the element or state rather than sleeping, make the data self-contained per run, block the third-party script in the test. Tighten rather than loosen: widening a timeout or adding retries to hide a cause only delays the pager, whereas a genuine intermittent outage found in the last row is a real finding to hand to `incident-response`. A check that cannot meet the target after the causes are fixed is deleted, and the gap is covered by real-user metrics.

## Anti-patterns

**A homepage check as the uptime signal.** It tests the edge, not the product.

**Paging on one location.** It trains the team to ignore the pager.

**Probing with a real customer account.** It produces real orders, emails and fraud flags.

**Raising the retry count until it goes green.** The cause remains and the detection time grows.

**Leaving the prober unmonitored.** A silent prober is indistinguishable from a quiet site.

## What to hand back

The journeys chosen with the cost of silence for each, the assertions, locations and paging quorum, the test tenant and probe identification agreed with analytics and fraud owners, the prober's own alerts, and the 30-day classification of failures by cause with the changes made and checks deleted.

## Reference files

- `references/probe-config-and-triage.md` — read when configuring checks or classifying failures: a Blackbox exporter module, a quorum alert, the prober-health alert and a triage query worksheet.
