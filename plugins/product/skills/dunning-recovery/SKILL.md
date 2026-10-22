---
name: dunning-recovery
description: "Recover failed subscription payments before they become churn: measure the involuntary share of churn first, retry by decline code (soft declines retried on a spaced schedule, hard declines sent to the customer), switch on a card account updater, send pre-expiry notices, run a three-email sequence over 14 days with an in-app banner, hold a grace period before access changes, and report recovered MRR per stage. Use this skill whenever someone mentions \"failed payments\", \"involuntary churn\", \"card declines at renewal\", \"dunning emails\", \"past-due subscriptions\" or \"customers churning because their card expired\". Not for customers choosing to cancel (churn-analysis), an angry account threatening to leave (escalated-account-recovery), a household's own bills and budget (personal-finance), or a payment service that is down right now (incident-response)."
allowed-tools: Read, Grep, Glob
---

# Dunning Recovery

Dunning is done well when every failed renewal is routed by its decline code, the payments that can recover without the customer do so silently, the customers who must act are told clearly, early and through the right channel, nobody loses access while a recovery is still likely, and the team can say how much recurring revenue each stage recovered last month.

The usual failure is a single generic setup: retry the card a fixed number of times, send one "your payment failed" email to whoever signed up, cancel the subscription. Retrying a card reported stolen never succeeds and can breach card network rules; retrying an insufficient-funds decline at the wrong moment wastes the attempt; the person who signed up two years ago has left the company; and the customer who would happily have paid finds their account cancelled. Involuntary churn is often the cheapest churn to win back, because the customer never decided to leave.

## Scope

Use for: designing or fixing the process for failed recurring payments; retry schedules; dunning emails and banners; card-updater and pre-expiry handling; grace periods; reporting on recovered revenue.

Do not use for: customers who chose to cancel (`churn-analysis`); a key account that is angry rather than unpaid (`escalated-account-recovery`); a person's own household finances (`personal-finance`); a payment provider or billing service that is failing right now for everyone (`incident-response`).

## Workflow

### 1. Measure the involuntary share first

Before changing anything, compute for the last three to six months:

- Recurring revenue lost to payments that failed and were never recovered, as a share of all churned recurring revenue. Industry figures often put involuntary churn at 20 to 40% of subscription churn; measure yours rather than assume it.
- The failure rate of renewal charges, and today's recovery rate (failed revenue later collected, divided by failed revenue).
- Failures broken down by decline code, card brand, issuing country, plan and billing interval.

If the involuntary share is small, effort belongs in `churn-analysis` instead. If it is large, the breakdown shows where: a pile of expired cards points at the updater and pre-expiry notices; a pile of insufficient-funds declines points at retry timing.

### 2. Route by decline code

Every failure carries a code from the processor. Group them into three routes:

| Route | Typical codes (Stripe names; other processors have equivalents) | Action |
| --- | --- | --- |
| Soft: may succeed later without the customer | `insufficient_funds`, `try_again_later`, `processing_error`, `generic_decline`, `do_not_honor`, `card_velocity_exceeded`, `approve_with_id` | Retry on a schedule; start the customer sequence in parallel |
| Hard: will not succeed on this card | `lost_card`, `stolen_card`, `pickup_card`, `fraudulent`, `expired_card`, `incorrect_number`, `invalid_account`, `restricted_card`, `card_not_supported`, `transaction_not_allowed`, `revocation_of_authorization`, `stop_payment_order` | Do not retry the same details; ask the customer for a new payment method |
| Customer action needed | `authentication_required` | Send the customer to a page where they can complete authentication; retries without it fail |

Card networks restrict re-attempting declines the issuer marks as final and cap repeated attempts on the same card, with fees for breaches. Your processor publishes the current limits; check them before setting a schedule. Bank debits have their own return codes (for SEPA, AM04 is insufficient funds and MD01 is no valid mandate) and their own re-presentment rules; route them the same way. Never tell a customer their card was reported lost, stolen or fraudulent; say the payment was declined and ask them to update their details or contact their bank.

