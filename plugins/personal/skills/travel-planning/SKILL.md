---
name: travel-planning
description: >-
  Plan a trip around the constraints that break trips — fix the immovable ones first (dates,
  budget ceiling, who is coming, what would make the trip a failure), verify entry and visa
  requirements at the official government source, check passport validity and blank pages, then
  build the itinerary around minimum connection times, single ticket versus self-transfer risk,
  change and cancellation windows, insurance exclusions and arrival-day pacing. Use this skill
  whenever someone is planning or booking travel — "plan me a week in Japan", "is this
  connection too tight", "do I need a visa for Vietnam", "my passport expires in four months",
  "should I book these two flights separately". Not for general money decisions
  (personal-finance), work visas and relocation (job-search), planning a week of work
  (weekly-review), or paperwork at home (life-admin).
allowed-tools: Read, Write, Edit, WebFetch, WebSearch
---

# Travel Planning

A trip is planned when every person going can board every leg, the total committed spend is known and under the ceiling, each booking's change and cancellation window is written down, and no day requires being in two places at once.

The job goes wrong in a small number of ways, and none of them is the part people spend their time on. First, the entry requirement is assumed rather than checked: visa policy, transit rules and health requirements change with weeks of notice, model training data and travel blogs both go stale, and a wrong answer is discovered at a check-in desk where the airline refuses boarding because it, not the border, pays the fine for carrying you. Second, the passport is valid on the calendar but not under the destination's rule — the common requirement is six months of validity beyond the intended departure date, and an issue date more than ten years old fails Schengen entry even when the expiry date is comfortable. Third, the connection is legal on a screen and impossible on the ground, or worse, it is two separate tickets, which means the second airline owes nothing at all when the first leg is late. Fourth, the itinerary is scheduled to capacity, so a single delayed train removes the rest of the week. Fifth, insurance is bought and its exclusions are never read, so the one claim that matters is denied for a pre-existing condition nobody declared. This skill fixes the constraints before the pleasures, sends every entry question to the official government source rather than answering it from memory, and prices the risk of each booking structure explicitly.

## Scope

Use for: planning a leisure or personal trip end to end; deciding between itinerary options; checking whether a connection, ticket structure or passport is safe; working out what documents, insurance and money a trip needs; rescuing a trip where something has already gone wrong with a booking.

Do not use for: budgeting, saving or a general money decision (`personal-finance`); a large discretionary purchase judged on its merits (`major-purchase`); work visas, relocation and immigration tied to employment (`job-search`); planning a week of work (`weekly-review`); renewing a passport or fighting a refund with a company back home (`life-admin`).

The boundary with `personal-finance` runs through the question, not the topic. "Can we afford a 4,000 trip this year given our savings" is a money decision and belongs there. "We have 4,000 — what does the trip look like" is a constraint on this trip and belongs here. State which one you are answering.

## Workflow

Steps 1 to 3 come before any destination research. Reversing that order is how people spend an evening on hotels for a trip their passport cannot make.

### 1. Fix the immovable constraints

Write these five down before anything else, because each one eliminates options rather than ranking them:

- **Dates**, and which end is fixed. A fixed return with a flexible departure is a different search from a fixed week.
- **The budget ceiling**, as a total including flights, accommodation, ground transport, food, activities and a 15% contingency. A ceiling without a contingency line is spent by day three.
- **Who is coming**, with each traveller's passport, nationality and anything that changes entry rules — a second citizenship, a residence permit, a child travelling without both parents, a mobility or medical need.
- **What would make this trip a failure.** Ask it in those words. The answers are specific and load-bearing: "spending it in transit", "not seeing my sister", "coming back more tired".
- **The one thing the trip exists for.** Everything else is negotiable against it.

### 2. Verify entry requirements at the official source

Do not answer a visa, transit or entry-health question from memory, and say so plainly. Check, in this order, and cite what you checked:

