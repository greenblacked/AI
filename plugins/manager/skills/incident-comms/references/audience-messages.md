# One incident, five audiences

## Contents

- [The scenario](#the-scenario)
- [1. Status page post](#1-status-page-post)
- [2. Customer email to affected accounts](#2-customer-email-to-affected-accounts)
- [3. Executive brief](#3-executive-brief)
- [4. Internal all-staff message](#4-internal-all-staff-message)
- [5. Support macro and holding line](#5-support-macro-and-holding-line)
- [Translation rules](#translation-rules)
- [Phrases to strike](#phrases-to-strike)
- [The escalating-severity rewrite](#the-escalating-severity-rewrite)

## The scenario

Same facts throughout, so the differences between the five are purely about audience.

At 09:12 UTC a configuration change to the session store caused sign-in to fail for
customers whose accounts are hosted in the EU region. Roughly 4% of all accounts. Signed-in
sessions continued to work; only new sign-ins failed. Detected at 09:19 by an alert on
sign-in success rate. Mitigated by rolling back the change at 10:31; sign-in success rate
back to baseline by 10:40. Two enterprise accounts have contractual notification clauses.
No customer data was accessed, exposed or lost, and this was confirmed by 11:15.

Note what is deliberately withheld from every external message: the service name, the
identity of the change author, the specific configuration key, and the hypothesis held
between 09:30 and 10:05 that turned out to be wrong.

## 1. Status page post

The first post, published at 09:26 — fourteen minutes after impact, seven minutes after
detection, and well before diagnosis.

```text
[Investigating] Sign-in failures for EU-hosted accounts — 09:26 UTC

We are investigating an issue preventing some customers from signing in. Customers
whose accounts are hosted in the EU region may see an error when signing in.
Existing signed-in sessions are not affected.

Our team is actively working on this. Next update by 09:55 UTC.
```

The 09:55 update, when the cause is suspected but not confirmed:

```text
[Investigating] Sign-in failures for EU-hosted accounts — 09:55 UTC

What we know: The issue continues to affect new sign-ins for EU-hosted accounts.
Existing sessions remain unaffected. We have not identified a fix yet.
What we are doing: We have narrowed the issue to one part of our sign-in
infrastructure and are validating a mitigation.
What you can do: Existing sessions continue to work. If you are signed out, please
retry in a few minutes.

Next update by 10:25 UTC.
```

The resolution post:

```text
[Resolved] Sign-in failures for EU-hosted accounts — 10:47 UTC

Sign-in was unavailable for customers with EU-hosted accounts between 09:12 and
10:40 UTC, a duration of 88 minutes. Approximately 4% of accounts were affected.
Existing sessions were not affected and no customer data was affected.

Service is restored and we have confirmed normal sign-in success rates for the past
20 minutes. No action is needed from customers.

We will publish a detailed write-up by 12 March.
```

## 2. Customer email to affected accounts

Sent after resolution, to the affected segment only, from a monitored address.

```text
Subject: Sign-in disruption on 5 March, 09:12-10:40 UTC — what happened

Between 09:12 and 10:40 UTC on 5 March, customers with EU-hosted accounts were
unable to sign in. Sessions that were already signed in continued to work normally,
and no customer data was accessed, exposed or lost.

The cause was a configuration change we made to part of our sign-in infrastructure.
We rolled that change back and sign-in was fully restored at 10:40 UTC.

You do not need to take any action. If you are still seeing sign-in errors, please
reply to this email and we will pick it up directly.

We are publishing a full write-up by 12 March, including the changes we are making
so that this class of change cannot reach production unvalidated again. If your
agreement includes service credits, these will be applied automatically to your next
invoice — you do not need to claim them.

[Name], [Role]
```

What makes this different from the status page: it is addressed, it states plainly that
no data was affected, it names what the customer must do (nothing), and it settles credits
without making the customer ask.

## 3. Executive brief

Sent at 09:35, then hourly. Written for someone who may have to talk to the board, the
press, or the two largest affected accounts, and who has ten seconds.

```text
SEV 1 · Sign-in failures, EU accounts · 09:35 UTC · Update 1 of ongoing

Bottom line: New sign-ins are failing for EU-hosted accounts, about 4% of accounts,
since 09:12 UTC. Existing sessions unaffected. Mitigation being validated now.

Exposure:
- Customers: ~4% of accounts, EU region. Two enterprise accounts (Northwind, Certa)
  have 24-hour contractual notification clauses; account management engaged at 09:30.
- Revenue: no direct revenue path affected. SLA credit exposure being calculated;
  under the monthly availability threshold at this duration.
- Regulatory: no indication of data access or exposure. Legal notified at 09:28 as a
  precaution; DPO assessing whether any notification duty applies.
- Public: status page updated 09:26. No press or social escalation seen.

Decision needed from you: None. We will escalate if we pass 11:00 without mitigation,
at which point the decision is whether to fail EU sign-in over to the secondary region,
which carries its own risk of session loss.

Next update: 10:35 UTC, or immediately on material change.
Incident commander: [Name]. Comms lead: [Name].
```

The explicit "no decision needed from you" plus a named future decision point is what keeps
an executive from arriving in the response channel to help.

## 4. Internal all-staff message

Posted in the company-wide channel at declaration. Its job is to stop people making it
worse and to stop them asking responders for updates.

```text
SEV 1 declared 09:22 UTC — sign-in failures for EU-hosted accounts.

Deploys are frozen across all services until further notice. If you have a deploy in
flight, hold it and post in #inc-2025-03-05-signin.

Response is in #inc-2025-03-05-signin. Please read, do not post, unless you are asked
for something specific — the channel is the incident commander's working surface.

If a customer or partner asks you about this, point them to the status page and say
nothing beyond what is on it.

Customer status: status.example.com. Comms lead: [Name]. Next internal update 10:00 UTC.
```

Note the last instruction. Internal speculation reaches customers verbatim within the hour
via someone being helpful in a shared Slack channel, and it is indistinguishable from an
official statement once it has been pasted.

## 5. Support macro and holding line

Support needs something they can send without thinking, plus an explicit boundary on what
they may not say.

Holding line, for chat and phone:

```text
We are aware of an issue affecting sign-in for accounts hosted in the EU, and our
engineering team is working on it now. Existing sessions are not affected. I do not
have a resolution time yet, but our status page at status.example.com is updated at
least every 30 minutes and you can subscribe there for updates.
```

Macro, for tickets:

```text
Thanks for getting in touch. You are seeing a known issue affecting sign-in for
EU-hosted accounts, which we began investigating at 09:19 UTC today.

Existing signed-in sessions are not affected. We do not have a fix time yet; the
status page at status.example.com carries updates at least every 30 minutes and you
can subscribe for notifications.

We will follow up on this ticket once the issue is resolved.
```

What support must be told separately, and must not say:

- Do not name a cause. If asked directly, say the investigation is ongoing.
- Do not give a resolution time, even an approximate one, even if a responder said one
  in a channel.
- Do not confirm or deny anything about data. Route any data question to the comms lead
  immediately — the answer changes what regulatory clocks are running.
- Do say what is known: scope, what still works, and where updates appear.

## Translation rules

Same facts, re-cut. Never a different set of facts — contradictory versions meet in the
same meeting eventually, and that is not recoverable.

| From the technical channel | To external | Rule |
| --- | --- | --- |
| Service or component name | The capability the customer uses | Nobody outside knows your service names |
| Percentage of requests failing | What the customer sees when it happens | Error rates are meaningful to you, not to them |
| A hypothesis | Silence, until confirmed | Only confirmed statements go outward |
| An engineer's name | Nothing | Names appear internally, and in thanks |
| An ETA said in the channel | The next update time | Channel ETAs are working estimates, not commitments |
| "Rolled back the deploy" | "We reversed a recent change" | True, understandable, and does not require explaining your release process |
| A vendor's incident | "A fault in part of our infrastructure" | You own what you sold |

Two things travel unchanged in every direction: the impact window with a time zone, and
the scope. Those are the facts every version must agree on, and they are what a reader
compares between your status page, your email and your write-up.

## Phrases to strike

| Phrase | Problem |
| --- | --- |
| A small number of customers | Minimising. Give the number, or the segment |
| We apologise for any inconvenience | Formulaic enough to read as indifference. Apologise once, specifically, for the actual impact |
| The issue has been fully resolved | "Fully" is doing nothing except raising the cost of a relapse |
| Due to circumstances beyond our control | Reads as blame-shifting even when true |
| Our engineers are working around the clock | Effort is not an outcome, and it invites the question of why it is taking so long |
| We take reliability extremely seriously | Every company that has ever had an outage has written this sentence |
| Should be resolved shortly | An estimate wearing a hedge. Give the next update time |
| Isolated incident | Only knowable after the review, and it is the phrase that ages worst |

## The escalating-severity rewrite

When an incident gets worse after you have already communicated, the update must state
plainly that the scope has grown. The failure is publishing a new post that reads as
though the larger scope was always the case, which makes the earlier post look like a lie.

```text
[Investigating] Sign-in failures — scope wider than first reported — 10:05 UTC

Our earlier updates described this as affecting EU-hosted accounts only. We have now
confirmed it also affects sign-in for customers in the UK region, from 09:12 UTC.
Approximately 11% of accounts are affected in total. Existing sessions remain
unaffected.

We are validating a mitigation now. Next update by 10:35 UTC.
```

Naming the correction explicitly costs one sentence and buys the credibility of every
subsequent update in the incident.
