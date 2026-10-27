# Sharing and reports

Read this at phase 8.

## Contents

- Two readers, two documents
- Researcher report layout
- Family summary layout
- GEDCOM mapping notes
- The privacy filter

## Two readers, two documents

The researcher report is for someone who needs to check the work or carry it on. It holds the
question, the method, the evidence and the reasoning. The family summary is for relatives who
want to know what was found, in plain language, without the apparatus. They are separate
documents because mixing them fails both readers: the researcher needs the citations the
family does not want, and the family needs the labels the researcher does not need.

Neither reports a level stronger than the register supports. Run
`scripts/audit_registers.py` first.

## Researcher report layout

Start from `assets/researcher-report.md`. Sections:

1. **Question and scope.** The research question, what was left out and why.
2. **Summary of conclusions.** One line each, with the proof level.
3. **Method.** The jurisdictions and calendars involved, the name variants used.
4. **Coverage.** The coverage list with each end state, so a reader sees what was not done.
5. **Evidence and reasoning.** For each conclusion, a proof summary or proof argument.
6. **Conflicts.** Each conflicting statement and how it was resolved or left open.
7. **Sources.** The full citations.
8. **Open questions and next steps.** What would move a level, ranked.
9. **Handling note.** Who may see the report; the privacy filter applied.

## Family summary layout

Start from `assets/family-summary.html`. It prints on paper and uses no script. Sections:

1. **What we asked.** One sentence.
2. **What we found.** A short paragraph per person or link, each with the label the proof
   level maps to in `proof-and-evidence.md`, never a stronger one.
3. **A timeline.** Dates in the form the record gave them; where the calendar was converted,
   both are shown.
4. **What we do not know yet.** The open questions in plain words.
5. **Where the stories and the records differ.** Stated kindly, with the record named.
6. **Who helped.** First names of the relatives who agreed to be mentioned.

Keep it to two pages. Leave out the apparatus; the researcher report holds it.

## GEDCOM mapping notes

GEDCOM is a text format for exchanging family trees. This skill does not write the file; it
describes the mapping so the user's software can import the registers. Check each point
against the version of the format the user's software reads, because versions differ in
which structures they allow.

- **People** (`assets/people.csv`): one individual record each. The name is the best
  established form; variants and the as-written forms go in alternate names or notes.
- **Relationships:** a conclusion of kind relationship becomes a family record linking the
  two people as partners or as parent and child. Only conclusions at probable or proved
  should become relationships in the user's tree; lower levels belong in notes.
- **Events:** each event conclusion becomes an event on the person with a date and a place.
  Keep the date phrase as written, with the calendar named; many versions allow a calendar
  escape, and some software mishandles it, so test one date first.
- **Sources** (`assets/sources.csv`): one source record each, with title and the citation text.
- **Citations:** each statement becomes a citation of its source, with the page or locator,
  attached to the event or name it supports. The informant and the information class can go
  in the citation's note.
- **Confidence:** some versions carry a quality rating on a citation. Do not map it to a
  stronger meaning than the proof level has; if the software cannot hold the level, put the
  level in a note.
- **Living people:** apply the filter first; use the format's privacy flag where the software
  has one, and still strip the data, since a flag is a request and not a guarantee.

## The privacy filter

Run this on every report, summary and export before anything is shared, in order:

1. List every person in the document. For each, check the flag in `assets/people.csv`.
2. Remove or relabel possibly-living people (a relationship in place of a name) unless the
   user has recorded their agreement.
3. Remove minors unless a guardian has agreed.
4. Remove addresses, contact details, employers, accounts and document numbers.
5. Reduce each sensitive finding to what the reader needs, in neutral words.
6. Check the file names, headings, image captions and any document properties.
7. Re-read the whole document as a stranger would, then give it to the user to read before
   they send it to anyone.
