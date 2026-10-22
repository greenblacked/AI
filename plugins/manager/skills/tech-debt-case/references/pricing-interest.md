# Pricing interest

Read this when pricing an item: where each input comes from, the conversion, the risk
arithmetic and a worked example. Figures in the example are illustrative.

## In this file

- Sources for the hours
- Risk cost
- Hours to money
- A worked item

## Sources for the hours

| Input | Where to get it | Caveat |
| --- | --- | --- |
| Tickets touching the area | Tracker search by component or label, last six months | Labels are inconsistent; sample twenty by hand to check |
| Pull requests in the area | `git log --since="6 months ago" --oneline -- path/to/area \| wc -l` | Counts changes, not effort; pair with review rounds |
| Authors who touch it | `git shortlog -sn --since="6 months ago" -- path/to/area` | A narrow author list is itself a risk signal |
| Incident and on-call hours | Pager history and postmortem records tagged to the service | Count responder hours, not elapsed time |
| Review rounds above norm | Pull request data for the area compared with the team median | Indicates friction, convert with a stated hours per round |
| Build or test wait | CI duration for the area x runs per month x people waiting | Only count waiting time that blocks work |
| Change failure rate | Deploys needing a rollback or hotfix divided by deploys, for the area | Needs enough deploys to be meaningful; show the count |

Estimate a monthly figure as the six-month total divided by six. If a number is a guess,
label it assumed and give the range.

## Risk cost

Risk per month = probability in twelve months x impact / 12.

- Probability needs a basis: past incidents in the area, an end-of-life date, a known
  single point of failure. A range is acceptable; a figure with no basis is not.
- Impact is the cost of the event: outage hours x revenue or cost per hour, data
  recovery, customer credits, regulatory fine. Source each.
- Keep the risk column separate from the hours column. They are different kinds of
  cost, and a reader who distrusts the probability should still be able to accept the
  hours.

## Hours to money

Use the finance partner's loaded cost per engineer-hour. If none is available, a
defensible figure is the loaded annual cost divided by roughly 1,600 productive hours,
stated as an assumption. Stay in hours when the audience works in capacity.

## A worked item

Item: the order-export job, a batch script with no tests.

- Tickets in six months: 14, average 3 hours each = 42 hours, so 7 hours per month
  (measured from the tracker).
- On-call pages: 6 in six months, 2 hours each = 12 hours, so 2 hours per month
  (measured).
- Review overhead: no estimate, set to zero rather than guess.
- Interest in hours: about 9 per month.
- Risk: one past failure that delayed customer invoices by a day; probability of a
  repeat in twelve months estimated at 30 percent (assumed), impact estimated at 8,000
  in credits (estimated). Risk per month about 200.
- Principal: 3 engineer-weeks, range 2 to 5 (estimated by the owner), about 120 hours.
- Risk in hours: assume a loaded cost of 100 an hour (160,000 a year over 1,600 hours,
  an assumption). Risk of about 200 a month is then about 2 hours a month, which makes
  the interest about 11 hours a month.
- Payback: 120 / 11 = about 11 months. Not in the first bucket. The risk adds about 2
  hours a month, small against the 120-hour principal, so it does not justify an
  executive decision. It is a candidate for the fixed capacity share, ranked by payback
  and re-priced next quarter.

The point of the exercise is that the item looked urgent and priced as moderate. Another
item at 30 hours per month and 60 hours of principal pays back in two months and goes
first.
