# The lifetime schedule

The dates and figures below are what the workflow's step 4 schedules against. Each is
attributed to its primary source so a stakeholder conversation can point at the source
rather than at this file.

## CA/Browser Forum Baseline Requirements

Ballot SC-081, "Introduce Schedule of Reducing Validity and Data Reuse Periods," was
adopted 2025-04-11. It sets a schedule of four maximum certificate validity periods,
keyed to the certificate's issuance date:

| Certificate issued | Maximum validity |
| --- | --- |
| Before 2026-03-15 | 398 days |
| 2026-03-15 up to 2027-03-15 | 200 days |
| 2027-03-15 up to 2029-03-15 | 100 days |
| From 2029-03-15 | 47 days |

The same ballot shortens how long domain-validation evidence can be reused before a CA
has to re-verify control of the domain, on the same three effective dates:

| From | Domain-validation reuse period |
| --- | --- |
| 2026-03-15 | 200 days |
| 2027-03-15 | 100 days |
| 2029-03-15 | 10 days |

Both schedules are binding on every publicly trusted CA: every major root program,
Mozilla's included, requires Baseline Requirements compliance as a condition of
inclusion.

## Let's Encrypt

Let's Encrypt's default ("classic") certificate profile is valid for 90 days. Applying
this skill's lifetime-fraction rule to that duration means renewing 30 days before
expiry — a third of the lifetime remaining. Two additional profiles narrow validity
further, ahead of the 2029-03-15 cut to a 47-day Baseline Requirements ceiling:

| Profile | Validity | What the lifetime-fraction rule yields |
| --- | --- | --- |
| `classic` (default) | 90 days | Renew 30 days before expiry (a third of the lifetime remaining) |
| `tlsserver` (opt-in) | 45 days | Exists explicitly to prepare subscribers for the eventual 47-day Baseline Requirements ceiling; renew 15 days before expiry |
| `shortlived` (opt-in) | 160 hours, described as "6ish days" | Under 10 days' validity, so the half-lifetime rule applies: renew 80 hours before expiry |

Let's Encrypt does not run an OCSP responder — its documentation states plainly that it
no longer provides an OCSP service. A client or appliance that still depends on OCSP for
revocation checking against a Let's Encrypt certificate has a dependency on a service
that does not exist; see this skill's OCSP-caching failure mode.

## ACME Renewal Information and the lifetime-fraction backstop

ACME Renewal Information (ARI) is the mechanism by which a CA tells a client when it
recommends renewing a given certificate, rather than the client guessing from a fixed
offset. ARI extends the ACME protocol, RFC 8555.

Let's Encrypt recommends checking ARI for each certificate at least twice a day, so that
a CA-initiated change in the recommended renewal time — a mass revocation, or a routine
policy change — reaches every client within hours rather than only at the certificate's
next scheduled check.

As a backstop where ARI is unavailable, or as the rule ARI itself falls back to, the
recommendation is to renew automatically once a third of the certificate's total
lifetime remains, or once half the lifetime remains for a certificate issued with a
validity under 10 days. `certbot` 4.0.0 (2025-04-07) implemented exactly this rule —
certificates now renew with a third of their lifetime left, or half if the total
lifetime is shorter than 10 days — and `certbot` 4.1.0 (2025-06-10) added automatic ARI
checking to `certbot renew`, which for a Let's Encrypt certificate typically causes
renewal at around two-thirds of the certificate's lifetime elapsed. That is a schedule
ARI computes and communicates itself, in place of the fixed `renew_before_expiry` value
recorded in each certificate's renewal configuration file before ARI checking existed.
