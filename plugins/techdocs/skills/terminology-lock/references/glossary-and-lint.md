# Glossary and generated lint

Read this when writing the glossary file and the generator that turns it into checks. The
rule that matters most: the glossary is the only file people edit. Everything below it is
generated, and a generated file edited by hand is overwritten on the next run, which is
how a hand fix disappears silently.

## Contents

- [Glossary schema](#glossary-schema)
- [What the generator writes](#what-the-generator-writes)
- [Generated Vale style](#generated-vale-style)
- [UI string check](#ui-string-check)
- [Rollout](#rollout)

## Glossary schema

```yaml
- term: workspace
  plural: workspaces
  proper_noun: false
  definition: >
    The container for a team's boards, members and billing. Not a code repository,
    which we call a repository.
  code_name: project            # API fields and URLs keep project_id, /projects/
  banned:
    - word: project
      reason: Means a code repository in our Git integrations; readers confused the two.
      ambiguous: true
      patterns: ["project settings", "create a project", "your project"]
    - word: work space
      reason: Spelling variant.
    - word: space
      reason: Used in early marketing; collides with disk space and whitespace.
      ambiguous: true
      patterns: ["create a space", "your space", "space settings"]
  decided: 2026-03-04
  decision: https://example.com/decisions/0042
```

`ambiguous: true` with `patterns` means the generator emits only the listed phrasings, in a
lower-severity rule, instead of banning the bare word. Keep the decision link: it is where
the next person finds why this was settled, and the reason a ban survives a disagreement.

## What the generator writes

One script in the repository, run in CI, produces every downstream file and fails when a
committed copy differs from what it would generate:

| Output | Used by |
| --- | --- |
| A Vale `substitution` rule for unambiguous bans, level `error` | Docs lint |
| A Vale `substitution` rule for ambiguous patterns, level `warning` | Docs lint |
| A vocabulary accept list of canonical terms with their capitalisation | Vale's built-in terms check |
| A banned-pattern list for the UI string check | UI string check |
| A one-way synonym list from banned words to canonical terms | Docs search, owned with `docs-search-vocabulary` |
| A termbase export for the translation tool | Localisation team |

The generator also validates the glossary before it writes anything, and fails on:

- a banned word that is another entry's canonical term, or that is banned under two
  entries, since two `swap` keys for the same word leave the suggestion to whichever
  entry is read last. This is the collision the inventory step looks for, caught
  mechanically;
- a banned word with no reason;
- a regular-expression character in a banned word that was not escaped on purpose.

It also emits the plural of each banned word, because `\bwork space\b` does not match
"work spaces".

The "fails when the committed copy differs" check is what stops someone fixing a false
positive by editing the Vale rule directly.

## Generated Vale style

The substitution rule maps each banned form to the canonical term. Vale treats `swap` keys
as regular expressions, and `%s` in the message is filled in with the suggested and the
matched text:

```yaml
# .vale/styles/Product/Terms.yml - generated from glossary.yml, do not edit
extends: substitution
message: "Use '%s' instead of '%s'."
level: error
ignorecase: true
swap:
  work space: workspace
  work spaces: workspaces
```

```yaml
# .vale/styles/Product/TermsAmbiguous.yml - generated from glossary.yml, do not edit
extends: substitution
message: "If this means a workspace, use '%s' instead of '%s'."
level: warning
ignorecase: true
swap:
  create a space: create a workspace
  your space: your workspace
  project settings: workspace settings
```

```ini
# .vale.ini
StylesPath = .vale/styles
MinAlertLevel = suggestion
Vocab = Product

[*.md]
BasedOnStyles = Vale, Product
```

With Vale 3, the vocabulary lives at `.vale/styles/config/vocabularies/Product/accept.txt`
(one term or pattern per line) and makes Vale's built-in `Vale.Terms` rule flag the wrong
capitalisation of an accepted term. Check the vocabulary location against the Vale version
pinned in CI; older releases kept it elsewhere.

Vale ignores code spans and fenced code in Markdown by default, so `project_id` in
backticks passes. When the ambiguous rule flags an API name written in plain prose, that
is a prompt to format it as code, not to weaken the rule.

## UI string check

Run the same banned list over the source-locale catalogue: JSON or YAML message files,
gettext `.po` files, Android `strings.xml`, iOS `.strings`. Parse the file and match the
values only. Keys and message IDs are code identifiers, and a key such as
`project.settings.title` is correct even after the display text says workspace.

Report each hit with the key, the value and the canonical term, and fail on unambiguous
bans. Ambiguous patterns warn, as in the docs lint.

Do not run the check on translated catalogues with the English list. Each locale has its
own glossary entry and banned list, maintained by the localisation team.

## Rollout

1. Generate everything and run it over the whole tree at report-only. Record the count per
   rule and per surface: this is the baseline.
2. In CI, fail on errors in changed files only, and report the whole tree on a schedule.
3. Burn the backlog down by area, one pull request per area, reading each hit. Ambiguous
   hits are where most of the false positives are; add a narrower pattern to the glossary
   rather than suppressing the rule inline.
4. When the whole-tree error count reaches zero, fail on the whole tree.
5. Review warnings at each measurement. A warning that is always a false positive should be
   a narrower pattern; one that is usually right should become an error.
