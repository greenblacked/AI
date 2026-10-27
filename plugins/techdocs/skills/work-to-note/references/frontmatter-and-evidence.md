# Frontmatter and evidence

Read this in step 4. It describes the fields a vault of this kind expects and the evidence section that backs a claimed level. The vault's own standard overrides it.

## Base fields

Write all seven on every note, even where the vault's checker would skip a note without evidence fields.

| Field | Format |
| --- | --- |
| `title` | Sentence case, names the lesson. It becomes the page heading, so the body has no H1. Quote it when it contains a colon followed by a space. |
| `description` | One sentence of about 140 to 160 characters: what the reader learns and when it applies. Not the title restated. `check_note.py` warns outside 50 to 170 characters. |
| `type` | One of `adr`, `pattern`, `tool`, `standard`, `runbook`, `guide`, `reference`. |
| `tags` | A list with at least one tag, all from the vault's taxonomy. A new tag is added to the taxonomy in the same change. Lowercase, hyphen-separated. |
| `created` | `YYYY-MM-DD`, unquoted. |
| `modified` | `YYYY-MM-DD`. Update it when the meaning changes, not for a typo. |
| `draft` | `true` or `false`. Use `true` while the note is unfinished; it keeps the note off the published site. |

Optional: `aliases`, a list of short names that wikilinks may use; add one only when the short name is genuinely used.

## ADR fields

- `status`: lowercase, one of `proposed`, `accepted`, `rejected`, `deprecated`, `superseded`. A superseded record also sets `superseded_by` to its successor and is linked in both directions; the vault's ADR index requires that field.
- `decided`: the date of the decision, required for every status but `proposed`. If it is set on a proposed record it must still be a valid date.
- An accepted record is immutable apart from status and links. A changed decision is a new record that supersedes the old one.

## Evidence levels

Evidence is optional. A note without it is simply unrated, and unrated is better than overstated.

| Level | Meaning | When you may claim it |
| --- | --- | --- |
| `source-reviewed` | Every technical claim (commands, flags, fields, limits, names, defaults, versions) was checked against current official documentation on the `reviewed` date. A claim that could not be confirmed was corrected, hedged or removed. | You opened the sources this session and compared each claim. |
| `lab-tested` | Everything above, and the main procedure was run in a disposable lab. | You ran the procedure and have the commands, versions and output. |
| `operationally-verified` | Everything above, and the procedure was carried out against a real environment of the kind the note describes. | Only with evidence the owner supplies: which system, who checked it, when, what was observed. An agent never sets this level on its own. |

Fields that go with a level:

- `reviewed`: the day of the review behind the level. Not in the future, not before `created`.
- `review-due`: the day of the next review, after `reviewed` and at most 366 days later. Pick a date that matches how fast the sources change; a fast-moving tool deserves months, not a year.
- `destructive: true`: set when the note tells readers to delete, revoke, disable, overwrite, force or bypass something. It is only allowed with `evidence`.
- `verified`: the day the content was compared with the real system or command output it describes. It is a promise, not a modification date. Leave it out unless you ran the comparison that day. It is required, and must not be in the future, for `operationally-verified`.

`reviewed`, `review-due` and `destructive` without `evidence` are an error.

## The Evidence section

A note with `evidence` has exactly one `## Evidence` section, placed before `## Sources` if there is one, otherwise before `## Related`, otherwise at the end. Its subsections:

| Subsection | Required for | Content |
| --- | --- | --- |
| `### Sources checked` | every level | At least one https link. One bullet per page: the page, the claims it backs, and "checked" with the `reviewed` date exactly as written in the frontmatter. |
| `### Not verified` | every level | Every claim or step no source or run confirmed. Never empty; write "Nothing beyond the items above" only when that is true. |
| `### Environment` | runbooks, destructive notes, lab-tested, operationally-verified | The platform and tool versions the steps assume or were run on. |
| `### Prerequisites` | the same | What must be true or in place first, including a backup. |
| `### Expected results` | the same | What a correct run prints or leaves behind. |
| `### Failure conditions` | the same | How a reader recognises that it went wrong. |
| `### Cleanup and rollback` | the same | How to undo it. It may point at an existing section of the note by name, plus whatever that section lacks. |
| `### Lab run` | lab-tested and above; optional below | The host OS, tool versions as printed, the exact commands in one fenced block, the observed output in another, and the date. At least two fenced blocks. |
| `### Operational check` | operationally-verified | The real system, who checked, when, what was observed. |

Each required subsection must say something. Headings compare without regard to case; a heading inside a code fence does not count. A destructive note also needs a danger or warning callout in the body, outside any code fence.

## Worked skeleton

```markdown
---
title: Example runbook
description: A description of about one hundred and forty characters that says what the reader learns and when the procedure applies to them.
type: runbook
tags:
  - runbooks
created: 2026-10-10
modified: 2026-10-20
draft: false
evidence: source-reviewed
reviewed: 2026-10-20
review-due: 2027-04-20
---

## Evidence

### Sources checked

- [Tool documentation](https://example.com/docs): the flags and defaults used above, checked 2026-10-20.

### Not verified

- Nothing was run; the commands are as documented, not as observed.
```

A runbook also needs the five executable subsections after those two, each with text.

Keep the skeleton out of HTML comments in the note. The vault's checker and `scripts/check_note.py` read a commented heading as a real one, so a commented `## Evidence` next to the real section fails as a second Evidence section. Write the section once, in place, or leave it out.
