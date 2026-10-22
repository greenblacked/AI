# The public accessibility statement

## Contents

- What it is for
- Template
- EU and UK public-sector requirements
- The feedback route
- Refresh checklist

## What it is for

The ACR answers a buyer's questions criterion by criterion. The statement answers a
disabled user's questions in plain language: does this work for me, what will not, how do
I get round it, and whom do I tell. Write it for that reader, from the same evidence as
the ACR, so the two never disagree. The W3C's Web Accessibility Initiative publishes a
statement generator that produces a reasonable starting structure; the content still
comes from your audit.

## Template

```markdown
# Accessibility statement for <product>

<Organisation> wants as many people as possible to be able to use <product>. This
statement covers <product> version <version> on <platforms>, at <URL or app store link>.

## How accessible this product is

We aim to meet WCAG <version> Level AA. <Product> <meets / partially meets / does not
meet> that standard. The known problems are listed below.

## Known limitations

| What does not work | Who it affects | How to get round it | When we expect to fix it |
| --- | --- | --- | --- |
| <Date picker in booking cannot be used with a keyboard> | <Keyboard-only and switch users> | <Type the date as DD/MM/YYYY> | <Q3 2027> |

## How we tested

<Internal team / independent evaluator> tested version <version> on <date>, using
<automated tools> and manual testing with <assistive technology and browser pairs>.
The full Accessibility Conformance Report is available at <link>.

## Feedback and contact

If you find a problem not listed here, or need information in a different format:

- Email: <monitored accessibility address>
- Phone: <number, with hours>
- <Third channel, for example a text relay service or postal address>

We will reply within <n> working days.

## Enforcement

<Where a regulator or enforcement procedure applies, name it and link to it.>

This statement was prepared on <date> and last reviewed on <date>.
```

Keep the status word honest. "Partially meets" with a clear list of limitations is the
normal state of a real product and reads as credible; "fully meets" invites a test that
will find something.

## EU and UK public-sector requirements

Public-sector bodies in the EU must publish a statement under the Web Accessibility
Directive (EU) 2016/2102, following the model in Commission Implementing Decision
(EU) 2018/1523. The model's sections include:

| Section | Content |
| --- | --- |
| Compliance status | Fully, partially or not compliant with the applicable standard |
| Non-accessible content | Grouped as non-compliance, disproportionate burden, and content outside the scope of the legislation, each with the reason |
| Preparation of the statement | The date, and whether the assessment was a self-assessment or by a third party |
| Feedback and contact information | How to report a problem and request inaccessible content |
| Enforcement procedure | A link to the national enforcement procedure |

A disproportionate burden claim needs its own documented assessment; it is not a label
for work that has not been scheduled. The UK's public-sector regulations require a
statement too, and GOV.UK publishes a sample statement in the same shape. National rules
add detail, so check the member state's or regulator's guidance for the body concerned.
This is procedure, not legal advice.

## The feedback route

The feedback route is the part of the statement that does real work, so test it before
publishing and on every review:

- At least two channels, at least one of them outside the product, because a user who
  cannot use the product may not be able to use a form inside it.
- A monitored address owned by a team, not a person who might leave.
- A response time you can keep, in working days, and a separate commitment to provide
  inaccessible content in another format on request.
- Each report logged as a ticket and linked back to the known-limitations table, so
  reports become findings rather than an inbox.

Send a test message through each channel and record the time to reply. If the reply took
longer than the statement promises, change the process or the promise before publishing.

## Refresh checklist

On each release:

- [ ] Changed areas re-tested and the ACR rows they touch updated
- [ ] Known-limitations table matches the ACR's Partially Supports and Does Not Support rows
- [ ] Fixed items removed; missed target dates replaced with new accepted dates, not left
- [ ] Version and dates updated in both documents
- [ ] Earlier ACR archived with its version, not overwritten

On the fixed review schedule, even without a release:

- [ ] Feedback channels tested and response times measured
- [ ] Contact details and enforcement link still correct
- [ ] Feedback received since the last review triaged into findings
- [ ] "Last reviewed" date updated
