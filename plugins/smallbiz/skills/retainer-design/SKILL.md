---
name: retainer-design
description: "Structure an ongoing monthly client arrangement. Pick the type: reserved capacity (paid whether used or not), hours bank (use it or lose it, or a one-month rollover cap) or outcome subscription with defined deliverables. Price reserved capacity at a premium over project rate, since you give up flexibility. Write down the hours cap and overage rate, response-time commitment, exclusions, rollover rule, 30-day notice both ways, annual indexation and a monthly one-page usage report sent regardless; review at three months on hours used versus paid. Gate: no discount without a longer commitment in return. Use for 'client wants me on retainer', 'should I offer a monthly retainer', 'how to price ongoing support hours', 'retainer hours unused every month'. Not for one-off projects (fixed-price-quote), repricing decisions (client-profitability-review) or a sales team's discount policy (discount-discipline)."
allowed-tools: Read, Glob, Grep
---

# Retainer Design

A finished design is a one-page retainer terms sheet naming the type, the monthly fee, the hours or deliverables, the overage rate, the exclusions, the notice period and the review date, plus a usage report template.

The usual failure is a vague promise of "a few hours a month" at a discount. The client assumes unlimited availability, you discover the real demand only after saying yes, and unused hours create resentment on both sides. A retainer sells predictability to you and availability to the client; the terms must say exactly what each side gets.

## Scope

Use for: setting up or restructuring a recurring monthly arrangement, pricing ongoing support hours, and fixing a retainer where hours go unused or overrun.

Do not use for: a one-off project quote (`fixed-price-quote`) or the analysis of which clients to move onto a retainer or reprice (`client-profitability-review`). Contract wording for the final agreement belongs with `services-agreement-checklist`; this skill decides the commercial shape. This is procedure, not legal advice.

## Workflow

### 1. Pick the type on purpose

| Type | Client pays for | Unused hours | Best when |
| --- | --- | --- | --- |
| Reserved capacity | A block of your time held for them | Paid regardless | They need you on call or in a fixed weekly slot |
| Hours bank | Up to N hours of work a month | Lost, or rolled over once under a cap | Work is varied and the client wants control |
| Outcome subscription | Defined deliverables each month (for example two articles, a monthly report) | Not applicable | The work repeats and can be specified |

Ask what the client actually needs before choosing: availability, a volume of work, or a result. Mixing types in one sheet is the usual source of later arguments.

### 2. Price from your rate, with a premium for reserved capacity

Start from the effective rate in `billing-rate-calculation` and the multiplier from `estimate-actuals-review` if you have one. Reserved capacity gets a premium over your project rate, because you give up the flexibility to sell that time elsewhere and you carry the risk of urgent requests. Charging less because the client commits monthly is the wrong way round unless the commitment is longer (step 7). Hours banks sit near the project rate; outcome subscriptions are priced from the hours per deliverable, with the multiplier applied.

### 3. Write the terms that prevent arguments

The sheet states, in plain words (template in `references/retainer-terms-sheet.md`):

- Monthly fee and what it covers: the hours cap, or the list of deliverables.
- Overage rate for work beyond the cap, and whether overage needs approval first.
- Response-time commitment, stated as a business-hours window and a channel. Do not promise a window you cannot meet while on another client's deadline.
- Exclusions: what is outside the retainer (new projects, emergencies out of hours, third-party costs), with the rate for each.
- Rollover rule: none, or one month with a stated cap.
- Notice: 30 days either way.
- Annual indexation: a stated increase or a rule for one, reviewed on the anniversary.

### 4. Send a usage report every month

One page: hours or deliverables used against the allowance, what was done, what is queued. Send it even when usage was zero. The report is how the client sees value, so that unused months are not read as wasted money, and how you notice a retainer drifting in either direction. A retainer without a report is the one that gets cancelled quietly.

### 5. Handle unused hours by rule, not by mood

Under reserved capacity, the fee is earned whether used or not; say so in the sheet and in the report. Under an hours bank, apply the rollover rule exactly as written. Do not carry hours forward informally "this time"; it becomes the expectation. If the client is not using the hours, raise it in the monthly report and the three-month review rather than at cancellation.

### 6. Review at three months

Compare hours used with hours paid, requests turned away because of the cap, time spent outside scope, and effective hourly rate. Decide one of: continue as is, resize up, resize down, change type or end. Put the date in the sheet at the start so a downsize or end is a scheduled review, not a confrontation.

### 7. Gate: no discount without a longer commitment

A retainer discount is only a trade. Give it in return for something specific: a six or twelve month term instead of rolling monthly, or payment quarterly in advance. Without that, the discount is a pay cut for the same obligation. Write the trade into the sheet (for example, a stated percentage off for a twelve month term, with early exit terms) so that it is visible and expires with the commitment.

## What to hand back

```text
Type: [reserved capacity / hours bank / outcome subscription] - reason
Fee and allowance: [amount per month - hours or deliverables]
Overage and exclusions: [rate - list]
Response time: [window - channel]
Rollover / notice / indexation: [rule - 30 days - rule]
Discount traded for: [commitment] or "none given"
Review date: [3 months from start]
Usage report: [template attached]
```

## Anti-patterns

- **Discounting for the same commitment.** A monthly rolling retainer already costs you flexibility.
- **Unlimited availability by omission.** Without a hours cap and a response window, the client will assume both.
- **Informal rollover.** One favour becomes a policy.
- **Silence in a zero-usage month.** Send the report anyway.
- **No review date.** Resizing becomes a crisis rather than a calendar item.
- **Mixing types.** A cap, a deliverable list and a standby slot in one retainer cannot be reported on honestly.

## Reference files

- `references/retainer-terms-sheet.md` - read at steps 3 and 4: the one-page terms sheet template and the monthly usage report layout.
