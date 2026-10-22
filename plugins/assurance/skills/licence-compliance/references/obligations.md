# Obligations by licence family and distribution mode

Read this in steps 1 and 4, when deciding what a licence requires of a given artefact, and
when writing the policy file. It is a map of what to check and what to send to counsel, not
a legal opinion: the cells say what the licence text typically asks for in that mode, and
the marked cells are the ones where the answer depends on facts a table cannot hold.

## Contents

- [The matrix](#the-matrix)
- [Family notes](#family-notes)
- [Non-software licences](#non-software-licences)
- [Expressions and compatibility](#expressions-and-compatibility)
- [A starting policy](#a-starting-policy)

## The matrix

| Family (examples) | Hosted only | Sent to browser | Shipped binary or image | Published library |
| --- | --- | --- | --- | --- |
| Permissive (MIT, BSD-2-Clause, BSD-3-Clause, ISC, Apache-2.0, Zlib) | No obligation triggered | Licence text and copyright notices with the copy, plus Apache-2.0 `NOTICE` contents (section 4(d) applies to any distribution, a browser download included) | Same | Keep notices in your source and package |
| Weak copyleft, file or module level (MPL-2.0, EPL-2.0) | No obligation triggered | Source of covered files, modified or not, available; notices | Same | Covered files stay under their licence |
| Weak copyleft, library (LGPL-2.1, LGPL-3.0) | No obligation triggered | Counsel: unusual in this mode | Library source, plus the recipient's ability to replace the library and relink; dynamic linking makes this straightforward, static linking needs more | Counsel |
| Strong copyleft (GPL-2.0, GPL-3.0) | No obligation triggered | Counsel | Linked into your code: counsel, usually denied. Separate program alongside: corresponding source, licence text | Your library's licence must be compatible; counsel |
| Network copyleft (AGPL-3.0) | Counsel: a modified version that users interact with over a network must offer them its source | Counsel | Counsel | Counsel |
| Source-available (BUSL-1.1, SSPL-1.0, Elastic Licence 2.0, Commons Clause riders) | Counsel: use restrictions, often aimed at hosting | Counsel | Counsel | Counsel |
| None, unknown, `NOASSERTION` | Blocked | Blocked | Blocked | Blocked |

"No obligation triggered" means the licence's conditions attach to distribution and a
hosted-only artefact does not distribute. It does not mean the component can be ignored:
the moment the same code ships in an installer, or the service is offered on-premises, the
row's other columns apply.

## Family notes

**Apache-2.0.** Section 4 asks for the licence text, notices of your modifications in
modified files, retention of upstream copyright and attribution notices, and — where the
upstream work includes a `NOTICE` file — a readable copy of its attribution notices in what
you distribute. The `NOTICE` requirement is the part most often missed, because it lives in
a separate file that dependency tools do not always collect.

**MIT, BSD, ISC.** The copyright notice and the permission notice must accompany copies.
A notices file that lists "MIT" without the copyright line does not meet it.

**MPL-2.0.** Copyleft at the file level: files under the MPL stay under it, and when you
distribute an executable form you must make the source of those files available and tell
recipients how to get it. Your own files beside them are unaffected.

**LGPL.** Aimed at libraries: a proprietary program may use the library if the recipient
can replace it with a modified version. LGPL-3.0 inherits GPL-3.0's requirement to provide
installation information for consumer devices, which matters for firmware and appliances.

**GPL.** Distributing a work based on GPL code requires offering its complete corresponding
source under the GPL. GPL-2.0's written offer must be valid for at least three years.
GPL-3.0 adds installation information for consumer devices. Whether two pieces of code form
one work or are merely aggregated on the same medium is the question to put to counsel,
with the facts: how they are linked, whether they share address space, how they
communicate.

**AGPL-3.0.** Adds a condition triggered without distribution: if you modify the program
and users interact with it remotely over a network, you must offer those users its source.
What counts as modifying it, particularly for a library linked into your service, is
contested, which is why most policies send every AGPL component to counsel rather than
encoding a rule.

**Source-available licences.** Not open source by the OSI definition. They grant use
subject to restrictions — BUSL-1.1 restricts production use beyond what the licensor's
additional use grant allows, until a change date after which the code converts to a named
open licence; SSPL places conditions on offering the software as a service. Read the
specific grant every time; two projects under BUSL-1.1 can grant very different things.

**Joke and ethical-use licences.** Licences that add a condition about how the software may
be used, such as the JSON licence's "shall be used for Good, not Evil", are not open source
and are usually denied, because the condition cannot be verified or enforced by the
recipient.

## Non-software licences

| Asset | Common licence | What to check |
| --- | --- | --- |
| Fonts | SIL Open Font Licence 1.1 | Bundling and embedding are allowed; selling the font on its own is not; a modified font may not use a reserved font name; the licence travels with the font |
| Icons and images | CC-BY-4.0 | Attribution to the creator, the licence, a link, and a note of changes, somewhere a recipient can see |
| Icons and images | CC-BY-NC variants | Non-commercial only; deny in a commercial product |
| Copied answers from Q&A sites | CC BY-SA | Share-alike on adaptations; compatibility with your code's licence is a counsel question, so rewriting is usually cheaper |
| Datasets | Varies, often bespoke | Commercial use, attribution, redistribution of the data itself |
| Model weights | Often bespoke | Acceptable-use restrictions, user-count or revenue thresholds, attribution, whether outputs are restricted; always counsel |

## Expressions and compatibility

SPDX expressions combine identifiers. `MIT OR Apache-2.0` lets you choose one; record which
you chose. `MIT AND BSD-3-Clause` means both apply, usually because the package contains
code under each. `GPL-2.0-only` and `GPL-2.0-or-later` are different licences with
different compatibility; a bare "GPL-2.0" in metadata is ambiguous and is resolved from the
source headers.

Compatibility matters when you publish a library or distribute a combined work: your
outbound licence has to be one under which the inbound licences can be honoured. The
standard example is Apache-2.0 and GPL-2.0-only, which the Free Software Foundation regards
as incompatible, while Apache-2.0 and GPL-3.0 are compatible.

## A starting policy

Adapt it per artefact; this is a default for a proprietary product, not a recommendation
for every organisation.

- **Allowed in every mode:** MIT, BSD-2-Clause, BSD-3-Clause, ISC, Apache-2.0, Zlib,
  0BSD, Unlicense, CC0-1.0, Python-2.0, OFL-1.1 for fonts.
- **Allowed with a condition:** MPL-2.0 and EPL-2.0 (source of covered files available,
  and recipients told how to obtain it); LGPL-2.1 and LGPL-3.0 (dynamically linked in shipped artefacts); GPL-2.0 and
  GPL-3.0 (hosted only, or as a separate program in a shipped image with source archived);
  CC-BY-4.0 for non-code assets (attribution generated).
- **Counsel every time:** AGPL-3.0, every source-available licence, model and dataset
  licences, anything not on these lists.
- **Denied:** no licence, unknown, `NOASSERTION`, non-commercial terms in a commercial
  product, ethical-use conditions.
