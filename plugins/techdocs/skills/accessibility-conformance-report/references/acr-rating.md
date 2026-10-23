# Rating criteria and writing the report

## Contents

- Choosing the edition
- Front matter
- The rating terms
- Decision table
- Edge cases
- The mapping table
- Remark templates and examples

## Choosing the edition

ITI publishes the VPAT template in editions that differ only in which standards' tables
they contain. Pick from what the requester will evaluate against, and ask when unsure:
an edition with tables you did not need is extra work, one missing a table is rejected.

| Requester | Edition | Tables beyond WCAG |
| --- | --- | --- |
| A general buyer or a private-sector RFP naming WCAG | WCAG | None |
| A US federal agency, or a buyer citing Section 508 | Section 508 | Functional performance criteria, hardware, software, support documentation and services |
| European public procurement, or a product under the European Accessibility Act | EU (EN 301 549) | The EN 301 549 clauses, including functional performance statements, non-web documents, software, documentation and support services |
| More than one of the above | INT | All of them |

Check the WCAG version the requester names against the version the template's tables
cover. Section 508 incorporates WCAG 2.0 A and AA by reference; EN 301 549 versions
reference a specific WCAG 2.x version; many private buyers now ask for 2.2. Reporting
against the newest version the buyer accepts costs little extra, because the later
versions mostly add criteria (2.2 also removed 4.1.1 Parsing; 2.4.7 Focus Visible
stays at Level AA).

## Front matter

Fill every field; buyers read this page first and stop if it is vague.

| Field | What goes in it |
| --- | --- |
| Name of product and version | Exact product name and the version or build tested |
| Report date | The date the report was issued, not the template's date |
| Product description | Two or three sentences a buyer can match to what they are buying |
| Contact information | A monitored address for accessibility questions, not a salesperson |
| Notes | Scope: platforms, included modules, exclusions with reasons, third-party components and where their reports are |
| Evaluation methods used | Who tested and when; automated tools and versions; manual methods; each assistive technology with its browser and operating system versions |
| Applicable standards and guidelines | Which standards and levels this report covers, matching the tables included |

## The rating terms

Paraphrased from the VPAT 2.x terms; quote the exact definitions from the template copy
you are filling in.

| Term | Meaning |
| --- | --- |
| Supports | The functionality has at least one method that meets the criterion without known defects, or meets it with equivalent facilitation |
| Partially Supports | Some functionality does not meet the criterion |
| Does Not Support | The majority of functionality does not meet the criterion |
| Not Applicable | The criterion is not relevant to the product |
| Not Evaluated | The product was not evaluated against the criterion; allowed only for WCAG Level AAA |

## Decision table

Work down the table and stop at the first row that matches.

| Evidence for this criterion, in scope | Rating | Remark must say |
| --- | --- | --- |
| No test result | None yet: test it | Nothing is published until it is tested |
| The content the criterion governs does not exist | Not Applicable | Why it does not exist ("no audio or video content") |
| Most screens or core journeys fail | Does Not Support | The scale of failure, the user effect, the plan |
| At least one known failure, anywhere in scope | Partially Supports | What fails, where, the effect, workaround, target |
| Tested on every platform and journey in scope, no known failure | Supports | How it was verified, when that is not obvious |

"Majority" is a judgement; make it on the share of screens or journey steps affected and
say which way it went in the remark. When in doubt between Partially Supports and Does
Not Support for a failure on a core journey, choose the worse: a checkout a screen-reader
user cannot finish is not a partial experience for that user.

## Edge cases

- **Several platforms, one row.** Rate the worst platform, or split the remark by
  platform ("Web: Supports. iOS: Partially Supports — ..."). Never average.
- **A third-party component inside the product.** Its failures are the product's
  failures. Rate the row on the combined behaviour and name the component in the remark;
  attach or reference the component vendor's own report with its version and date.
- **User-generated content.** Rate what the product controls (the authoring interface,
  the prompts for alternative text, the default markup), and say in the notes that content
  users author is outside the report.
- **4.1.1 Parsing in a 2.0 or 2.1 report.** WCAG 2.2 removed it, and the W3C errata for
  2.0 and 2.1 note it is to be treated as always satisfied for content in HTML or XML.
  Cite the errata in the remark rather than testing markup validity.
- **Equivalent facilitation.** Allowed for Supports, but the remark must describe the
  alternative and how a user reaches it. An alternative that requires contacting support
  is not equivalent for a task users perform themselves.
- **An overlay or accessibility toolbar.** Rate the product without it. A widget layered
  on top does not change whether the underlying content meets the criterion.
- **A fix merged but not released.** The rating describes the version in the report.
  Mention the fix and the release it ships in; do not upgrade the rating early.

## The mapping table

Build this before touching the template; every remark is written from it.

| Criterion | Platform | Finding IDs | Screens or journeys | Severity | Ticket | Rating |
| --- | --- | --- | --- | --- | --- | --- |
| 1.1.1 Non-text Content | Web | A-012, A-019 | Product gallery, order history | High | ACC-341 | Partially Supports |
| 1.3.1 Info and Relationships | Web, iOS | A-004 | Settings form | High | ACC-322 | Partially Supports |
| 2.4.7 Focus Visible | Web | none | All templates sampled | none | none | Supports |
| 1.2.2 Captions (Prerecorded) | All | none | No prerecorded video | none | none | Not Applicable |

A finding that maps to several criteria appears on each row. A rating with no finding IDs
and no "none" in the evidence column is a row nobody checked.

## Remark templates and examples

Template for any rating short of Supports:

```text
<What fails> on <where> (<platform>). <Effect on a user>. <Workaround, if any>.
Planned fix: <release or quarter> (<ticket>).
```

| Weak | Usable |
| --- | --- |
| "Some images may be missing alt text." | "Product images in the gallery and order history have no text alternative (web). Screen-reader users hear the file name instead of the product. Product names are in the adjacent text. Planned fix: release 6.3 (ACC-341)." |
| "We are committed to improving keyboard access." | "The date picker in booking cannot be operated by keyboard (web). Keyboard-only users cannot choose a date. Workaround: type the date into the field in DD/MM/YYYY form. Planned fix: Q3 (ACC-355)." |
| "Supports with minor exceptions." | Rate it Partially Supports and write the remark above. |
| "N/A" | "Not Applicable: the product contains no prerecorded audio or video." |

Keep remarks factual and in the present tense. A buyer's accessibility team will test the
worst-sounding rows first; a remark that already tells them what they will find, and when
it changes, is the one that survives that test.