`references/dunning-playbook.md` has the fuller decline-code table, an example retry schedule, the email and banner copy, and the reporting table. Read it when building the schedule or the messages.

### 3. Retry soft declines on a spaced schedule

Spread a small number of retries across the dunning window rather than retrying daily. For `insufficient_funds`, time retries near when money is likely to arrive (shortly after common pay dates in the customer's country, or the start of a month). If you use the processor's own automated retry timing (Stripe calls it Smart Retries), let it set the timing but keep the window and the cap your own. Stop retrying the moment the customer adds a new method, and charge that instead.

### 4. Keep card details current without the customer

Switch on account updater through your processor: Visa Account Updater, Mastercard Automatic Billing Updater and the equivalents from other networks pass new card numbers and expiry dates from issuers to merchants. Network tokens, where the processor supports them, keep the credential current in a similar way. Both quietly prevent many `expired_card` failures. Coverage is not universal across brands and countries; check it in the processor's reporting where it is offered.

### 5. Send pre-expiry notices

For cards the updater did not refresh, email the billing contact about 30 days before the expiry month ends, and again about 7 days before, with a direct link to update the card. A card replaced before it fails costs nothing to recover.

### 6. Run the customer sequence: three emails over 14 days, plus a banner

From the first failure, in parallel with retries:

- **Email 1, day 0:** neutral and short. The payment did not go through, here is a one-click link to update the method, nothing changes yet.
- **Email 2, around day 5 to 7:** a reminder with the date access will change.
- **Email 3, around day 12 to 14:** final notice with the exact date and what will happen, and a direct contact.
- **In-app banner from day 0**, shown only to people who can pay (account owners and billing admins), with the same link. Showing it to every user embarrasses the customer and reaches people who cannot act.

Send to the billing contact and the account owner, not only the person who signed up. The update link should work without a password reset where your security model allows a signed, expiring link; every extra step loses customers who meant to pay. For large accounts, add a call or message from the account owner before email 3.

### 7. Hold a grace period before access changes

Keep access unchanged throughout the sequence. When it ends without payment, restrict rather than delete: read-only or paused, with data kept for a stated period and reactivation that restores everything the moment payment succeeds. Map this onto your billing system's states (in Stripe, for example, a subscription moves through `past_due` and can be set to `unpaid` or cancelled when retries are exhausted) and choose deliberately rather than accepting the default.

### 8. Report recovered revenue per stage

Each month, report the failed recurring revenue entering dunning and where it went: recovered by a retry on the same details, by the updater, by a new payment method added after email 1, 2 or 3, through the banner or the account team, and lost. Attribute each recovery to the mechanism that produced it, not to the time window: a soft-decline retry that succeeds on day 3 is a retry recovery, not an email 1 recovery. The per-stage view shows which change to test next; a single recovery rate does not.

Change one element at a time (the timing of email 2, the banner wording, a retry date) and compare recovery rates across monthly cohorts of failures, so the effect of each change is visible.

## What to hand back

- The involuntary share of churn, the failure rate and today's recovery rate, with the breakdown by decline code.
- The routing table and retry schedule in use, checked against the processor's limits.
- The updater and pre-expiry settings, the email and banner sequence, and the grace-period rules.
- The per-stage recovery report and the next change to test.

## Anti-patterns

**Retrying hard declines.** A stolen card never approves; repeated attempts risk network fees and teach the issuer to distrust you.

**Emailing only the person who signed up.** In business accounts that person has often left. The billing contact and the owner are who can pay.

**Cancelling at the first failure.** The customer who meant to pay now has to sign up again, and many will not.

**Telling the customer why the bank declined.** "Your card was reported stolen" is not yours to say and may be wrong; a neutral message and a link is enough.

**One blended recovery rate.** It cannot say whether the updater, the retries or the emails are doing the work, so nobody knows what to improve.

## Reference files

- `references/dunning-playbook.md` — read when building the retry schedule or the messages: the decline-code routing table, an example 14-day schedule, email and banner copy, and the monthly per-stage reporting table.
