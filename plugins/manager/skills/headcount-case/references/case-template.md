# Case template

Read this when drafting the document: a one-page layout, the evidence table and the
objections that recur.

## In this file

- One-page layout
- Evidence table
- Alternatives grid
- Objections that recur

## One-page layout

1. The ask and the decision, in two lines at the top.
2. Cost of not hiring, as a table, with the single largest item named first.
3. Alternatives that lost, as a grid.
4. Ramp and benefit date, one chart or three sentences.
5. If declined, and the smaller option.
6. Success measure, with baseline, target and check date.

Appendix: the data sources and queries, so the finance partner can re-run any figure.

## Evidence table

| Figure | Value | Label | Source |
| --- | --- | --- | --- |
| Committed roadmap effort next two quarters | engineer-weeks | Estimated | Planning document, date |
| Capacity available | engineer-weeks | Measured | Team roster minus leave and on-call |
| Incident and on-call hours per month | hours | Measured | Pager history, ticket export |
| Toil hours per month | hours | Estimated | Team survey or time sample |
| Revenue or contract tied to slipped items | currency | Estimated | Account owner |
| Time to fill this role | weeks | Measured | Last three comparable hires |

## Alternatives grid

| Alternative | Cost | What it solves | Why it falls short |
| --- | --- | --- | --- |
| Reprioritise | Value of dropped work | Part of the gap | The dropped items are named and are worth more than the hire |
| Contract | Monthly rate x months | Short-term capacity | Knowledge leaves, onboarding repeats |
| Tool or automation | Licence plus build time | Named toil hours | Covers a fraction; the rest remains |
| Stop a project | Value of the project | Frees engineers now | The project is the one you would stop if declined |

## Objections that recur

- Why now rather than next quarter: cost of delay per month, from the evidence table.
- Why this level: the work's requirements, and what the lower level would add in
  mentoring load.
- Why not contract: the grid above.
- Why not fix the process first: what has already been fixed, with measured effect, and
  what remains.
- What if the project ends: where the person moves, or that the role is tied to a
  standing workload and not a project.