| Source | What it settles | Why this one |
| --- | --- | --- |
| The destination government's own immigration or foreign-ministry site | Whether this passport needs a visa, which visa, and the current fee | It is the authority; everything downstream copies it late. |
| The traveller's own foreign ministry travel advice page | Health requirements, security advisories, and the advisory level that can void insurance | It is written for this nationality and is updated on incidents. |
| The operating airline's destination or travel-requirements tool | What the check-in agent will actually enforce | The airline carries the fine for boarding an inadmissible passenger, so it applies rules conservatively. |
| The transit country's rules, separately | Whether a transit visa is needed even airside | Transit is a separate permission and is the most commonly missed one. |

Check every passport separately when the party holds more than one nationality, and check the transit point even for a connection you never leave the terminal for. If a required document has a processing time, that time is now a date on the plan. `references/entry-requirements.md` has the full checking procedure, the passport-validity and blank-page rules, and the electronic authorisation schemes to look for; read it before booking anything non-refundable.

### 3. Check the passports against the destination's rule, not the expiry date

Three rules fail people who believe their passport is valid:

- **Six months beyond departure.** A large number of countries, concentrated in Asia, the Middle East and Latin America, require the passport to be valid for at least six months after the intended date of departure from the country. A passport expiring in four months is refused at check-in for a trip that ends next week.
- **Blank pages.** Many countries require one to two entirely blank pages for the entry stamp, and some, South Africa among them, refuse entry without two. Amendment and endorsement pages do not count.
- **Issued within the last ten years.** Schengen entry requires the passport to have been issued less than ten years before the date of entry and to be valid at least three months beyond the intended departure. Extension months added to an older renewal are the usual trap.

Renewal takes weeks and the trip cannot move, so this check happens the day planning starts, not the week before.

### 4. Structure the flights around the risk, not the price

The difference between one ticket and two is the whole of your protection when the first leg is late.

| Structure | What happens when leg one is late | Use when |
| --- | --- | --- |
| Single ticket, one airline | The carrier rebooks you at no charge and owes duty of care — meals and a hotel — while you wait | Default, and the only sane choice for a same-day international connection. |
| Single ticket, interline or alliance partners | Same protection; the ticket is one contract of carriage regardless of who flies it | Long routings where no one carrier covers it. |
| Two separate tickets, self-transfer | The second airline owes you nothing. The fare is gone and a replacement is bought at the walk-up price | Only with an overnight buffer, or a booking platform that sells an explicit self-transfer guarantee — read what it actually pays. |

Minimum connection time is the airport's published legal minimum, not a safe one. Commonly it is 45 to 60 minutes for domestic connections, 60 to 90 for international, and 90 to 120 at large hubs that require terminal changes, immigration or a security re-clear. Book at the published minimum only when you can afford the trip to break; on a single ticket, add 50%, and where you must change terminal, clear immigration, or collect and recheck bags, treat two hours as the floor. Two separate tickets need the buffer sized to the next available replacement flight — if there is one a day, the buffer is a night in a hotel.

### 5. Write down the change and cancellation window for every booking

For each flight, hotel and rail ticket, record the answer to four questions at the moment of booking, while the page is still open: what it costs to change, what it costs to cancel, when the free window closes, and whether the refund is money or credit. Credit expires; money does not.

Three specific windows are worth knowing and are all time-limited:

- **The 24-hour rule.** Tickets bought in the United States at least seven days before departure can be cancelled for a full refund within 24 hours of booking, under a US Department of Transportation rule. That window is free thinking time — use it to run the entry and connection checks before the ticket becomes non-refundable.
- **Free cancellation on accommodation.** Usually ends between 24 hours and 14 days before arrival, and differs per rate on the same property. Put the date in the calendar with the booking reference in the title, not in a folder you will not open.
- **The cancellation-for-any-reason insurance window.** Where it is offered at all, it must normally be bought within 14 to 21 days of the first trip deposit, and it reimburses 50% to 75% rather than everything.

