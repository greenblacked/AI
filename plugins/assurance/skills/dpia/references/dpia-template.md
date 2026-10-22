# DPIA template

Read this when writing or reviewing the assessment itself. The sections follow the order
of the workflow, and they cover the minimum contents of Article 35(7): a systematic
description, an assessment of necessity and proportionality, an assessment of the risks to
individuals, and the measures to address them. Keep the headings so a reviewer can find
each part without reading the whole document.

## Contents

- [Header and version history](#header-and-version-history)
- [1. Description of the processing](#1-description-of-the-processing)
- [2. Necessity and proportionality](#2-necessity-and-proportionality)
- [3. Risk register](#3-risk-register)
- [4. Sign-off](#4-sign-off)
- [5. Re-trigger list](#5-re-trigger-list)
- [Harms to look for](#harms-to-look-for)

## Header and version history

```text
Title:             DPIA — <feature or processing>
Version:           <major.minor>   Status: <draft | in review | accepted | superseded>
Owner:             <name, role>
Screening record:  <link>
Design document:   <link>
Processing starts: <planned date> — the assessment must be accepted before this

| Version | Date | Author | Change | Approved by |
| --- | --- | --- | --- | --- |
```

Bump the major version when the risk register or sign-off changes, the minor version for
wording. An accepted version is never edited in place; a change makes a new version.

## 1. Description of the processing

- **Purposes**, each stated narrowly enough that a new use would obviously fall outside it.
- **Data subjects**, with any vulnerable group named.
- **Data items**, grouped, with special-category and criminal-offence data marked.
- **Sources**: collected directly, observed, inferred, or obtained from someone else.
- **Flow**: a diagram or numbered list from collection to deletion, naming every store,
  every recipient and processor, and every transfer abroad with its destination.
- **Retention** per data group, and what enforces it.
- **Scale**: people, records, geography, duration.
- **Technology**: anything new in the processing, and whether it makes or shapes decisions.

## 2. Necessity and proportionality

| Question | Answer and evidence |
| --- | --- |
| Lawful basis for each purpose | Named basis; for legitimate interests, link the balancing record |
| Is each data item needed for its purpose | Per item; list removed or reduced items separately |
| Could less achieve the purpose | Aggregation, pseudonymisation, coarser precision, on-device processing, shorter retention |
| Purpose limitation | What stops the data being reused for something else |
| Accuracy | How errors are found and corrected, especially for inferred data |
| Transparency | Where and when people are told, in what words |
| Rights | How access, rectification, erasure and objection are served; human review of automated decisions |
| Processors | Each processor and the contract terms that bind it |
| Transfers | Each destination and the mechanism relied on |

**Removed or reduced:** a list of every item cut or narrowed by this section, with the
reason. Empty is a finding worth questioning.

## 3. Risk register

One row per harm to a person. Score inherent risk before measures and residual risk
after, and keep likelihood and severity as separate columns rather than a product.

Scale (keep it the same across every assessment in the organisation so they can be
compared):

- Likelihood: remote, possible, probable.
- Severity: minimal, significant, severe.
- Overall, read from this matrix. A severe harm never scores low, however remote, which is
  the property that matters. Replace it with your organisation's matrix if one exists, and
  apply the same one every time.

| Likelihood \ Severity | Minimal | Significant | Severe |
| --- | --- | --- | --- |
| Remote | Low | Low | Medium |
| Possible | Low | Medium | High |
| Probable | Medium | High | High |

| ID | Harm to the person | Source | Inherent L / S | Measure | Owner | Due / gates | Evidence | Residual L / S | Overall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | | | | | | | | | |

"Source" is either a failure (illegitimate access, unwanted modification, loss) or the
processing working as designed. "Evidence" is a link to the merged change, configuration
or contract that implements the measure, filled in when it is done.

## 4. Sign-off

```text
Residual risk accepted by:  <name, role>   Date: <YYYY-MM-DD>
Against version:            <version>
DPO advice:                 <verbatim, or "no DPO designated">
Advice followed:            <yes | no — reasons>
Views of data subjects:     <sought from whom and summary | not sought — reasons>
High residual risks:        <none | IDs, and the prior consultation outcome>
```

## 5. Re-trigger list

List the changes that require a new version before they ship. Start from these and add
any specific to the system:

- A new data category, especially special-category data.
- A new purpose, or reuse of the data for analytics or model training.
- A new recipient, processor or sub-processor.
- A new transfer destination.
- A new group of data subjects, children especially.
- A step change in scale.
- A model or rule added to, or given more weight in, a decision about people.
- Longer retention.

## Harms to look for

Use this as a prompt when the register looks thin, not as a list to copy in. Each line is
written as what happens to a person.

- Someone sees information about them they were entitled to keep private: a manager, a
  family member, an insurer, the public.
- They lose money, or are defrauded or impersonated using what was exposed.
- They are refused a service, a job, credit or a price on the basis of a score or an
  inference they cannot see or contest.
- They are treated differently because of a characteristic the processing reveals or
  proxies, such as health, ethnicity or age.
- They change what they do because they know they are watched.
- A decision about them is based on wrong data and they cannot get it corrected.
- They cannot find out what is held about them, or cannot get it deleted.
- Data about a child is used in a way the child could not understand or anticipate.
- Pseudonymised data is linked back to them.
- Their data is used for a purpose they were never told about.
