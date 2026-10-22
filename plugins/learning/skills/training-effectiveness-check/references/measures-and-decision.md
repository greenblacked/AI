# Measures and decision

## Contents

- Pre-registration note
- Practical task and rubric
- Behaviour indicators and example queries
- Decision table

## Pre-registration note

Write this before delivery and keep it where the sponsor can see the date.

```text
Training:              (name, dates, cohort and size)
Objective behaviour:   (what people do differently at work)
Practical task:        (before and after; variant used for each)
Rubric pass mark:      (for example 6 of 8 items)
Behaviour indicator:   (source and query; baseline window)
Read dates:            30 days = ... ; 90 days = ...
Comparison group:      (later cohort, or none and why)
Failure criterion:     (the result that means this did not work)
Decision owner:        (who chooses repeat, revise or stop)
```

## Practical task and rubric

Choose a task that takes 30 to 60 minutes and can be scored from what the person produces.

- **Lab:** deploy, configure or fix something in a sandbox. Score items: reached the working state, followed the procedure taught, used the safe path for the risky step, time to result.
- **Review task:** give a sample change with five to eight planted defects of the kind the training covers. Score: how many were found, how many were named correctly, whether any false alarm was raised.

Use two variants of equal difficulty (A and B). Give half the cohort A first and half B first, so a harder variant does not look like a learning effect. Strip names before scoring, and have a second scorer mark a few to see whether the rubric is read the same way. An item that two scorers disagree on is not observable enough; rewrite it.

## Behaviour indicators and example queries

An indicator is a rate from a source that exists whether or not anyone is studying it. Fix the definition before reading.

Review comments naming a practice (adjust the phrase to what was taught). The query below returns pull requests where USER commented and some comment, by anyone, contains the phrase. The two conditions are not tied to one comment, so treat the count as an upper bound only; the date filter also applies to when the pull request was opened, not when the comment was written. For the indicator itself, read the comments endpoint for each pull request and keep comments whose user is the cohort member and whose body contains the phrase, filtering on created_at.

```bash
gh api -X GET search/issues -f q='repo:ORG/REPO is:pr "threat model" in:comments commenter:USER created:2026-01-01..2026-03-31' --jq '.total_count'
```

Distinct test files touched by the cohort, from local history (replace the authors and dates):

```bash
git log --since=2026-01-01 --until='2026-03-31 23:59:59' --author=alice --author=bob --name-only --pretty=format: -- 'tests/' | grep -v '^$' | sort -u | wc -l
```

Other sources: incident timelines that include the declared step, such as a recorded rollback decision; pipeline logs showing the new check enabled; tickets reopened; time from page to first mitigation. Count per person, or per pull request, and say which; counts of events per team say nothing about spread.

Windows: baseline is the three months before; read at 30 days and at 90 days after. With fewer than about ten people, report counts and show each person, not a percentage.

## Decision table

| Task improved | Indicator moved at 90 days | Reading | Decision |
| --- | --- | --- | --- |
| Yes | Yes | Learned and applied | Repeat; keep the failure criterion for next time |
| Yes | No | Learned, not applied: environment, tooling or lead is the cause | Revise the surroundings, not the content: reinforcement, templates, review checks |
| No | Yes | Something else changed, or the task did not match the objective | Revise the task and check the comparison group before crediting the training |
| No | No | Neither learning nor use | Stop, unless the cause is cheaply fixable, and say which |

If the comparison group moved the same amount, the training did not cause the change; state that, even when the trained group improved.