### 6. Buy insurance for what it actually covers

Insurance covers catastrophes, not disappointments. The claim that makes a policy worth buying is a medical evacuation, which is routinely quoted in the tens of thousands and can reach six figures for an air ambulance across an ocean, or a cancellation that costs the whole trip. Check three exclusions before price:

- **Pre-existing conditions** are excluded unless declared and accepted, and the definition usually reaches back over a lookback period of several months, including conditions under investigation rather than diagnosed.
- **Acting against official advice** voids most policies: travelling to a region your own foreign ministry advises against, or ignoring a published evacuation order.
- **Named activities.** Motorcycling, diving beyond a depth, skiing off-piste, climbing and any organised sport are typically excluded from the base policy and need an endorsement.

Check whether cover already exists before buying: some credit cards include trip cancellation and medical cover when the trip was paid on that card, and some national health arrangements cover state care between specific countries. Both have limits far below a private evacuation. `references/booking-mechanics.md` compares the booking structures, the compensation regimes and the insurance types in detail; read it when a flight has already gone wrong or when a policy decision is close.

### 7. Pace the itinerary below capacity

The standard mistake is scheduling to capacity: every day full, every transfer at the minimum, no slack anywhere, which means the first delay consumes something that had to happen.

- **Two anchors a day.** One in the morning, one in the afternoon, and a list of optional third things. Three anchors plus a move is a day nobody enjoys.
- **One moving day in four at most.** Changing city costs most of a day once packing, transfer, check-in and reorientation are counted, regardless of how short the journey looks.
- **Three nights minimum per base** for anywhere you want to have seen rather than visited. Two nights is one full day.
- **Book the things that sell out, leave the rest open.** Timed-entry museums, a specific restaurant, a permit or a long-distance train are booked; afternoons are not.
- **A deliberate empty half-day** every three or four days, placed in advance. Unplanned slack gets filled; planned slack absorbs the delay that arrives.

### 8. Plan the arrival day around the time zone, not the clock

Arrival day is capacity you do not have. Jet lag resolves at roughly a day per time zone crossed, and eastward travel is harder because the body adapts more easily to a longer day than a shorter one. Plan nothing that matters on arrival day and nothing requiring alertness on the morning after a red-eye. For an overnight arrival, either book the previous night so the room is available on landing, or confirm the property's actual check-in time — a 15:00 check-in after a 06:00 landing is nine hours with luggage. Check whether the destination observes daylight saving on your dates: a timetable read in the wrong offset is how a connection that looked fine turns out to be a missed flight.

### 9. Assemble documents and money before departure

Work through the checklist in `references/documents-and-money.md`, which covers the document set, the copy strategy, the card and cash mix, and the per-destination payment quirks; read it in the final week before departure. The core of it: carry the passport plus separate physical and encrypted digital copies, name one card as primary and a second on a different network as backup carried separately, and know which of your cards is accepted at all where you are going — American Express and Discover are thinly accepted outside their home markets. Decline dynamic currency conversion every time it is offered; paying in your home currency at a foreign terminal costs a 3% to 7% margin over the card network's own rate.

## Choosing the tools

Trip-planning applications are the fastest-growing segment of travel software, with the largest reporting year-on-year growth of around 37%, so the traveller probably already has one. That is worth knowing and not worth deferring to: the tools are good at storing an itinerary and bad at the two checks that actually strand people, which are entry eligibility for a specific passport and the ticket structure behind a connection. Use whatever the traveller already uses to hold the plan; do the verification here.

## Output format

