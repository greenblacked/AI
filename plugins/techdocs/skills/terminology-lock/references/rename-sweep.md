# Rename sweep

Read this when a term is being renamed. A rename fails by omission: every surface that was
changed looks right, and the one that was missed keeps the old word in front of readers
for years. The checklist is the defence, and the tracking issue is where it lives.

## Contents

- [Before the change](#before-the-change)
- [Surfaces to sweep](#surfaces-to-sweep)
- [Order while the change is in flight](#order-while-the-change-is-in-flight)
- [After it ships](#after-it-ships)

## Before the change

- Record the decision: old term, new term, reason, owner, target release.
- Run the inventory search for the old term on every surface and paste the counts into the
  tracking issue. This is the list the sweep has to bring to zero, minus what is kept on
  purpose.
- Decide what keeps the old word on purpose: API identifiers that are not being versioned,
  changelogs and release notes for past versions, legal documents that a separate process
  owns. List them in the issue so a later search does not reopen the question.
- Ask localisation for the new term in each locale before strings are sent for
  translation.

## Surfaces to sweep

| Surface | What to change | What to check |
| --- | --- | --- |
| Glossary | Move the old term to banned with the reason "renamed on DATE" | The generator's outputs regenerate cleanly |
| Docs lint | Regenerated from the glossary | The old term now fails the lint on the whole tree |
| UI strings | Source-locale values | Keys unchanged; the UI string check passes |
| Translations | Locale catalogues and the termbase in the translation tool | Each locale's own banned list includes its old term |
| Docs pages | Prose, headings, page titles, navigation labels | Lint clean; headings still match inbound anchor links or have redirects |
| Docs URLs | Paths containing the old word | Old URLs redirect, page by page (`docs-url-permanence`) |
| Docs search | Old term added as a one-way synonym to the new | A search for the old word finds the renamed page (`docs-search-vocabulary`) |
| Screenshots | Every image showing the old label | Scripted captures re-run; hand-made ones re-taken (`screenshot-rot`) |
| Error messages | Message text | Error codes unchanged; error pages updated (`error-catalogue`) |
| API | Descriptions and docs strings in the spec | Field and path names unchanged unless a new version is planned |
| CLI | Help text and output | Flag names unchanged, or the old flag kept as a deprecated alias |
| Notifications | Email, push and in-app templates | Rendered once in each locale |
| Support | Macros, help-centre articles, saved replies | Support team signs off |
| Marketing and sales | Site, decks, pricing page | Owner named in the issue, even if outside engineering |
| Release note | One entry saying the old name is now the new name | Readers searching the old name find the entry |

Code identifiers internal to the product (class names, database columns) are optional and
usually a separate, later change: renaming them buys consistency for engineers at real
migration cost, and it does not affect what readers see.

## Order while the change is in flight

Ship in an order that never shows the reader a page using the new word for a UI that still
shows the old one:

1. Search synonym first. Readers using either word find the same page from the start.
2. UI strings and translations, in the release that carries the rename.
3. Docs, screenshots and redirects, published when that release goes out.
4. Glossary ban and lint at error, merged with the docs change, so nothing reintroduces the
   old word afterwards.
5. Support, notifications and marketing on the same day as the release, from the owners
   named in the issue.

## After it ships

- Re-run the inventory search on every surface. Close the tracking issue only when every
  count is zero except the deliberate exceptions listed at the start.
- Watch support tickets for the old term for a few weeks. A steady flow means a surface
  was missed.
- Keep the search synonym indefinitely. Readers remember old names far longer than the
  product does.
