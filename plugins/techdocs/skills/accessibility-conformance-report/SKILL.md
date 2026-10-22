---
name: accessibility-conformance-report
description: "Turn accessibility audit results into an Accessibility Conformance Report (a completed VPAT) and a public accessibility statement that buyers and disabled users can rely on. Fixes the product version, platforms, standard edition and test method first; rates every criterion Supports, Partially Supports, Does Not Support or Not Applicable with evidence, the known gap and a remediation target; refuses a full-conformance claim without a complete audit; publishes a feedback route with a response time; and re-issues the report each release. Use whenever someone says \"a customer wants our VPAT\", \"the RFP asks for an ACR\", \"write our accessibility statement\", \"fill in the 508 or EN 301 549 report\" or \"our VPAT is two versions old\". Not for finding the defects (accessibility-audit), a usability review (ui-ux-review), or comparing the VPATs vendors sent you (vendor-evaluation)."
allowed-tools: Read, Grep, Glob
---

# Accessibility Conformance Report

The report is done when every criterion in the chosen standard has a rating backed by a
test result for this product version, every rating short of Supports names what fails,
where, the effect on a user and a remediation target, the public statement says the same
thing in plain language with a working feedback route, and a date is set to re-issue
both.

The usual failure is the optimistic VPAT: a sales request lands, someone copies last
year's report or fills the template from memory, and most rows say Supports with remarks
that quietly describe defects. Procurement teams increasingly test what they buy, and a
report contradicted by the first screen-reader session costs more trust than an honest
Partially Supports would have. In public-sector and regulated procurement a false claim is
also a contractual problem. The honest report is the one that survives.

This is a documentation procedure, not legal advice. Whether a law applies to the
product, and what it requires, is a question for counsel.

## Scope

Use for: an Accessibility Conformance Report from the ITI VPAT template in any edition, a
public accessibility statement, an EU model statement for a public-sector site, refreshing
either for a new release, and answering a buyer's questions about a rating.

Not for: finding the defects, which is `accessibility-audit` and must come first;
a broader usability critique, which is `ui-ux-review`; judging the VPATs third-party
vendors sent you during a purchase, which is `vendor-evaluation`; screenshots and alt text
in the product docs, which is `screenshot-rot`.

## Workflow

### 1. Fix the scope before reading any result

Write these down first, because every rating is only true relative to them:

- **Product and version.** The exact name and the version or build tested. A report
  without a version is undatable and therefore unusable.
- **Platforms.** Web (which browsers), iOS, Android, desktop. Each is a separate set of
  results; a rating covers all of them or says which one it covers.
- **Standard and edition.** Ask the requester which they need: the WCAG edition for a
  general buyer, the Section 508 edition for US federal, the EU edition (EN 301 549) for
  European public procurement and products under the European Accessibility Act, the
  INT edition when more than one applies. Name the WCAG version (2.0, 2.1, 2.2) and level
  (A and AA is the usual target).
- **Inclusions and exclusions.** Which parts of the product, which documentation and
  support channels, which embedded third-party components. An exclusion is stated with
  its reason, not left out.
- **Test method.** Who tested (internal team or independent evaluator), when, the
  automated tools and versions, and the assistive technology and browser pairs used.

Download the current template from ITI rather than reusing last year's copy, and check
which WCAG version its tables cover.

### 2. Gate on a complete audit

List every success criterion in scope and look for a test result for each, per platform.
A criterion with no result has no rating yet. The VPAT terms allow Not Evaluated only for
WCAG Level AAA criteria, so a gap at A or AA is closed by testing it, not by leaving it
blank or guessing Supports.

If the audit is missing or older than the version being reported, stop and get it run
first with `accessibility-audit`. Sample the way WCAG-EM describes: a structured sample of
templates and states plus every step of the core user journeys, because conformance under
WCAG applies to complete processes, and a checkout that fails at payment fails as a whole.

An automated scan alone is not an audit. It catches a minority of failures and cannot
judge most criteria, so a report built only on a scan rates criteria nobody tested.

### 3. Map findings to criteria

Build one table: criterion, platform, finding identifiers, pages or screens affected,
severity, ticket. One finding often maps to several criteria (a custom dropdown built
from generic elements can fail 2.1.1 Keyboard, 2.4.7 Focus Visible and 4.1.2 Name, Role,
Value at once), and several findings land on one criterion.
Working from this table rather than from the template keeps the remarks traceable to
evidence a reviewer can open.

