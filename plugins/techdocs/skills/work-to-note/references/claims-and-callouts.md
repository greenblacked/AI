# Claims and callouts

Read this in steps 5 and 6. It covers how to mark a claim, the callout forms, the link rules and the index entries.

## Marking each claim

A claim is anything that could be wrong: a command, a flag, a default, a limit, a version statement, a cause, a number. Mark it with one of three states, and keep the three apart.

| State | What it means | How to write it |
| --- | --- | --- |
| Checked against a source | You read the official page on a date and the page says so | A bullet in the Evidence section, or in a Sources section: the link, the claim it backs, and "checked" with the date. Use https links only. |
| Checked against a running system | You ran it and saw the output | The command and the observed output in fenced blocks, with the tool version and the date. If the run was a helper step and not the main procedure, say so. |
| Not checked | Recalled, inferred or reported by someone else | A callout that says so, placed at the section it covers, and a line under Not verified when the note has an Evidence section. |

Do not upgrade a state in the writing. A command that worked once on one machine is checked against a running system for that machine, not for every platform. A claim copied from a ticket is not checked. A cause you inferred from symptoms is a hypothesis until a test separates it from the others.

## Callout forms

Callouts are blockquotes whose first line names a kind, with a title after it:

```markdown
> [!warning] Check before relying on this
> The retention default was recalled, not read from the current docs.
```

| Kind | Use it for |
| --- | --- |
| `> [!note]` | Neutral extra context, and the form `> [!note] Not verified` for a claim left unchecked |
| `> [!info]` | Scope, assumptions, versions checked, for example `> [!info] Scope and sources` |
| `> [!tip]` | A shortcut or a recommended practice |
| `> [!warning]` | Something that causes outages, data loss or insecurity, and the form `> [!warning] Check before relying on this` for a claim that may have changed |
| `> [!danger]` | An irreversible action; a destructive note needs one |

Limits: about two callouts on a screen. More than that means the prose needs work, or the whole note is unchecked and should say so once at the top. A compliance note also carries `> [!warning] Not legal or audit advice`.

Inline markers for smaller cases: "(verify for your version)" after a version-dependent value, and "Illustrative" before output that differs per machine.

## Examples and addresses

Use example domains (`example.com`, `example.org`) and the documentation address ranges `192.0.2.0/24`, `198.51.100.0/24` and `203.0.113.0/24`. Never real hosts, addresses, account names or tokens, including ones that are only internal. Put variables at the top of a command block and reference them, so the block is copy-pasteable.

## Wikilinks

- Link with `[[note-name]]`, the file name without extension. Add the folder, `[[adr/index]]`, when the bare name is ambiguous, as with index pages.
- Use `[[note-name|display text]]` for different text and `[[note-name#Heading]]` for a section.
- Inside a table, escape the pipe: `[[note-name\|display text]]`.
- Link to at least one other note that exists. A link that does not resolve fails the vault's link check after a build, so check the name before writing it.
- External links are ordinary Markdown links and always https.

## Registering the note

- **Folder index.** Every folder has an `index.md` of hand-written wikilinks. Add the note there with a one-line description in the same style as its neighbours. The vault's own checker may not test this, so `check_note.py --vault` does.
- **ADR index.** An ADR also gets a row in the Records table of the ADR index, in the same style as the rows above it, for example `| [[0001-short-title\|0001]] | Title |`.
- **Taxonomy.** A tag that does not yet exist is added to the taxonomy in the same change that first uses it. Prefer an existing tag.
- **Pages that need nothing.** Home, the all-notes list and the tag browse page are generated or automatic in a vault of this kind; do not hand-edit them unless the vault's standard says to.
