# Rejection playbook

Read this at step 6, when a build has come back from review with a rejection notice.

## Contents

- [Read the notice back to its citation](#read-the-notice-back-to-its-citation)
- [Common causes by category](#common-causes-by-category)
- [The resubmission checklist](#the-resubmission-checklist)

## Read the notice back to its citation

Every rejection from either store's review team cites a specific guideline, policy
section or technical requirement, not just a description of the symptom. Find the exact
number or heading in the notice before doing anything else, and open the current version
of that guideline or requirement in the platform's own developer documentation — a
guideline's wording and scope both change over time, so a cached memory of what a clause
used to say is not a safe basis for a fix.

Write the citation into the rejection-response record verbatim, and do not paraphrase it
from the reviewer's summary sentence — the summary is what the reviewer thought the
problem was in one line; the citation is what the fix has to actually satisfy.

## Common causes by category

These are categories to check the notice against, not a substitute for reading the actual
citation — the specific requirement text moves, and only the current documentation for
that guideline number is authoritative.

| Category | What to check first |
| --- | --- |
| Metadata or screenshots | Do the submitted screenshots and description match the build under review, with no placeholder art, debug overlay or feature that is not actually present |
| Privacy or data declaration | Does the declaration match every SDK actually bundled in the build, not just the ones the team configured directly |
| Crash or bug on review hardware | Does the crash reproduce on the same device class and OS version the reviewer used, not only on the team's own test devices |
| Design or functionality guideline | Is the cited behaviour actually present in the build under review, on a fresh install with no prior state |
| Account or entitlement | Is the developer account, business entity or capability entitlement actually approved and attached to this build, not just requested |

## The resubmission checklist

1. The citation is written down verbatim, with a link to or quote of the current
   guideline text.
2. The fix addresses that specific citation, and nothing else has changed in the build —
   a resubmission carrying unrelated changes enlarges what the reviewer has to re-check
   and is the usual way a second rejection happens.
3. The fix is verified against the citation's actual wording before resubmitting, not
   against the team's guess at what the reviewer meant.
4. The resubmission notes reference the original rejection and state plainly what
   changed and why it satisfies the cited requirement.
5. The outcome — accepted, or rejected again with a new or repeated citation — is
   recorded, along with whether an earlier step in this skill's workflow would have
   caught it before submission.