### 4. Rate each criterion by rule, not by feel

Apply the decision table in `references/acr-rating.md`. The short form:

- **Supports** only when testing found no known defect against the criterion in scope,
  or an equivalent facilitation meets it.
- **Partially Supports** when some functionality fails it. One known defect in scope is
  enough; "mostly works" is Partially Supports.
- **Does Not Support** when the majority of functionality fails it.
- **Not Applicable** only when the content the criterion governs does not exist, with the
  reason in the remark ("no prerecorded video in the product").

Rate the worst platform when one rating covers several, or split the remark by platform.
A Supports row whose remark mentions a defect is the defect this procedure exists to
prevent; correct the rating rather than the wording.

### 5. Write remarks a buyer can act on

Every rating other than Supports and Not Applicable gets a remark with what fails, where,
the effect on a user, any workaround, and the remediation target as a release or a
quarter with its ticket. Commit only to dates the owning team has accepted; a missed
date in a published report is a second broken promise. Supports rows get a short remark
naming how it was verified when that is not obvious. `references/acr-rating.md` has
remark templates and weak-versus-usable examples.

For the 508 and EU editions, also rate the functional performance criteria, the
software and hardware chapters where they apply, and the documentation and support
services chapter. That chapter covers whether your help centre and support channels are
themselves accessible, which a web audit alone does not test.

### 6. Review against the evidence

A second person, ideally one who ran part of the audit, reads every rating against the
mapping table and the findings. Check in particular:

- No conformance summary claims full conformance unless every criterion in scope is
  Supports or Not Applicable.
- No row contradicts its own remark.
- Third-party components are rated, or referenced to their own vendor's report with its
  version and date.
- Overlay or toolbar widgets are not cited as the reason a criterion is met; the
  underlying content is what is rated.

Route the result through whoever signs procurement documents before it leaves the company.

### 7. Write the public accessibility statement

Draft it from the same evidence, with the template in `references/accessibility-statement.md`.
It states the standard and level, the honest status (meets, partially meets, does not
meet), the known limitations with workarounds and target dates, how the product was
assessed and when, and a feedback route: at least two contact channels, one of them not
the product itself, and a response time you can keep, stated in working days. For an EU
public-sector site, follow the model statement in Commission Implementing Decision (EU)
2018/1523, including the link to the enforcement procedure.

Test the feedback route before publishing: send a message through each channel and time
the reply.

### 8. Publish, version and refresh

Publish the ACR with its product version and report date in the filename and on the first
page, keep earlier reports archived, and link the statement from every page footer. Put
re-issue on the release checklist: for each release, re-test what changed, update the
affected rows and remediation targets, and re-date both documents. Review the statement
on a fixed schedule even when nothing ships, because commitments in it age.

## What to hand back

- The scope block: product, version, platforms, standard edition, WCAG version and level,
  exclusions with reasons, and the test method.
- The completeness check: any criterion without a result, and the plan to test it.
- The criterion-to-finding mapping table.
- The completed ACR rows, with remarks and remediation targets.
- The accessibility statement draft, and the result of testing its feedback route.
- The re-issue trigger added to the release checklist and the statement review date.

## Anti-patterns

**Supports with a confession in the remark.** "Supports. Some images lack alternative
text." Buyers read remarks; the contradiction tells them the whole report is unreliable.

**A report from a scan.** Automated tools cannot judge most criteria, so the report
asserts results nobody obtained.

**No version, no date.** A buyer cannot tell whether it describes what they are buying.

**Boilerplate remarks.** "Working to improve" on every row carries no information and
reads as evasion.

**A statement with no way to reach anyone.** The feedback route is the part of the
statement a disabled user actually needs.

**Copying another product's report.** Shared components do not make two products
conform equally; each is tested and rated on its own.

## Reference files

- `references/acr-rating.md` — read at steps 1, 4 and 5: choosing the VPAT edition, the
  rating decision table, edge cases, remark templates with weak and usable examples, and
  the report's front-matter fields.
- `references/accessibility-statement.md` — read at steps 7 and 8: the statement
  template, the EU model statement's required sections, feedback-route and response-time
  guidance, and the refresh checklist.
