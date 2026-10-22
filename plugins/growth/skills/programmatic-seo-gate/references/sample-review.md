# Sample review and duplication check

Read this at step 3, before the fifty pages are drawn.

## Contents

- Drawing the sample
- Reading rubric
- Near-duplicate check
- Decision

## Drawing the sample

Draw at random across the whole set, stratified by the data volume of the pages (a few from the thinnest tenth, a few from the middle, a few from the richest). Keep the list of URLs and the random seed so the draw can be repeated.

## Reading rubric

Score each page on one line:

| Check | Pass condition |
| --- | --- |
| First screen | answers the query without scrolling past boilerplate |
| Distinct information | at least one fact, number or listing that the neighbouring pages lack |
| Accuracy | spot-check two facts against the source |
| Reads naturally | no obvious template seams such as "in the city of the city" |
| Useful next step | a link or action relevant to the intent |

A page fails if either of the first two fails. Score pass, thin or duplicate.

## Near-duplicate check

Strip the shared template (navigation, footer, fixed sentences) from the text of each sampled page, split the rest into word shingles of about five words, and compare pairs with Jaccard similarity. Pairs of pages that are mostly the same after stripping are duplicates in practice, whatever their titles say. A script in `python3` using sets of shingles is enough for fifty pages.

## Decision

Pass: at most five failures in fifty. Fail: more than that, or any cluster of duplicates. After a fail, change the template or data, draw a new sample, and repeat. Record each round so the history of the page type is clear.
