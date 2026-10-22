# Dunning playbook

## Contents

- Decline-code routing
- Example 14-day schedule
- Pre-expiry notice
- Email sequence
- In-app banner
- Grace period and access
- Monthly per-stage report

## Decline-code routing

Stripe's `decline_code` values are used as the example vocabulary; Braintree, Adyen and
others return equivalent processor or issuer response codes. Map yours onto the same
three routes, and check your processor's documentation for any code not listed.

| Code | Route | Notes |
| --- | --- | --- |
| `insufficient_funds` | Soft | Time retries near likely pay dates |
| `try_again_later`, `processing_error` | Soft | Transient; an early retry often succeeds |
| `generic_decline`, `do_not_honor` | Soft, capped | Issuer gave no reason; retry a few times, then treat as needing the customer |
| `card_velocity_exceeded`, `withdrawal_count_limit_exceeded` | Soft | A limit was hit; retry after the limit period |
| `approve_with_id` | Soft | Issuer could not authorise this attempt; retry |
| `call_issuer` | Customer action | The customer needs to contact their bank |
| `authentication_required` | Customer action | Needs strong customer authentication; send them to an authentication page |
| `expired_card` | Hard | Updater may refresh it; otherwise new details needed |
| `incorrect_number`, `invalid_account` | Hard | New details needed |
| `lost_card`, `stolen_card`, `pickup_card`, `fraudulent` | Hard | Do not retry; do not tell the customer the specific reason |
| `restricted_card`, `card_not_supported`, `transaction_not_allowed`, `currency_not_supported` | Hard | A different method is needed |
| `revocation_of_authorization`, `stop_payment_order` | Hard | The customer stopped the payment; treat as a possible cancellation and contact them |

## Example 14-day schedule

Adjust to your processor's retry limits and your billing interval. Day 0 is the first
failed renewal.

| Day | Retry (soft only) | Customer touch |
| --- | --- | --- |
| 0 | First attempt fails | Email 1; banner on for owners and billing admins |
| 1 | Retry | |
| 3 | Retry | |
| 6 | | Email 2 |
| 7 | Retry, moved to just after a likely pay date if within two days | |
| 10 | Retry | Account owner contacts large accounts |
| 13 | | Email 3, final notice |
| 14 | Last retry | Sequence ends; access changes per the grace-period rules |

Hard declines get the customer touches and no retries on the same details. Any new
payment method added during the sequence is charged at once and the sequence stops.

## Pre-expiry notice

```text
Subject: Your card ending [1234] expires at the end of [month]

The card we charge for [product] expires soon. To avoid any interruption, update it
here: [signed link]. It takes under a minute, and nothing changes on your account.
```

Send about 30 days before the expiry month ends and again about 7 days before, only
for cards the account updater has not already refreshed.

## Email sequence

Plain, short, one link, no blame. Send to the billing contact and the account owner.

Email 1, day 0:

```text
Subject: Your [product] payment did not go through

We tried to collect [amount] for your [plan] subscription on [date], and the payment
was declined. Nothing has changed on your account.

Update your payment method: [signed link]

If you think this is a mistake, your bank can tell you more about the decline.
```

Email 2, around day 6:

```text
Subject: Action needed: update your payment for [product]

We still have not been able to collect [amount]. Your account stays fully active
until [date]. After that, it will become read-only until payment is made.

Update your payment method: [signed link]
```

Email 3, around day 13:

```text
Subject: Final notice: [product] access changes on [date]

On [date] your account will become read-only. Your data is kept for [period] and
everything returns as soon as payment goes through.

Update your payment method: [signed link]
Questions? Reply to this email or contact [name, channel].
```

## In-app banner

Shown only to account owners and billing admins, from day 0 until payment succeeds:

```text
Your last payment was declined. Update your payment method to keep [product] running
after [date]. [Update payment]
```

Other users see nothing until access changes, and then a message that names who in
their organisation can resolve it.

## Grace period and access

| Stage | Access | Data | Billing state (Stripe example) |
| --- | --- | --- | --- |
| Days 0 to 14 | Unchanged | Kept | `past_due` |
| After sequence | Read-only or paused | Kept for a stated period | `unpaid`, or cancelled if that is your chosen setting |
| After retention period | Closed | Deleted per your data policy, with notice | Cancelled |

Reactivation on payment must restore access immediately, without support involvement.

## Monthly per-stage report

| Stage | Failed MRR entering | Recovered MRR | Share of failed MRR |
| --- | --- | --- | --- |
| Retry succeeded on the same details | | | |
| Account updater refreshed the card | | | |
| Customer added a new method after email 1 | | | |
| Customer added a new method after email 2 | | | |
| Customer added a new method after email 3 | | | |
| Banner or account team prompted the update | | | |
| Paid after the sequence ended (reactivation) | | | |
| Lost | | | |
| **Total** | | | |

Each failure is counted in exactly one row, the mechanism that produced the successful
payment (a silent retry is credited to retry, not to whichever email went out before it), so the shares sum to 100%. Add the involuntary share of total churn and the month-on-month change in recovery rate
beneath the table, and note the one change being tested this month.
