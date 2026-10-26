# Privacy and sensitive findings

Read this at phase 1 before naming anyone, and again before phase 8.

## Contents

- Living people
- Minors
- Consent and basis
- Uploads and sending
- DNA results
- Photographs
- Sensitive findings
- What to strip before sharing

## Living people

Treat anyone who may be alive as living. A practical default, to be adjusted by the user:
someone born within the last hundred years with no death record is possibly living. The
people register has a flag for it, and a flagged person needs an inclusion basis before they
appear in any register, report or summary.

For a living person record only what the question needs: a name and a relationship. Leave out
current addresses, contact details, employers, accounts and document numbers. They are the
parts that let a stranger find the person, and a family tree rarely needs them.

## Minors

Do not trace a minor on the web at all: no searches for their name, no looking up their
school, club or accounts. Family records the user already holds may be used as they are. A
child can be named in a private register, and shared only after the filter below.

## Consent and basis

Before researching or including a possibly-living person, ask the user for:

- their basis (the person is a close relative who has agreed; the person is the user; the
  user holds a documented reason and will keep the output private);
- whether the person has agreed to appear, and in what form;
- anything the person wants left out.

Write the answers in `assets/people.csv`. If the user cannot give a basis, leave the person
out of scope in the coverage list and say why. For an interview, get consent to talk and
separately to record, and tell the speaker how the recording will be kept and who will hear it.

## Uploads and sending

Nothing is uploaded to a third-party service unless the user gives explicit permission for that specific service and file. That covers a
transcription tool, cloud notes, an online tree, a photo-restoration site and a shared
document. A document in the user's
possession can contain living people's details the user cannot see at a glance, and once it
has gone out it cannot be recalled.

Nothing is sent to an archive, a person or a forum without the user's explicit permission for
that specific message. Draft the request, show it, and let the user send it. A
request to an archive includes the names and dates the question needs and nothing else.

## DNA results

Work only with what the user supplies: a list of matches, a shared-amount figure, a stated
relationship. Do not log in to a testing service and do not request results.

A DNA match is a lead. State the alternative explanations next to it: a different common
ancestor than the one assumed, a half rather than a full relationship, an unknown parent, an
earlier shared line, or a data error. Shared amounts overlap between several relationships,
so a figure fits a range, never one answer. A match on its own supports no conclusion in the
register; it justifies a documentary search. Unexpected findings about parentage are
sensitive (below) and belong to the person whose result it is, who decides what is said and
to whom.

## Photographs

Identify people in a photograph from a caption, an inscription or the testimony of someone
who was there, and record which. Do not use face recognition or reverse image search on a
photograph of a living person, and do not conclude identity from a resemblance. Likeness is
the weakest evidence there is, and both tools expose people who never agreed to it.

## Sensitive findings

A person's religion, ethnicity, non-paternity, adoption, deportation or repression can affect a living
person's sense of who they are, and sometimes their safety. State them neutrally, in the
words of the record, and only as far as the question needs.

A list entry shows that a person was listed. It does not show what they did, whether the
charge was true, or what happened next. Do not assert a specific deed from a list. Say what
the entry says, cite it, and note what other records could clarify it.

Before sharing a sensitive finding with a relative, ask the user whether the relative wants
to know, and let the user decide how it is told. Findings that touch a living person's
parentage or origins are not put in a summary meant for the wider family.

## What to strip before sharing

Apply the filter in `sharing-and-reports.md`. In short:

- names of possibly-living people, or replace them with a relationship ("a cousin");
- minors altogether, unless the guardian has agreed;
- addresses, contact details, employers, accounts, document numbers;
- file names and metadata that carry any of those;
- sensitive findings not needed for the reader;
- free-text notes in the registers that mention any of the above.
