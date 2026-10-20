# Judge calibration

Read this at step 6 of `SKILL.md`, when a model judge is about to influence a gate: how to
measure a judge against human labels, which known biases to test for, and what to freeze so
a score can be compared with the one before it. `evaluation-design.md` lists what to
retain in a calibration record; this file covers how to produce and read one.

## Contents

- [What calibration claims](#what-calibration-claims)
- [Known judge biases and how to test each](#known-judge-biases-and-how-to-test-each)
- [Write the rubric before grading, then version it](#write-the-rubric-before-grading-then-version-it)
- [Report agreement as its own metric](#report-agreement-as-its-own-metric)
- [Pin the judge](#pin-the-judge)
- [Repeated runs: pass@k and pass^k](#repeated-runs-passk-and-passk)
- [Check the grader before blaming the agent](#check-the-grader-before-blaming-the-agent)
- [Sources](#sources)

## What calibration claims

A calibrated judge is one whose verdicts have been compared with independent human labels
on this rubric and this kind of output, and found close enough for the decision it will
inform. It is not a property of the judge model. A judge that tracks reviewers on support
summaries says nothing about code correctness, and a rubric edit or a new model resets the
claim. Anthropic's guidance is the same: model graders should be closely calibrated with
human experts, and vague rubrics produce inconsistent judgments.

## Known judge biases and how to test each

The MT-Bench paper (Zheng et al., 2023) names three biases in model judges: position bias,
verbosity bias and self-enhancement bias. Treat them as hypotheses to test on your own
judge and data, not as numbers to import.

| Bias | How it corrupts a gate | Test on the calibration set |
| --- | --- | --- |
| Position | In a pairwise comparison the judge favours the answer shown first or second, so baseline versus candidate order decides the result. | Grade every pair twice with the order swapped. Report how often the verdict flips with position. |
| Verbosity | Longer or more elaborately formatted answers win regardless of content. | Pad a known-good answer with filler, and shorten a known-good answer; the verdict should not move. Check whether judge scores correlate with length where humans' do not. |
| Self-enhancement | A judge favours output from its own model family, which matters when the candidate and the judge share a vendor. | Grade the same human-labelled items produced by different model families; compare the judge's false-accept rate by producer. Prefer a judge from a different family than the candidate when you can. |

Pairwise rules that follow:

- Run both orders. Count a win only when both orders agree; record a disagreement as a tie
  and report the tie rate, because a high tie rate means position is deciding the verdicts.
- Randomise which side holds the baseline when a single order is unavoidable, and record
  the assignment so a later audit can check it.
- Prefer single-answer grading against a rubric when the question is pass or fail. Reserve
  pairwise comparison for ranking two candidates where no absolute standard exists.
- Blind the judge to candidate identity, as `SKILL.md` requires, and strip headers or
  signatures that reveal the producing model.

## Write the rubric before grading, then version it

Shankar et al. (EvalGen) report that people need criteria to grade outputs, yet grading
outputs is what helps them define the criteria. The consequence is criteria drift: the
standard shifts while the grading is under way, so early and late verdicts follow different
rubrics and the aggregate is not comparable with anything.

Contain it:

1. Write the rubric, with anchored passing and failing examples, before any candidate run
   is graded. Drafting it against a handful of outputs from a development run is fine;
   those outputs then leave the calibration set.
2. Freeze it under a version identifier. Any wording change to a criterion, anchor or
   scale is a new version, and old results stay attached to the version that produced them.
3. When grading reveals a case the rubric cannot decide, do not patch the rubric silently.
   Record the case, write the new version, and regrade everything under it, baseline
   included.
4. Grade one criterion per judge call. A judge asked for one overall quality score blends
   criteria that humans weigh differently, and its disagreements cannot be traced to an
   item.
5. Give the judge a way out, such as an explicit "Unknown" verdict, and route those cases
   to human review instead of forcing a label.

## Report agreement as its own metric

Judge-human agreement belongs in the results next to task success, with its own
denominator. A gate built on a judge whose agreement nobody reported rests on an unmeasured
assumption.

- **Raw agreement** is the share of calibration items where judge and human give the same
  verdict. It misleads when classes are imbalanced: if nearly every item passes, a judge
  that always passes agrees almost always. Report it with the class counts.
- **Chance-corrected agreement** such as Cohen's kappa discounts matches the label
  distribution would produce anyway. Report it beside raw agreement when classes are
  imbalanced. Any threshold for acceptable agreement is a rule of thumb, so state the one
  you chose and why before the run, in the gate worksheet, not afterwards.
- **False accepts and false rejects** matter more than the single figure. A false accept
  ships a failure; a false reject wastes review time. Report both per criterion, and
  weight the one that is costly for this gate.
- **Human-human agreement** sets the ceiling. If two reviewers disagree on a criterion,
  the rubric is ambiguous and no judge can be calibrated to it; revise the rubric first,
  as `SKILL.md` says.
- Report the size of the calibration set. Agreement measured on a small set carries wide
  uncertainty, so say how many items stand behind each figure.

## Pin the judge

A judge is part of the measurement instrument. Record, with each result, the judge model
identifier (a dated snapshot where the host exposes one, an alias with that fact noted
where it does not; `model-lifecycle.md` explains why an alias is not a version), the
rubric version, the judge prompt, sampling parameters and the date. Recalibrate when any
of them changes, and never compare a score from one judge configuration with a baseline
graded by another: rerun the baseline under the new judge, or report the change as a
break in the series.

Judges also vary run to run. Where the judge is not deterministic, grade borderline items
more than once and treat inconsistent verdicts as unresolved for human review.

## Repeated runs: pass@k and pass^k

Agent output varies between trials, so one graded run of each case confounds agent
variance with judge variance. Anthropic defines the two reporting metrics:

- **pass@k** is the probability of at least one success in k attempts. It rises with k and
  suits tools where one success is enough.
- **pass^k** is the probability that all k trials succeed. It falls with k and suits agents
  whose users expect the same behaviour every time. At a 75% per-trial success rate and
  three trials, pass^3 is 0.75 cubed, about 42%.

At k equal to 1 the two are identical; they diverge as k grows. Choose the metric from the
product requirement before reading results, and state k. A consistency-critical agent
reported only as pass@k looks far better than its users will find it.

## Check the grader before blaming the agent

A low score can be a grading defect. Anthropic reports Opus 4.5 scoring 42% on CORE-Bench
until a researcher found rigid grading that penalised "96.12" when the expected answer was
"96.124991...", ambiguous task specifications and stochastic tasks that could not be
reproduced exactly; after fixes and a less constrained scaffold the score rose to 95%.

Before accepting a surprising failure rate:

1. Read a sample of failed transcripts alongside the grader's verdict and ask whether a
   careful human would also fail the run.
2. Look for graders that demand an exact form where the contract allows several, tasks
   whose stated goal conflicts with the grading threshold, and tasks the grader can only
   pass by a path the task never mentioned.
3. Test the grader on a known-good and a known-bad artifact, as `SKILL.md` step 4 requires,
   and fix the grader or task, not the score.
4. When a task or grader changes, version it and rerun every compared candidate on the new
   version.

## Sources

- [Zheng et al., Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685) — position, verbosity and self-enhancement biases in model judges, and mitigations including swapping answer order. Cited for the named biases only; no figures from it appear here.
- [Shankar et al., EvalGen](https://arxiv.org/abs/2404.12272) — criteria drift while grading outputs, and why criteria need defining and validating against human judgement.
- [Anthropic, Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — pass@k and pass^k, judge calibration against human experts, isolated per-dimension judges, the "Unknown" way out, and the CORE-Bench grading-bug example.
