# Screening

Read this in step 1, when deciding whether an assessment is required, and when recording
that decision. The three layers are applied in order; any one can make the assessment
required, and none of them can make it unnecessary on its own if another says otherwise.

## Contents

- [Layer 1: the mandatory cases](#layer-1-the-mandatory-cases)
- [Layer 2: the supervisory authority's list](#layer-2-the-supervisory-authoritys-list)
- [Layer 3: the nine criteria](#layer-3-the-nine-criteria)
- [The screening record](#the-screening-record)
- [Worked examples](#worked-examples)

## Layer 1: the mandatory cases

Article 35(3) names three cases where an assessment is required in particular:

1. A systematic and extensive evaluation of personal aspects, based on automated
   processing including profiling, on which decisions are based that produce legal effects
   or similarly significant effects on the person.
2. Processing on a large scale of special-category data, or of data about criminal
   convictions and offences.
3. Systematic monitoring of a publicly accessible area on a large scale.

These are a floor, not the whole list. The general test in Article 35(1) is processing
"likely to result in a high risk" to people's rights and freedoms, and the next two layers
are how that test is applied in practice.

## Layer 2: the supervisory authority's list

Each supervisory authority publishes a list of processing types that require an
assessment in its jurisdiction, and some publish a list of types that do not. Find the
current list for every authority that is competent for the processing and check the
feature against each entry. Record which list and which version you checked, because these
lists are revised.

## Layer 3: the nine criteria

The European guidelines on DPIAs (WP248, endorsed by the European Data Protection Board)
give nine criteria. Where processing meets two or more, assume an assessment is required.
Meeting one can still be enough; record why you judged it was not.

| Criterion | What it looks like in a product |
| --- | --- |
| Evaluation or scoring, including profiling and prediction | Credit or fraud scores, churn prediction, behavioural segments, performance ratings |
| Automated decision with legal or similarly significant effect | Automatic loan refusal, account suspension, shortlisting candidates with no human review |
| Systematic monitoring | Employee activity tracking, location history, CCTV, keystroke or screen capture |
| Sensitive or highly personal data | Health, biometrics, ethnicity, beliefs, sexual life, criminal records; also financial data, precise location, private communications |
| Large scale | Many people, many records, long duration or wide geography — judge all four, not only the head count |
| Matching or combining datasets | Joining your data with purchased or partner data, or datasets collected for different purposes |
| Vulnerable data subjects | Children, employees, patients, elderly people, asylum seekers — anyone with an imbalance of power against the controller |
| Innovative use or new technology | A model in the decision path, biometric login, IoT sensors, a new kind of tracking |
| Processing that blocks a right, service or contract | Using a score to decide who may open an account or receive a service |

A feature rarely hits only one. Biometric login for employees is sensitive data, vulnerable
data subjects and new technology at once.

## The screening record

Keep this whether or not the answer is yes. It is short on purpose: a screening nobody can
fill in within twenty minutes stops being done.

```text
Feature / processing:       <name and link to design document>
Screened by / date:         <name>, <YYYY-MM-DD>
Regime and authority:       <law, supervisory authority, list version checked>
Layer 1 cases met:          <none | which, with one line each>
Authority list entries met: <none | which>
Nine criteria met:          <each criterion met, with the fact that meets it>
Decision:                   <required | not required | referred to DPO>
Reasoning if not required:  <why, especially where one criterion was met>
DPO consulted:              <yes, advice: ... | no DPO designated>
Re-screen when:             <the design changes that would change this answer>
```

## Worked examples

**Employee laptop monitoring that flags "low productivity".** Systematic monitoring,
vulnerable data subjects (employees), evaluation or scoring. Three criteria: required.

**Newsletter sign-up storing an email address and topic preferences.** None of the
criteria, unless the preferences feed profiling. Not required; keep the record, because
the day someone joins it with purchase history it becomes matching datasets plus
profiling.

**A symptom checker that stores answers to health questions.** Sensitive data, and
probably large scale once it launches nationally. Two criteria: required, and possibly
Layer 1 case 2 depending on scale — a question for the DPO.

**Moving an existing assessed system from one hosting region to another abroad.** Not a
new screening question so much as a re-trigger: the existing assessment's transfer
section and risk register change, and the new version goes through sign-off again.
