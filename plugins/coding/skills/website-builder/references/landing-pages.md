# Landing pages

Read this when the brief is a single page whose whole job is to get one kind of visitor to
take one action. A page like that is judged by whether the visitor does that one thing, so
the message and the order of the sections matter more than the styling. Settle them first,
then let the direction gate and `quality-floor.md` own how the page looks.

## Contents

- [Extra intake](#extra-intake)
- [Section order](#section-order)
- [Choosing a layout](#choosing-a-layout)
- [Writing the copy](#writing-the-copy)
- [What to show before code](#what-to-show-before-code)
- [Building it](#building-it)
- [Keeping content real](#keeping-content-real)
- [Ship list](#ship-list)
- [Indexing](#indexing)
- [Neighbouring skills](#neighbouring-skills)

## Extra intake

Ask these in the same batch as step A1, not as a second round of questions:

- **Primary action.** What is it, and which event on the page proves it happened? A signup,
  a purchase and a booked call are measured differently, and the page is built around one of
  them.
- **The exact offer.** What the visitor gets, for what price or commitment, and by when.
- **Audience and objections.** Who lands here, and what stops them acting? The objections
  that come up most become a section later.
- **Traffic source.** Where visitors come from and what they already know. Someone
  arriving from a specific ad has been promised something; someone arriving from search
  has not.
- **Proof available.** Numbers, named customers, quotes, logos, press, ratings. Say which
  are real; proof that does not exist cannot be shown.
- **Guarantee or risk-reduction terms.** A trial, a refund window, a cancel-anytime
  clause.

When an answer is missing, write the assumption in one line and carry on. A stalled
intake costs more than a wrong guess the user corrects at the structure stage.

## Section order

Three parts, in this order.

**The first screen** carries five things and nothing else:

1. A headline that names the outcome and who it is for.
2. A line under it that clarifies how, or for whom, in plain words.
3. One primary action.
4. One proof signal: a number, a rating or a recognisable customer.
5. A visual that shows the offer rather than decorates the page.

**The middle** argues the case:

- Problem to solution, in that order, in a few sentences.
- A few benefits written as outcomes the visitor gets, not as features of the product.
- A short how-it-works, in a small number of steps.
- Proof set directly beside each claim it backs up, rather than gathered into a single block lower down.

**The end** removes doubt:

- The objections from intake, answered as a section.
- A risk reducer: the guarantee, trial or cancellation terms, stated plainly.
- A closing action identical to the first, so the visitor who scrolled to the end meets
  the same promise they started with.

## Choosing a layout

Pick one, say why, and show it at the direction gate.

| Layout | Fits when |
| --- | --- |
| Standard: hero, then sections | The audience knows the problem and needs the argument laid out; the default |
| Long argument | The audience is sceptical or the offer is expensive or unfamiliar, so the page has to build belief before it asks |
| Minimal | Traffic is high-intent or the offer is short, so anything between the visitor and the action is friction |
| Comparison | The visitor arrives already weighing this offer against a named alternative; lead with the comparison, not a pitch |

## Writing the copy

- Match the promise of the ad, email or link that sent the visitor. A headline that
  restates something different reads as the wrong page and the visitor leaves.
- No competing actions in the first screen. A second button, or a navigation bar full of
  exits, splits the one decision the page exists for.
- Outcomes before features, and concrete numbers over vague verbs: "resolves 9 of 10 tickets
  on the first reply" beats "makes support faster".
- An action label says what the visitor gets: "Get the pricing sheet" or "Book a
  15-minute call", never a bare "Go" or "Continue".
- At least one risk reducer, visible without hunting for it.

## What to show before code

This extends the step A3 gate; it does not replace it. Alongside the design directions,
present, in this order, and stop for the user's answer:

1. The section outline.
2. The first-screen copy.
3. The benefits and the how-it-works steps.
4. The objections section.
5. The layout choice and the reason for it.
6. The indexing decision, with the reason.

Changing a headline in a message costs a sentence; changing it after the page is built
costs a rebuild.

## Building it

Build section by section: first screen, benefits, how it works, proof, objections, closing
action. Change one section per iteration and never regenerate the whole page, so each
change stays reviewable and a section the user already approved is not quietly rewritten.
Values for type, colour and spacing come from the chosen direction's tokens, defined once;
this file sets none.

## Keeping content real

- No filler text, and no stock names or placeholder brands.
- Every figure is either real or visibly marked as a placeholder to replace; never make up
  a plausible-looking one. A marked placeholder keeps a realistic length, so the
  layout holds when the real figure arrives.
- Vary names, dates and avatars so a list of testimonials does not read as one person
  repeated.
- Sentence-case headings.
- Error and success messages are plain and direct: say what happened and what to do next.

## Ship list

`quality-floor.md` already requires a 404 page, per-page title and description, share
tags and a working keyboard path; do not repeat those here. A landing page also needs:

- Links to a privacy notice and terms, in the footer at least.
- Validation on every form field, with the errors in plain words (`form-design` owns where
  and when they appear).
- Consent, where the visitor's jurisdiction requires it, before any non-essential cookie
  or tracker loads.
- A favicon.

## Indexing

Decide this before building, because it changes the markup.

- A page that exists only for an ad campaign, or for a limited time, stays out of search
  with `noindex`. It would compete with the evergreen page and then go stale.
- An evergreen page is indexed: a real title and description, internal links to and from
  the rest of the site, and the objections section written as plain questions followed by
  plain answers. Structured data for those questions is optional and only honest when the
  questions are visible on the page.

## Neighbouring skills

- `message-match-audit` audits an existing page against the ad that sends traffic to it;
  this file is for building a page, not judging one.
- `low-traffic-page-testing` is for testing variants of a page that does not get enough
  visits for a conventional experiment.
- `fake-door-test` is for probing demand with a page before the offer exists.
- `form-design` owns validation timing and error placement.
- `content-design` owns interface microcopy such as labels, errors and empty states.
