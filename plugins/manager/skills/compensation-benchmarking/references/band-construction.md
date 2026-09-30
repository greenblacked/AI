# Band Construction

Read this when building or refreshing a salary band: the sources worth using and what each
is trustworthy for, how to clean the data, the formulas for a midpoint and a spread, geo
differentials, and a worked band you can copy the arithmetic from.

## In this file

- Sources, and what each is for
- Cleaning the data
- Midpoint and spread
- Geo differentials
- Placing people
- Compression and inversion
- A worked band

## Sources, and what each is for

No single source is the market. Use two or three and read the disagreement as your range.

| Source | Good for | Watch for |
| --- | --- | --- |
| A paid compensation survey (Radford, Mercer, Pave, Option Impact) | Defensible midpoints, level-matched, auditable | Cost; a lag of a few months; the level definitions may not match your ladder |
| Crowd-sourced data (levels.fyi, Glassdoor) | A fast read on a hot role and a specific company | Self-report skews high; small samples; total comp mixed with base |
| Government or national statistics | Broad market context, cost-of-living | Too coarse for a specific level or role |
| Your own hiring data | What you actually had to pay to hire | Selection bias — you only see the ones who said yes |
| Recruiter intelligence | Live signal on a specific market right now | Anecdotal; a recruiter has an interest in the number looking high |
| Published pay ranges (some jurisdictions require them) | Exact company and level, where available | Coverage is patchy and biased to large employers |

For equity-heavy roles, benchmark base and equity separately and recombine. A startup's
"competitive" offer is usually a below-market base with a large option grant whose value
depends on a strike price and a future round.

## Cleaning the data

Apply all five before you use a percentile.

- **Skew.** Self-reported data skews high; the people who submit are often the ones who
  negotiated or are moving. Discount the crowd-sourced top end.
- **Age.** Comp data decays. Age anything older than a year forward by a stated market
  movement, or drop it and say so. A 2022 number is a history lesson.
- **Sample size.** Report the count behind any percentile. Fewer than about fifteen
  entries for a role and level is a hint, not a benchmark.
- **Mix.** Normalise everything to base, bonus and equity, then to total comp. Do not
  compare your base to a market total.
- **Level definition.** Read how the source defines the level. A "senior" at a ten-person
  company and at a 400-person company are different jobs.

## Midpoint and spread

Pick a target percentile for the midpoint. Most organisations target the median (P50) for
a solid performer at the level and price above it deliberately.

```text
midpoint   = the market rate at the target percentile for this level, role and location
spread     = the half-width of the band, as a fraction of the midpoint
band_min   = midpoint × (1 - spread)
band_max   = midpoint × (1 + spread)
```

Typical half-widths:

| Level | Half-width | Why |
| --- | --- | --- |
| Junior / entry | 15% | The work is narrow; little room to differentiate |
| Mid | 20% | A solid performer range |
| Senior | 25% | Wider range of scope at the same title |
| Staff and above | 30% | The work varies most; the band has to hold it |

A 25% half-width gives a band from 0.75 to 1.25 of midpoint — a 1.67× ratio top to
bottom, which is enough to reward growth without a promotion and not so wide that the
band means nothing.

## Geo differentials

Two defensible approaches, and one indefensible one.

- **One band per market.** Cleanest to explain; more bands to maintain.
- **One band, a location factor.** Multiply the midpoint by a factor per location (for
  example 1.0 for the HQ, 0.8 for a lower-cost market). Simpler; the factors drift and
  need refreshing with the same discipline as the band.
- **HQ pay everywhere.** Indefensible: it overpays in low-cost markets, underpays in
  high-cost ones, and the market corrects it for you by attrition.

Whatever you choose, apply it to the whole band, not to selected people, or the
differential becomes a hidden exception.

## Placing people

```text
compa-ratio          = salary / midpoint
range penetration    = (salary - band_min) / (band_max - band_min)
```

| Compa-ratio | Reading |
| --- | --- |
| Below 0.85 | Below the band's working range; a retention risk unless a promotion is imminent |
| 0.85 – 1.15 | The working range; most people should sit here |
| Above 1.15 | Above midpoint; fine for a strong performer, an exception if the band has a ceiling |

In a band symmetric around its midpoint, compa-ratio 1.0 always means 50% range
penetration. The measures diverge away from the midpoint when band widths differ: with
a £100,000 midpoint and £110,000 salary, compa-ratio is 1.10 in either a £80,000–£120,000
band (75% penetration) or a £70,000–£130,000 band (about 67% penetration). Look at
both, next to tenure and performance.

## Compression and inversion

Pull every person at a level, sorted by salary, with tenure and last rating beside it.

- **Compression:** a new hire within about 10% of people with two or more years more
  tenure at the same level. Common after a hot hiring market; fixed by repricing, not by
  a bonus.
- **Inversion:** a less senior or lower-rated person paid more than a more senior one at
  the same level. An inversion with no named reason is a bug in the structure.

Record the reason for every person above 1.15 or below 0.85. The unexplained ones are
what an equity review or a curious employee finds first.

## A worked band

Senior backend engineer, London, target P50, 25% half-width.

| Step | Value | Working |
| --- | --- | --- |
| Market P50 (survey, aged forward 4 months) | £92,000 | Survey said £89,000, aged +3.4% |
| Crowd-sourced P50, discounted | £98,000 | £104,000 raw, discounted 6% for self-report skew |
| Blended midpoint | £95,000 | Weighted toward the survey |
| Band min | £71,250 | 95,000 × 0.75 |
| Band max | £118,750 | 95,000 × 1.25 |

A current senior at £88,000 has a compa-ratio of 0.93 — in the working range, with room
to grow. A new hire offered £112,000 sits at 1.18: inside the band but at the top, which
is a deliberate exception to record, not a default to repeat.
