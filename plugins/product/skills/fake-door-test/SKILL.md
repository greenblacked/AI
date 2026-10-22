---
name: fake-door-test
description: "Measure demand for an unbuilt feature or product with a fake door, smoke test or landing page, and decide from a rule written before launch. Set the pass threshold and sample size from what the build is worth; count only a costly action (a waitlist sign-up with a work email, a refundable deposit, a booked call), never a click; tell responders on the follow-up page that it is not live, and contact every one within 48 hours. A pass leads to serving those responders by hand, not to a build. Use when someone wants to test demand before building, gauge interest with a coming-soon button, run a smoke test or painted door, or decide whether a landing-page result is good enough. Not for checking that a problem exists through interviews (problem-validation), serving the first customers manually (concierge-mvp), or finding what they would pay (pricing-research)."
allowed-tools: Read, Glob, Grep
---

# Fake Door Test

Done means a demand test whose pass threshold, sample size and stopping rule were written down before anyone saw the door, that counted only an action costing the visitor something, that told every responder the truth and followed up with each within 48 hours, and that ended in a recorded pass or fail with the next step named.

The usual failure is reading the result after the fact. A button gets 4% click-through, someone says that sounds good, and the build starts. Nobody decided beforehand what number would have meant no, clicks cost the visitor nothing, and the traffic was whoever happened to pass. A test that cannot fail is a ceremony. The second failure is deception: a fake checkout that takes a card, or a waitlist nobody ever hears from, spends the trust of exactly the people most likely to buy.

## Scope

Use for: testing demand for a feature, add-on, plan or new product before building it, with an in-product entry point or a landing page; deciding the threshold and sample size; reading the result.

Do not use for: finding out whether the problem exists at all, which is `problem-validation` and comes first; delivering the service by hand once demand is shown, which is `concierge-mvp`; testing price points, which is `pricing-research`; rolling out a feature that already exists, which is `release-strategy`; a properly powered user-level A/B test of a variant that is already built, which is `experiment-design`.

## Workflow

### 1. Write the value of the build and derive the threshold

Before designing the door, write three numbers and where each came from:

1. What the build costs: engineering, design and a year of upkeep.
2. What a customer is worth over the period you care about, as gross margin, not revenue.
3. How many of the people who take the costly action you expect to become paying customers. This is an assumption; say so and say why.

From those, work back to the conversion rate the door needs on the audience you can reach. If the build costs 120,000, a customer brings 6,000 of gross margin in the first year, and you expect a quarter of waitlist sign-ups to convert, you need 20 customers, so 80 sign-ups; from 10,000 qualified visitors a year that is a threshold of 0.8%. The arithmetic and a worksheet are in `references/threshold-and-sample.md`.

Writing the threshold from the build's value is what makes the test a decision. A threshold copied from an industry benchmark answers a question nobody asked.

### 2. Choose the door and the audience

- **In-product door**: a menu item, button or plan option for existing users, placed where the real feature would live, with the same prominence. Over-promoting it measures curiosity about the promotion.
- **Landing page**: for a new product or segment, with traffic from the channel you would really use to acquire them. Traffic from your own newsletter measures fans.

Restrict exposure to the segment the build is for, and keep the door out of any workflow where a dead end would cost a user real work, such as checkout or incident tooling.

### 3. Count a costly action, never a click

Pick one primary action that costs the visitor something:

| Action | Fits |
| --- | --- |
| Waitlist sign-up with a work email | Business products, where a personal address says little about a buying organisation |
| Refundable deposit | Consumer or prosumer products where money is the honest signal |
| Booked call | High-value business products where buying involves a conversation |
| Pre-order or signed letter of intent | Hardware, services, large contracts |

Record clicks and page views as funnel diagnostics only. A click shows the label was intriguing; it does not show anyone would give up anything for what is behind it.

### 4. Fix sample size and the stopping rule before launch

Count exposures as unique people who saw the door, not page views. Choose the sample size so that a result at the threshold is distinguishable from a result at half of it; at a 0.8% threshold that is about 1,900 exposures. The formula and a table are in `references/threshold-and-sample.md`.

Write the stopping rule: run until the planned exposures are reached or a fixed end date passes, whichever comes first. Do not stop early because a good day made it look decided; early stopping on a favourable run is how a fail becomes a pass. If the end date arrives short of the sample, the result is inconclusive, not a pass.

### 5. Tell the truth on the follow-up page

Behind the door, say plainly that it is not available yet, what you are considering building, and what happens if they sign up. Then ask for the costly action.

- Never take a payment you are not prepared to refund on request. Deposits are refundable, and refunded automatically if you decide not to build.
- Collect only what you need to follow up and say what you will use it for.
- Check the consumer-protection and privacy rules where you sell before taking deposits or emails. This skill is procedure, not legal advice.
- Remove or relabel an in-product door when the test ends.

Page copy and the follow-up email are in `references/threshold-and-sample.md`.

### 6. Contact every responder within 48 hours

Write to every person who took the costly action within 48 hours: thank them, confirm it is not built, and ask for a twenty-minute call about the last time they needed this. The call is where you learn what job they were hiring it for; record how many accept, because accepting a call is a second costly signal. Waiting longer turns warm interest into a cold list and reads as the bait it was not meant to be.

### 7. Read the result against the rule

At the planned sample:

1. Remove internal, test and bot traffic, and anyone outside the target segment. State how many were removed.
2. Compute the costly-action rate on exposures and its 95% interval.
3. Compare with the threshold written in step 1. Pass or fail is decided by that rule, not reopened.
4. Report the call acceptance rate from step 6 alongside it.

A pass hands the responders to `concierge-mvp` as its first customers, because demand for a promise is not yet evidence the product delivers. A fail stops the build or changes the proposition; a changed proposition is a new test with a new written threshold, not a re-reading of this one.

## Output

```markdown
## Decision rule (written [date], before launch)
[Build value, conversion assumption, threshold, sample size, stopping rule, costly action.]

## Door
[Placement or landing page, audience, traffic source, dates.]

## Result
[Exposures after exclusions, costly actions, rate and 95% interval, pass or fail against the rule.]

## Responders
[Count contacted within 48 hours, calls accepted, what the calls said about the job.]

## Next step
[Concierge cohort, stop, or a new test with its own rule.]
```

## Anti-patterns

**Click-through as demand.** Clicks are free. The test exists to find out whether anyone will pay a cost.

**Threshold after the data.** Any number looks like a pass once you have seen it. Write the rule first, date it, and keep it.

**A pass that goes straight to a build.** People sign up for a promise. Serve them by hand first and see whether they come back.

**Silent waitlists.** Responders who never hear back stop trusting the next thing you put in front of them, and they were the most interested people you had.

## Reference files

- `references/threshold-and-sample.md` — read at steps 1, 4, 5 and 7: the threshold worksheet from build value, the sample-size formula and table, the interval calculation, and follow-up page and email copy.
