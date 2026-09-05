# Obsidian conventions

## Contents

- [Frontmatter schema](#frontmatter-schema)
- [Tags are types, not topics](#tags-are-types-not-topics)
- [Links](#links)
- [Filenames and folders](#filenames-and-folders)
- [Maps of content](#maps-of-content)
- [Templates](#templates)

## Frontmatter schema

Every note carries the same block. Consistency matters more than completeness — a field
that is sometimes present cannot be queried.

```yaml
---
source: https://example.com/post      # url, ISBN, "conversation with X", or "own thinking"
author: Name                          # omit if the note is the user's own idea
date: 2026-08-04                      # date processed, not date published
status: inbox | literature | permanent | evergreen
tags: [note/permanent, source/paper, area/platform]
---
```

- `status` drives everything else. `inbox` means unprocessed and safe to delete. `literature`
  means read and recorded, no claim. `permanent` means a claim in the user's words with links.
  `evergreen` is a permanent note that has survived at least one rewrite.
- `date` is when the note was processed. Publication date belongs in the source line, because
  the question the user asks later is "when did I think this", not "when was it published".
- Optional fields worth having when they apply: `rating` (1-5, only for books and courses),
  `review: true` for anything with cards attached, `up:` pointing at the parent MOC.

## Tags are types, not topics

Topics belong in links; a `#kubernetes` tag and a `[[Kubernetes]]` note compete, and the tag
loses because it carries no context. Keep the tag namespace small and structural:

| Namespace | Values | Purpose |
| --- | --- | --- |
| `note/` | `capture`, `literature`, `permanent`, `moc` | What kind of object this is |
| `source/` | `article`, `paper`, `book`, `talk`, `course`, `docs`, `thread` | Where it came from |
| `area/` | a handful of long-lived domains — `platform`, `ai-enablement`, `leadership` | Coarse filter for search |

Rules of thumb: if a tag has one member, it should have been a link. If a tag would be
obvious from the note's links, drop it. Ten to twenty tags total across the vault is healthy;
two hundred is a folksonomy nobody can use, including its author.

## Links

- Link with the note's real title: `[[Rate limiting belongs at the edge, not in the service]]`.
  Claim titles read as sentences inside a paragraph, which is most of why they are worth the
  extra effort at creation time.
- Use an alias when the sentence needs different grammar:
  `[[Rate limiting belongs at the edge, not in the service|push it to the edge]]`.
- Prefer inline links inside the argument over a bare list of related notes at the bottom. A
  link inside a sentence records *why* the two notes touch; a list at the bottom records only
  that they do.
- A link to a note that does not exist yet is legitimate and useful — it is a stub the vault
  will resolve later. Do not create empty notes to satisfy the link.
- Backlinks are the search interface. Before writing a new note, check the backlinks of the
  most obvious neighbour; the note being written often already exists in worse form.

## Filenames and folders

- Filename equals the title. No date prefixes, no numbering schemes — Obsidian resolves links
  by title, and a renamed file rewrites its links automatically.
- Keep the folder tree shallow and boring. A workable default:

```text
00-inbox/         unprocessed captures, deletable without guilt
10-notes/         all permanent notes, flat, no sub-folders
20-sources/       literature notes, one per source
30-maps/          maps of content and indexes
90-archive/       superseded notes kept for provenance
```

- Flat beats nested inside `10-notes/`. A note that belongs in two folders is the normal case,
  and links solve it; folders do not. The only justified folder split is by lifecycle, which is
  what the layout above encodes.
- Do not design this structure before the vault has notes in it. Heavy taxonomy up front is
  procrastination — the categories that matter are only visible in hindsight.

## Maps of content

A MOC is a hand-written index note: a claim about how a set of notes fit together, with links
and one line of commentary each. It is not a tag page and not an auto-generated list.

Worth writing when: an area has roughly fifteen or more notes, the user has repeatedly failed
to find something they knew they had written, or they are about to teach or present the area
and need a spine.

Not worth writing when: the area has five notes (links between them are enough), or the MOC
would only restate the tag.

```markdown
---
status: permanent
tags: [note/moc, area/platform]
---

# Map: how we think about platform reliability

The through-line: reliability work pays off where it removes a class of incident,
not where it adds a check.

## Load and shedding
- [[Rate limiting belongs at the edge, not in the service]] — why the service-level
  limiter always lands too late.
- [[Backpressure is a product decision]] — the queue depth argument.

## Open questions
- Nothing written yet on multi-region failover cost. Next source to process.
```

The "open questions" section is the part that makes a MOC useful: it turns the index into a
reading agenda instead of a trophy cabinet.

## Templates

Keep two templates only — the processed-note format and the quick-capture format from
SKILL.md. More templates than that means the note types are being invented rather than
discovered, and every extra template is another shape of note nobody rereads.
