# Claim check sheet

## Contents

- [The claim sentence](#the-claim-sentence)
- [Evidence questions](#evidence-questions)
- [Red flags by paper type](#red-flags-by-paper-type)
- [Verdict template](#verdict-template)

## The claim sentence

Template: On X, method M improves metric Y by Z over baseline B.

Worked example: "On a public document-ranking benchmark, a re-ranker with the new loss
improves nDCG at ten by 1.8 points over the same re-ranker with the standard loss, averaged
over five seeds." Every slot is a fact in the paper. If baseline B is "prior work" with no
named method, that slot is empty.

## Evidence questions

| Question | Good answer | Worrying answer |
| --- | --- | --- |
| Were baselines tuned as hard? | Same search budget, same data, stated | Defaults for baselines, a tuned grid for the new method |
| Are baselines current? | Strong recent methods included | Only old or weak ones |
| How many seeds, what variance? | Several, with spread or intervals | One run, no spread |
| Is the gain bigger than the spread? | Clearly | Within one standard deviation |
| Can the test set leak? | Held-out, checked for overlap with training data | Public test set that may sit in pretraining data; test used for model selection |
| Does the ablation isolate the claim? | One component removed at a time | Several changes removed together |
| Is the metric the right one? | Matches the stated goal | A proxy that is easy to move |
| Does it generalise? | Several datasets or scales | One benchmark |
| Is cost reported? | Compute, latency and data needs given | Gain bought with ten times the compute, unmentioned |
| Is code or data released? | Yes, with settings | No, and details are vague |

## Red flags by paper type

- Empirical: results only on the authors' own dataset; baselines copied from older papers with different settings.
- Systems: benchmarks on a workload the system was designed around; no tail latency; no failure behaviour.
- Theory: a bound that needs assumptions the practical setting violates; no experiments connecting it to practice.
- Position or survey: claims about trends without a stated search method. If it is a survey, `literature-scan` has the method to judge it.

## Verdict template

```text
Verdict: adopt | watch | ignore
Claim:   on X, M improves Y by Z over B
Basis:   the checks that held and the ones that did not, with pages
Change my mind: the evidence that would move the verdict
Cheapest test in our setting: one experiment, or none
```
