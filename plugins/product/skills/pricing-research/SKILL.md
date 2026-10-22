---
name: pricing-research
description: "Find out what customers will pay before a price is set: pick the method by sample size (under about 30 respondents, value interviews anchored on what the current alternative costs them; above it, Van Westendorp for the acceptable range plus Gabor-Granger for demand at each price), ask the buyer who signs separately from the user who benefits, cross-check against the economic value the product creates and the share of it you can capture, and hand back a price range with its stated risk rather than one number. Use for \"how should we price this\", \"are we underpriced\", \"what would people pay\", a willingness-to-pay survey, or choosing the value metric for a new tier. Not for deal-level discount rules (discount-discipline), moving existing customers onto a new price (price-change-rollout) or negotiating your own salary (offer-negotiation)."
allowed-tools: Read, Glob, Grep
---

# Pricing Research

Pricing research is done when there is a price range for a named segment and value metric, each end of the range is tied to evidence, the risk in the range is stated in a sentence a finance lead can argue with, and the next step to narrow it is named.

The usual failure is asking people what they would pay and believing them. Stated willingness to pay runs above real behaviour, users who never sign a purchase order answer as freely as buyers who do, and a single number from a survey hides how wide the uncertainty is. The second failure is copying a competitor's price, which inherits their cost base and positioning rather than your customers' value.

## Scope

Use for: pricing a new product, tier or add-on; checking whether a current price is too low or too high; choosing what to charge per (seat, usage unit, workspace, outcome); designing or analysing a willingness-to-pay survey; interviewing customers about value before a price exists.

Do not use for: rules for how far sales may discount a list price, which is `discount-discipline`; moving existing customers to a new price with notice and grandfathering, which is `price-change-rollout`; deciding whether the problem is worth solving at all, which is `problem-validation`; testing demand with a page before anything is built, which is `fake-door-test`; your own pay or a job offer, which is `offer-negotiation`.

## Workflow

### 1. Write the pricing decision down first

State what is being priced, for which segment, what decision the research feeds (launch price, a new tier, a repricing) and by when. List the value metric candidates and choose the one that grows with the value the customer gets and that they can predict on their own budget. A metric the customer cannot forecast (raw API calls for a buyer who thinks in projects) creates bill shock and procurement friction regardless of the level.

### 2. Separate the buyer from the user

Name who signs, whose budget line pays, and who uses the product day to day. Find out the approval threshold that changes the purchase path: a price that needs a procurement review or a second signature sells differently from one a team lead can expense. Interview and survey the two roles separately and label every answer by role. A user's enthusiasm is evidence of value; only a buyer's answer is evidence of price.

### 3. Choose the method by sample size

- **Under about 30 respondents per segment** (most B2B products, any early-stage product): value interviews anchored on the cost of the current alternative. Survey statistics on a sample this small produce curves that move when one person changes an answer.
- **About 30 or more per segment you intend to price separately**: a survey with Van Westendorp's four questions for the acceptable range, followed by Gabor-Granger purchase-likelihood questions at fixed price points for the demand curve. Van Westendorp alone gives a range but says nothing about how many people buy at each price; Gabor-Granger alone gives demand only at the prices you chose to show. Together they give both.

Count only respondents who match the segment and role from step 2. Fifty answers from the wrong segment are not a sample.

### 4. Run value interviews where the sample is small

Anchor every conversation on what the customer does today and what it costs: hours spent and by whom, the tool or service they pay for now, the cost of the failure the product prevents. Ask about the last time they bought something comparable, who approved it and how long it took. Leave price to the end, and test specific numbers rather than asking an open question: "At 400 a month per team, who would need to approve this?" tells you the purchase path; "What would you pay?" tells you a number they made up on the spot.

Read `references/value-interviews.md` for the interview guide and the economic value worksheet.

### 5. Run the survey where the sample is large enough

Show the same product description to everyone before any price question. Ask the four Van Westendorp questions, drop respondents whose answers are not in order, and compute the range. Then ask Gabor-Granger likelihood at five to seven price points spanning the range you expect, set from interviews or a pilot, with the order randomised or adaptive. Treat purchase intent as optimistic: count only the top answer ("definitely would buy") as a buyer, or report top-two separately as an upper bound.

Read `references/survey-methods.md` for exact question wording, the analysis, the two conventions for the Van Westendorp marginal points, and a short script that computes both methods from a CSV.

### 6. Cross-check against economic value

Estimate the economic value to the customer: what the next-best alternative costs them (the reference value), plus the net worth of what the product does differently (the differentiation value). A common working range is to capture roughly 10 to 30 per cent of the value created, leaving the customer most of the gain so the purchase is easy to justify. Treat that as a heuristic to test the survey, not a law.

When the survey range sits above the value estimate, either the survey is overstating or the value case is missing something; go and find out which. When it sits far below, the value is not being felt or not being communicated in this segment, which is a positioning problem before it is a pricing one. Competitor list prices are a reference point for the buyer's expectations; record them, but do not set a price from them.

### 7. Hand back a range with its risk

Report a floor, a ceiling and a recommended starting point within them, per segment and value metric, each tied to the evidence behind it. State the risk in one or two sentences: what could make the range wrong, in which direction, and what it would cost. Name the next step that would narrow it — usually a live price in a limited market, a pilot with a few buyers, or the first renewals at the new price. Before showing different prices to different visitors, check with legal and with whoever owns customer trust, because some markets and customers treat that as unfair; this is procedure, not legal advice.

## Output format

```markdown
## Decision
[What is priced, segment, value metric, the decision this feeds, date.]

## Evidence
[Method and why; respondents by segment and role; what each method showed.]

## Value cross-check
[Reference value, differentiation value, implied capture at the proposed range.]

## Range
[Floor, ceiling, recommended start; evidence behind each.]

## Risk and next step
[What could make it wrong, in which direction, cost of being wrong; the test that narrows it.]
```

## Anti-patterns

**"What would you pay?" asked cold.** The answer is invented on the spot. Anchor on the current alternative and test specific numbers.

**Users answering for buyers.** The person who loves the product is often not the person who signs. Label every answer by role.

**One number.** A point estimate hides the uncertainty the decider needs to see. Report a range with its risk.

**Van Westendorp alone.** It gives an acceptable range, not demand. Pair it with Gabor-Granger or with interviews about volume.

**Pricing off the competitor.** Their price reflects their costs and strategy. Use it as a reference, not a target.

**A survey on thirty friends of the founder.** Respondents outside the segment add noise that looks like signal. Screen before counting.

## Reference files

- `references/value-interviews.md` — read at steps 2, 4 and 6: the interview guide for buyers and users, price-testing questions, and the economic value worksheet.
- `references/survey-methods.md` — read at step 5: Van Westendorp and Gabor-Granger wording, cleaning and analysis, the marginal-point conventions, and a standard-library script for both.