```text
# [Trip] — [dates]

## Fixed constraints
Dates: [fixed / flexible which end] · Budget ceiling: [total, including 15% contingency]
Travellers: [name — nationality — passport expiry — anything that changes entry rules]
Failure condition: [what would make this trip a failure]
The trip exists for: [the one thing]

## Entry requirements — verified [date]
[Traveller / destination]: [requirement] — source: [official page checked]
[Transit point]: [transit visa needed or not] — source: [official page checked]
Passport check: [six-month rule / blank pages / ten-year issue rule — pass or action]
Actions with lead times: [document] — [processing time] — [apply by date]

## Bookings
| Item | Ticket structure | Change cost | Cancel free until | Refund type |
| --- | --- | --- | --- | --- |

Connection risk: [leg] — [buffer] vs [published minimum] — [one ticket / self-transfer]

## Itinerary
[Day] — [base] — [anchor 1] / [anchor 2] — [booked in advance: yes/no]
Slack: [which half-days are deliberately empty]
Arrival day: [what is deliberately not scheduled]

## Insurance
Policy: [type] · Bought by: [deadline for any window]
Checked exclusions: [pre-existing] / [advisory] / [activities]

## Before departure
- [ ] [document, copy, card, notification, deadline]
```

## Anti-patterns

**Answering a visa question from memory.** Entry rules change with weeks of notice and the answer is enforced at a check-in desk by an airline that pays the fine for getting it wrong. The cost is a refused boarding and a non-refundable trip. Check the destination government's own page, name it, and give the date you checked it.

**Reading only the expiry date on a passport.** Six months of validity beyond departure, two blank pages, and an issue date under ten years old are three separate rules, and a passport can pass the expiry test and fail all three. Check the destination's rule, not the date on the front.

**Two tickets treated as one journey.** A self-transfer that saves 80 on the fare costs a full-price walk-up ticket, a night in an airport hotel and a missed first day when leg one is late. Either buy one ticket, or buy the buffer — an overnight, not ninety minutes.

**Connecting at the published minimum.** The legal minimum assumes no immigration queue, no gate change, no bag recheck and an on-time arrival. On a single ticket add half again; where a terminal change or an immigration clearance is involved, two hours is the floor.

**Booking before the entry check.** Research done in the wrong order produces a beautiful itinerary to a country whose visa takes six weeks. Constraints first, always, and the US 24-hour cancellation window exists precisely to let you check after you have secured a fare.

**Scheduling to capacity.** Every day full means the first delay deletes something irreplaceable and the trip becomes an exercise in catching up. Two anchors a day, one moving day in four, and a planned empty half-day every three or four days.

**Buying insurance without reading the exclusions.** The undeclared pre-existing condition, the region under a foreign-ministry advisory, and the unendorsed activity are the three reasons real claims are denied. Read those three before comparing prices, and check whether a credit card already covers the trip.

**Treating a credit voucher as a refund.** Vouchers expire, are non-transferable and are often restricted to the same airline and fare class. Record refund type at the moment of booking, and prefer the fare that returns money when the difference is small.

**Planning the arrival day.** A day booked solid after an overnight flight across six time zones produces one exhausted person and one missed reservation. Arrival day carries luggage, a check-in time and nothing that matters.

**Leaving one card and no copies.** A single card that gets blocked, swallowed or stolen strands you where your bank's phone line does not reach. Two cards on different networks carried separately, plus physical and encrypted copies of every document.

## Reference files

- `references/entry-requirements.md` — read before booking anything non-refundable: the official-source checking procedure, the passport validity and blank-page rules by region, electronic travel authorisations and what they do not replace, transit rules, and the questions that change the answer (dual nationality, children, residence permits, onward-ticket proof).
- `references/booking-mechanics.md` — read when comparing fares, when a connection looks tight, or when a leg has already gone wrong: ticket structures and what each one owes you, minimum connection times by airport type, fare rule vocabulary, the EU and US delay and refund regimes, and how the insurance types differ.
- `references/documents-and-money.md` — read in the final week before departure: the document and copy checklist, the card and cash mix, dynamic currency conversion, per-destination payment quirks, health documents and prescriptions, and the emergency contact set.
