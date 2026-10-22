# Driver taxonomy

Read this when building or revising the contact-driver taxonomy: how to write a driver, a
starter set, the agreement check, sampling, and how to fold overlapping drivers.

## Contents

- Writing a driver
- A starter set for a subscription product
- The agreement check
- Sampling
- Folding and splitting drivers

## Writing a driver

A good driver is the customer's problem, specific enough that one team could remove it.

| Too broad | Too narrow | About right |
| --- | --- | --- |
| Billing | Invoice PDF missing VAT number for German customers on annual plan | Cannot find or download an invoice |
| Login | Reset email lands in spam on one mail provider | Password reset email not arriving |
| Integrations | Webhook retries on 502 from one endpoint | Integration stopped syncing |

Rules:

- Name the problem from the customer's side, not the product team's.
- One cause per driver. If a driver's name uses "or" to join two different causes, it is probably two drivers.
- Each driver gets a one-line definition and one example ticket, written into the
  taxonomy, so a new tagger can apply it without asking.
- Keep "other" and "unclear" as tags. Use them honestly rather than forcing a fit.

## A starter set for a subscription product

Adapt rather than adopt; the useful drivers are the ones specific to your product.

| Driver | Definition |
| --- | --- |
| Cannot sign in | Login fails for a reason other than a forgotten password |
| Password reset not arriving | Reset requested, email not received |
| Cannot find or download an invoice | Customer looking for a billing document |
| Unexpected charge | Customer does not recognise or disputes a charge |
| Payment failed | Card or payment method declined at renewal or purchase |
| Change plan or seats | Upgrade, downgrade or seat change the customer could not do alone |
| Cancel | Customer wants to cancel or asks how |
| Invite or remove a user | Team management the customer could not do alone |
| Data import failed | Import errors or partial imports |
| Integration stopped syncing | A connected system no longer updates |
| Export or report request | Customer needs data out in a form the product does not offer |
| Feature not found | Feature exists but the customer could not find it |
| Feature missing | Customer needs something the product does not do |
| Bug | Product behaves incorrectly and the agent confirmed it |
| Performance | Slow or timing out, outside a declared incident |
| Security or privacy request | Access, deletion, security question or report |
| How-to, other | Usage question not covered above |
| Other or unclear | Does not fit, or the ticket does not say |

Payment failures and cancellations belong in the taxonomy because they generate contacts,
but their analysis sits with the teams that own recovery and retention.

## The agreement check

Two people tag the same 50 tickets independently, then compare.

- Count the tickets where they chose the same driver. If they agree on fewer than roughly
  four in five, the definitions are too loose to tag at scale.
- For each disagreement, decide the correct tag and change the definition that allowed the
  other reading, not just the ticket.
- Repeat on a fresh 50 after changing the taxonomy.

Run the check again whenever a new tagger joins or drivers are added.

## Sampling

For ranking the top drivers, a simple random sample of several hundred tickets from the
month is usually enough, because the top drivers are large. Increase the sample when the
drivers you care about are rare, or when you need per-segment figures, since each segment
needs its own sample. Draw the sample across the whole month, not the first few days.

Report counts from a sample as estimates and say what the sample size was.

## Folding and splitting drivers

- **Fold** two drivers when taggers keep confusing them and they share a fix.
- **Split** a driver when it is in the top ten and contains two causes with different fixes.
- Keep a mapping from old to new drivers when you change the taxonomy, so the monthly trend
  survives the change. A taxonomy that is redrawn every month cannot show whether a fix
  worked.
