# Observation and licence boundaries

Read this before step 2 of the main workflow, to decide which case you are in before you
look at the reference's internals — its code, its bundle, its captured network traffic.
Using the feature as an ordinary user, which step 1 relies on, is always fine; what this
file sorts out is everything past that. "I can see it" and "I can copy it" are different
questions, and this file answers the first one: what each way of learning about a feature
actually permits.

## What each way of looking counts as

| How you learned it | What it gives you | What it does not give you |
| --- | --- | --- |
| Using the product as an ordinary user | The feature's behaviour: inputs, outputs, visible edge cases | Any right to its code, assets, exact text or exact visual design |
| Reading public docs, help pages or a changelog | Stated behaviour, sometimes more precisely than using the UI alone | The same as above; doc text itself is also someone's copyrighted content — summarise it, do not quote it into your spec at length |
| Reading your own network requests in a browser's dev tools | The shape of a request or response your own client made | A right to copy the server's exact response body, sample data or distinctive formatting verbatim. A short, functional field name is generally not protected expression and an interoperating client often has to use it; that is a reason it is usually low-risk, not a right you have been granted — if a name is distinctive enough to be an issue, that is the same expression question as the row below, not a separate one |
| Reading the reference's source, because it is genuinely open source | Everything the licence grants — which varies by licence; a permissive one may allow direct reuse, a copyleft one carries obligations | Nothing beyond what that specific licence says; "open source" is not one licence, and seeing the code is not the same as having cleared it. Route to `licence-compliance` before reusing anything, including a pattern distinctive enough to be protected expression in its own right |
| Static or dynamic analysis of a shipped binary or package (`reverse-engineering`) | Behaviour and structure that analysis establishes, under that skill's own lawful-use scope | The same ceiling as reading source without a licence: understanding is not a right to copy, and that skill's own scope excludes producing a bypass of any protection it finds |
| A sample, dataset, icon or asset handed to you or found attached to the product | Nothing automatically | Nearly always needs its own licence check; treat it the same as code until cleared |

## Patents and trade dress are a different question entirely

Copyright covers the expression — the code, the text, the exact asset — not the underlying
idea, method or algorithm, so an independently written implementation of the same algorithm
is not, by itself, a copyright problem. What gate 3 actually bars is copying the reference's
code, or a distinctive way it implements that algorithm (its particular expression of the
method) — that is still copied expression even though the method itself is free to use under
copyright. Writing your own code from scratch does not, however, clear a patent on the
technique: a patent can cover the method itself regardless of whose code expresses it, which
is exactly what gate 5 and the row below are for. Two things copyright does not cover, that
can still block you regardless of how the code was written:

- **A patent** can cover a specific technique or method regardless of whether you wrote your
  own code for it. This is not something this skill or `licence-compliance` clears; flag it
  for legal review when the feature is a core differentiator of your product, or the
  reference is a direct competitor's — either one is reason enough, and together they are
  exactly the situation where a patent is most likely to exist and most likely to be enforced.
- **Trade dress or trademark** can cover a product's distinctive look, name or branding even
  where no single asset is copied. A UI that is "inspired by" a competitor's overall look,
  not just one icon, is a question for the same legal review, not an engineering judgement
  call.

## Terms of service sit beside, not inside, copyright

Scraping a product's own UI or API to observe behaviour in bulk, automatically, or
persistently can be a terms-of-service matter independent of whether anything you then write
infringes a copyright. Reading a page as a human, once, to understand a feature is a
different posture than running an automated collector against it; if your observation step
looks like the second one, that is its own question to clear before you start, not something
this skill's gates cover.
