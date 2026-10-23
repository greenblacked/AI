# Sources and confidence

Read this when collecting or scoring evidence for a competitor watch: what each public
source reveals, how it misleads, how to count job postings, how to read review sites by
theme, and how to assign confidence the same way every time.

## Contents

- Source catalogue
- Counting job postings
- Reading review sites by theme
- Archiving and diffing pages
- The confidence rubric, with examples
- A worked register entry

## Source catalogue

| Source | Look for | Misleads when |
| --- | --- | --- |
| Careers page and the applicant tracking board it links to | Open roles by team, location, seniority; new teams appearing | Roles stay open for months, are reposted, or are evergreen pipelines |
| Changelog and release notes | Cadence, which areas ship, deprecations | Entries are marketing; small fixes are bundled to look like features |
| Product documentation | Whether a feature is generally available, beta or preview; limits and quotas | Docs lag the product, or describe a feature only some plans get |
| Pricing and packaging page | Tiers, the pricing metric, what moved between tiers, minimums | Enterprise prices are unpublished; existing customers may be grandfathered |
| Status page history | Which components exist and how often they fail | Many incidents are never posted; a quiet page proves little |
| Review sites | Recurring praise and complaints, by company size and role | Review campaigns produce bursts of positive reviews; one review is an anecdote |
| Partner, integration and marketplace listings | Which ecosystems they invest in; new channel partners | A listing can be a thin connector or a logo exchange |
| Public code repositories | SDK activity, new client libraries, what they open source | Activity in a public repo can be unrelated to the commercial roadmap |
| Conference talks, webinars, blog posts by staff | Architecture and direction, in the engineers' own words | A talk describes one team's view, sometimes of a past system |
| Public filings and earnings calls, for listed companies | Segment revenue, stated strategy, risk factors | Forward-looking statements describe intent and are hedged by design |
| Press releases and funding announcements | Capital available, stated use of funds | Announcements are written for investors and recruits |

A direct source supports Medium on its own. An indirect signal, such as postings, needs a second source type before the claim rises above low confidence.

## Counting job postings

Count, do not read. Once a month, record each open role with team, location, seniority and
the date first seen. Then look at the series:

- **Growth by team over a quarter.** A team going from two to eleven open roles is a
  signal of investment; a steady four is maintenance.
- **New teams.** The first posting for a function that did not exist (a partnerships team,
  a regional sales team, a team named after a product area) is often the earliest public
  sign of a bet.
- **Location.** The first roles in a new country or time zone usually precede a regional
  launch or support coverage.
- **Seniority.** A first senior hire for a function often means a new area is being set
  up.

Remove reposts and evergreen roles before counting: the same title reappearing every month
with no change is a pipeline, not a new hire.

## Reading review sites by theme

Read reviews in a fixed window, such as the last six months, and filter to the segments
that match our customers. Code each review into a small set of themes (onboarding,
reliability, support, pricing, a named capability) as praise or complaint. Report the
themes with counts and one representative quote each. A theme with fewer than about five
reviews behind it in the window is reported as tentative.

Watch for bursts: many reviews in a short period, often after a campaign that offered an
incentive, skew the themes positive. Note the burst and read the reviews outside it
separately.

## Archiving and diffing pages

Save each captured page as plain text with the capture date in the file name, or record the
Wayback Machine snapshot URL, which gives a third party's dated copy. Keep the captures in
one folder per competitor so the next review can diff against them.

Diff the text, not the screenshots. A diff shows the tier that was renamed, the limit that
changed from 10 to 5, the feature that moved from the middle tier to the top one. Those
moves are often more informative than a headline price change, because they show which
customers the competitor wants to push upward.

## The confidence rubric, with examples

| Level | Rule | Example |
| --- | --- | --- |
| High | The competitor stated it publicly, or two independent source types agree | Changelog ships an EU data region and the careers page lists support roles in Dublin |
| Medium | One direct source | Pricing page moves single sign-on from the middle tier to the top tier |
| Low | One indirect signal, or an inference across a gap | Six new data engineering postings in a quarter, nothing shipped yet |

Confidence is about the evidence, not about how plausible the claim feels. A claim that
everyone in the room finds obvious, with one indirect signal behind it, is low.

## A worked register entry

| Field | Value |
| --- | --- |
| Id | C-07 |
| Claim | They are moving upmarket to companies with more than 1,000 employees |
| Sources | Pricing page diff (SSO and audit logs moved to the top tier); careers page (first enterprise account executive roles, three regions); partner page (new systems integrator listing) |
| Captured | 2026-07-01, 2026-07-03, 2026-07-03 |
| Confidence | High: three source types agree |
| Would be disproved by | The enterprise roles closing unfilled and no case study from a company of that size within two quarters |

At the next review, recapture each source. If the enterprise roles have been filled and
case studies have appeared, keep the claim with the new date; if the pricing change was
reversed, correct the claim; if no source can be reconfirmed, delete it.
