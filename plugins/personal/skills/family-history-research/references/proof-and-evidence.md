# Proof and evidence

Read this at phase 6, and again before writing any conclusion. Every family and place in the
examples is fictional.

## Contents

- The five-part standard
- Source, information, evidence
- Proof levels
- Family labels
- Leads are not evidence
- Proof summary or proof argument
- Worked example: a clear case
- Worked example: two people with one name
- Worked example: a negative result

## The five-part standard

A conclusion about a person or a link counts as reliable only when all five hold.

1. **A reasonably exhaustive search.** Every record type that could plausibly answer the
   question was looked for, in the places that kept it, under every name variant. The stop
   rule is in `searching-and-logging.md`.
2. **Complete and accurate citations.** Each item names what it is, where it is held, how to
   open the same page, when and how it was obtained. A claim without a locator cannot be
   checked, so it cannot be relied on.
3. **Analysis and correlation of the evidence.** Each item is classified (below) and the
   items are compared against each other, not read one at a time.
4. **Resolution of conflicting evidence.** Where two statements disagree, one is chosen with
   a reason, or the conflict is left open and the conclusion is capped.
5. **A soundly reasoned written conclusion.** The reasoning is written out. A conclusion held
   only in someone's head is a belief.

## Source, information, evidence

Classify every item three times, because the three answers are independent.

**The source** is the object you are holding.

- **Original:** the first recording of the thing, in its first form. A church register page,
  a census household sheet, a signed letter.
- **Derivative:** a copy or transformation of an original: a transcription, an abstract, an
  index, a photograph of the page, a translation.
- **Authored:** a work someone composed from other material: a family tree, a compiled
  family history, a local-history book, an encyclopedia entry.

A photograph of an original page is derivative as a copy, and you can treat it as the
original only when you have checked it is complete and legible. An index entry points to a
record and is never the record.

**The information** is each statement the source makes, judged separately.

- **First-hand:** the informant took part in or witnessed the event.
- **Second-hand:** the informant was told.
- **Undetermined:** the record does not say who knew it, or how.

One record mixes these. A death entry may be first-hand for the date of death (the
registrant was present) and second-hand for the birth year (the registrant was told).
Record the informant and how close they were in `assets/statements.csv`.

**The evidence** is what a statement does for the question you asked.

- **Direct:** it answers the question by itself. A baptism entry naming the child, the date
  and both parents answers "who were the parents".
- **Indirect:** it answers only in combination with other items.
- **Negative:** the absence of an expected entry, which means something only when the record
  would have been made and the scope searched is known.

The same statement can be direct for one question and indirect for another, so classify
against the research question.

## Proof levels

| Level | Meaning |
| --- | --- |
| proved | The five-part standard is met, at least two independent original sources support it, and no unresolved conflict or credible alternative remains. A further record that contradicts it would be a surprise. |
| probable | The evidence supports it clearly and nothing found points elsewhere, but a part of the standard is incomplete. It normally rests on more than one original source, or on one strong original plus consistent indirect evidence. A single-original probable is allowed, and the audit flags it with a warning. |
| possible | The conclusion fits the evidence but so do others, or the evidence is thin. Worth a next search, not worth stating as fact. |
| not proved | A reasonable search found nothing that supports it, or the evidence cannot decide. This is not a finding that it is false. |
| disproved | Reliable evidence contradicts it, or it is incompatible with the dates or places the records fix. |

Two rules cap a level. Authored and derivative works never count toward proved or probable;
a conclusion supported only by them stays at possible. Negative evidence alone never makes a
positive conclusion proved.

Independence matters: a church register entry and a later certificate copied from it are one
original source plus a derivative, not two. `scripts/audit_registers.py` counts distinct
original sources; deciding whether two of them are truly independent is the researcher's
judgement and goes in the reasoning.

## Family labels

The register's level maps one-to-one to a plain-language label for relatives. The label is
never stronger than the level. This is the one place the mapping is written; every report and
summary uses these words.

| Proof level | Label for relatives |
| --- | --- |
| proved | Shown by the records |
| probable | Likely, but not certain |
| possible | Possible, not yet shown |
| not proved | Not shown |
| disproved | The records point elsewhere |

## Leads are not evidence

An online tree, a compiled history, a forum post, a surname that is common in one village, a
likeness between two photographs and a DNA match nobody has explained are leads. Follow them
to the record they claim to rest on. If the record is found and says so, the record is the
evidence and the lead is footnoted. If it is not found, the lead stays a lead, in the log as
a follow-up.

A family story is treated the same way. It often preserves something true and garbles the
rest, and the garbling is usually in the names and the order.

## Proof summary or proof argument

A **proof summary** is a few sentences: the conclusion, the records that state it directly,
and their citations. Use it when direct evidence from original sources agrees.

A **proof argument** is a written case. Use it when the evidence is indirect, when records
conflict, or when two people share a name. It states the question, lists the items with their
classes, walks through the correlation, takes each conflict in turn with the reason it was
resolved, rules out the alternatives, and ends with the conclusion and its level.

## Worked example: a clear case

Fictional. Question: who were the parents of Ana Verhoeven, baptised in the fictional parish
of Alderbrook in 1851?

- A baptism entry in the parish register, original, lists the child, the date, the father
  Pieter and the mother Johanna, and names two godparents. The informant is the officiant,
  who was present: first-hand for the baptism, undetermined for the parents' names. Direct
  evidence.
- A marriage entry for Ana in 1874, original, gives her parents as Pieter and Johanna. The
  informant is the bride at the ceremony: first-hand for her marriage, second-hand for her
  parentage in the sense that she was told it. Direct evidence.

Before the level was set, the coverage list was closed: the baptism register for 1850-1852
(searched-found), the marriage register for 1874 (searched-found) and the neighbouring
parish's baptisms for 1851 (searched-not-found, no second Ana of those parents). No
same-name child of other parents appeared in the district. That is the reasonably exhaustive
search the level rests on.

Two original sources, different record types, different dates, agreeing. Proof summary: Ana
was the daughter of Pieter and Johanna Verhoeven. Level: proved. Label: Shown by the records.

## Worked example: two people with one name

Fictional. Two men named Jan Brodsky appear in the same fictional district in 1880. One is a
miller, the other a labourer, and a marriage record names "Jan Brodsky" with no occupation.

Keep two candidates, A (miller) and B (labourer). The marriage record names a witness, a
neighbour of A in the census and a godparent of A's children. That correlation is indirect
evidence for A. Neither a shared name nor the district decides it. The proof argument states
the cluster, notes that B has no recorded tie to the witness, and rules B out only as far as
the cluster supports. Level: probable, because one cluster rests on one record set. Label:
Likely, but not certain. A later record naming the occupation would move it.

## Worked example: a negative result

Fictional. The family story says a brother named Karel emigrated before 1900. The household
list of 1890 shows no Karel; the search covered that household only.

Recorded as negative evidence with its scope: "household of the family farm, 1890 only". It
does not show Karel never lived there, only that he was absent that year. Level for the
conclusion "Karel was a child of the household": not proved. Label: Not shown. The follow-up
is the baptism register for the ten years before the household list, which the coverage list
shows as searched-not-found only for the first five.
