# Synonyms, renames and aliases

Read this when deciding how a failing query cluster gets fixed. The three tools look
interchangeable and are not: a synonym changes what a query matches, a rename changes what
the page says, and an alias changes where a URL goes.

## Contents

- [Choosing between them](#choosing-between-them)
- [One-way and equivalent synonyms](#one-way-and-equivalent-synonyms)
- [How common engines express them](#how-common-engines-express-them)
- [Aliases](#aliases)
- [Checks before a synonym ships](#checks-before-a-synonym-ships)
- [The synonym file](#the-synonym-file)

## Choosing between them

| Signal in the cluster | Tool | Why |
| --- | --- | --- |
| A minority of readers use another word for our exact concept | One-way synonym | Their search finds our page; ours is unchanged |
| Most readers use their word, ours is internal jargon | Rename the title or heading | The title is what both ranking and a scanning reader weight most |
| Readers use an old product name or a competitor's term | Synonym plus a mention in the body | They should find the page and see the mapping stated |
| Readers type or paste a URL that no longer exists, or a short memorable path | Alias redirect | The fix is at the URL, not in the index |
| The word means two things in our docs | Neither: split or disambiguate the pages | A synonym would send half the readers to the wrong page |

## One-way and equivalent synonyms

An equivalent synonym makes each word find the other. A one-way synonym makes the reader's
word also find ours, without changing what our word finds.

Start one-way. Equivalence is right only when the two words are interchangeable in every
page of the docs, which is rarer than it looks: making "token" equivalent to "API key"
also sends every "API key" search to session-token pages. Promote a one-way synonym to
equivalent only when the after measurement shows the reverse direction failing too.

## How common engines express them

- **Algolia** distinguishes regular (multi-way) synonyms from one-way synonyms, and also has
  alternative corrections and placeholders; DocSearch indexes are configured the same way.
- **Elasticsearch and OpenSearch** use a synonym token filter in the analyser. The
  Solr-style rule `a, b, c` declares equivalence. `a => b` is a replacement: `a` is rewritten to `b` and
  stops matching itself. The one-way form that keeps the reader's word is
  `reader => reader, ours`. Use `synonym_graph` in the search analyser rather than the index analyser, so
  multi-word synonyms are handled correctly and changing the list does not require
  reindexing the documents.
- **Meilisearch and Typesense** both support multi-way synonyms and one-way synonyms as
  index settings.

Whichever engine, keep the rules in the repository in the engine's own format and push
them from CI, so the vendor console is a deployment target and not the source of truth.

## Aliases

An alias is a URL that redirects to the canonical page: `/docs/sso` to the SAML setup page,
or an old product name's path to its renamed successor. Prefer a server-side permanent
redirect where the host allows it. Static site generators offer alias mechanisms — Hugo's
`aliases` front matter, the Docusaurus client-redirects plugin, the MkDocs redirects
plugin — and some of these generate a refresh page rather than an HTTP redirect, so check
what yours emits.

An alias is for a URL a reader types or a link someone else published. Moving or
restructuring real pages, with the redirect map and the crawl that proves nothing broke,
belongs to `docs-url-permanence`.

## Checks before a synonym ships

1. Run the cluster's example queries against a staging index with the rule applied and
   confirm the intended page appears in the top results.
2. Run the target term's own top queries against the same index and confirm their top
   results did not change. A one-way rule should pass this by construction; an
   equivalent rule often does not.
3. Search the docs for the reader's word. If it already appears with a different meaning
   somewhere, the synonym will pull that page into results for the wrong intent.
4. Record the cluster name and example queries beside the rule, so the after measurement
   can find it and a later reader knows why it exists.

## The synonym file

One file in the docs repository, reviewed like code. Each rule carries the cluster it came
from and the date it shipped. Prune it on the same cadence as the log review: a rule
whose source queries no longer appear in the log is a candidate for removal, and a rule
that now draws clicks to the wrong page comes out immediately.
