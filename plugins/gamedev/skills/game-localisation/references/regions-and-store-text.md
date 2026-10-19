# Regions, ratings and store text

Read this at step 7 when the release regions are set and at step 9 before release. It draws the line between this skill and `game-certification`, and lists the localisation-specific work on each side of it. It does not repeat the rating routes, the platform requirements or the submission calendar, which `game-certification` owns and which change by platform and by year.

## Contents

- [The split](#the-split)
- [Language is not region](#language-is-not-region)
- [Strings the platform and the store read](#strings-the-platform-and-the-store-read)
- [Store listing](#store-listing)
- [Content that differs by territory](#content-that-differs-by-territory)
- [Questions to put to legal or the publisher](#questions-to-put-to-legal-or-the-publisher)

## The split

| Question | Owner |
| --- | --- |
| Which rating route applies in which territory, and how long it takes | `game-certification` |
| What the platform tests, including its nomenclature and required languages | `game-certification` |
| Where the translated rating text, legal text and platform names live in the string table, and who owns them | This skill |
| Whether those strings fit, render and read correctly in each language | This skill, in the pass in `linguistic-qa.md` |
| What to do after a rejection for a text fault | `game-certification` to read the requirement; this skill to fix the string |

## Language is not region

A locale combines a language with a region and can include a script or variant. Godot's documentation uses English in the United States and Great Britain as the example: spelling, vocabulary, units and currency differ although the language is the same (<https://docs.godotengine.org/en/stable/tutorials/i18n/internationalizing_games.html>). Two consequences follow.

- Decide per language whether a regional variant is needed, and write the decision down. Most games ship one version per language; some need a variant where wording or units differ in a way that matters to play.
- Different content per region multiplies the translation work. Godot's documentation raises the case of different content in Europe and in China, which needs each variation translated into many languages and stored and loaded accordingly. Count variants before committing to a region list.

## Strings the platform and the store read

Some strings are checked by someone other than the player. Treat these as their own category in the table, with an owner, because an error in them can fail a submission instead of merely annoying a player.

- **Platform nomenclature.** The names of buttons, accounts, storage and hardware, in each language the platform supports. `game-certification` explains that another platform's term is a plain rejection. Take the term from the platform's developer documentation for that language rather than translating it, and keep a glossary entry per term that the translator cannot override.
- **Legal and privacy text.** Terms of service, privacy policy summaries and consent prompts have legal meaning. The translator supplies the wording only from an approved source, and legal approves the result. A privacy policy link must resolve for the language shown.
- **Rating descriptors and display.** The rating body specifies how a rating and its content descriptors are displayed in its territory, and `game-certification` covers what to display. In the table, keep these as fixed entries supplied by the rating body or publisher, with the translator unable to change them.
- **Required system-facing strings in required languages.** `game-certification` notes that legal, safety and system-facing strings must be localised into every language the storefront lists for the territory, even when the game's content is not. Ask the platform which languages and which strings, and list them in the table.
- **Achievement and trophy metadata,** which `game-certification` lists as needing to be complete and localised.
- **Error text the platform specifies.** Where a platform dictates the wording of a common error, use its wording in each language.

## Store listing

The listing is a set of strings and images, and so a localisation deliverable.

- Description, short description, keywords, feature lists and update notes, per listed language, each as a table entry with a length limit from the store's field. Take the limit from the store's current documentation, since it changes.
- Screenshots and video with text in them, per language, captured from the build being submitted. A localised screenshot taken from an earlier build is a rejection waiting to happen; `game-certification` covers the rule for metadata matching the build.
- A listed language promises that language. If the game ships interface text only, say so in the listing where the store allows it, and do not list a language you have not reviewed.
- Patch and season notes in each language follow the same pipeline; their content belongs to `game-live-ops`.

## Content that differs by territory

Some content is acceptable in one territory and not in another: imagery, symbols, names, historical or political references, gambling-like mechanics, depictions of violence or drugs, and the use of real places and organisations. Some territories also require their own approval before a game can be sold, separate from a rating. The rules differ by territory and change, so none are listed here.

Treat this as a decision for legal or the publisher, made before the content is locked, and record the outcome per territory: ship as is, ship a variant, or withhold. Variants are tracked in the table by territory, which is why step 2 includes images, audio and store text in its inventory.

## Questions to put to legal or the publisher

1. Which territories are we releasing in, and in which languages for each?
2. Does any territory require its own approval or rating, and what lead time does it have? (Then hand the answer to `game-certification` for the calendar.)
3. Which content, names or images need review per territory before lock, and who decides?
4. Which strings are legal text, and who approves their translation?
5. Does any territory need a variant, and who owns maintaining it after launch?
6. What does the platform require in each language we list, and where is that written down?
