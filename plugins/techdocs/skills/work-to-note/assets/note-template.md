---
# Fill every field. The checker reads these lines with a strict subset of YAML: plain
# or quoted values, "- item" lists, true/false, unquoted dates. Quote any value that
# contains a colon followed by a space, and avoid folded or block scalars (> and |) and
# inline lists, which the checker rejects.
title: Sentence-case title that names the lesson, not the day
description: One sentence of about 140 to 160 characters that says what the reader learns and when it applies, written to stand alone in a search result.
# One of: adr, pattern, tool, standard, runbook, guide, reference.
type: pattern
# Only tags that already appear in the vault's taxonomy.
tags:
  - replace-with-a-taxonomy-tag
created: 2026-01-01
modified: 2026-01-01
draft: true
# An ADR also needs a lowercase status, and a decided date unless it is proposed:
# status: proposed
# decided: 2026-01-01
#
# Add these four together only when the body carries a matching Evidence section.
# review-due is after reviewed and at most 366 days later. Never write
# operationally-verified without evidence from a real environment the owner supplied.
# evidence: source-reviewed
# reviewed: 2026-01-01
# review-due: 2026-07-01
# destructive: true
---

<!--
Body rules: no H1 (the title is the page heading), start at ## headings, and use the
section shape for the chosen type from references/note-types.md. Every claim that could
be wrong carries a mark from references/claims-and-callouts.md. For an Evidence section, copy the layout from
references/frontmatter-and-evidence.md. Delete these comments before the note is published.
-->

## Context

What was going on, in the terms a stranger needs. Link at least one related note, for
example [[replace-with-a-real-note]].

## The lesson

The reusable part, stated as a rule with its reason. Commands in fenced blocks with a
language. Example domains and documentation addresses only.

## Failure modes

How this goes wrong and how to notice.

## Related

- [[replace-with-a-real-note]]: why it is related.
