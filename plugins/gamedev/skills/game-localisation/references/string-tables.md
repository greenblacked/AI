# String tables and pseudo-localisation

Read this at step 2 when the table is being designed, and again at step 3 when the pseudo-localised pass is set up. It covers what an entry holds, how keys and placeholders are written, and how to run the pass that finds hard-coded text and clipped layouts before any translation exists.

## Contents

- [The entry](#the-entry)
- [Keys](#keys)
- [Placeholders](#placeholders)
- [Table layout](#table-layout)
- [Pseudo-localisation](#pseudo-localisation)
- [Running the pass](#running-the-pass)

## The entry

One row per string, with these fields. The first three are what most engines already store; the rest are what make the entry translatable by someone who has never seen the game.

| Field | What it holds | Why it exists |
| --- | --- | --- |
| Key | A stable identifier, never reused | The code and the translations both point at it |
| Source text | The string in the source language | What the translator reads first |
| Note | Where it appears, who speaks, to whom, in what tone | The same word means different things in different places |
| Context | The disambiguator for identical source text | Lets one English word translate two ways, such as "Close" as an action against "Close" as a distance |
| Maximum length | Characters, or a pixel width for a fixed-size control | Turns "it does not fit" from a surprise into a defect against a stated limit |
| Placeholders | Each name, its type and an example value | A translator cannot reorder what they cannot identify |
| Gender and plural data | Which placeholders drive a plural or a select | See `grammar-and-formatting.md` |
| Screenshot | A capture of the string on screen, or a path to one | Context a note cannot carry |
| Status | New, translated, reviewed, changed since translated | Drives the delta in a live game |

Godot's context mechanism is the model for the second field: the same source text takes a different context argument per meaning, so the translation table can hold two entries for it (<https://docs.godotengine.org/en/stable/tutorials/i18n/internationalizing_games.html>).

The maximum length is a measured limit, not a guess. Set it from the control's size and the longest translation seen so far, and revise it when a longer one arrives. A character count is a proxy: proportional fonts and different scripts give different widths for the same count, so a fixed-size control wants a pixel limit checked in the engine.

## Keys

- Use an identifier that describes the position, not the words: `shop.confirm_purchase.title`, not `Are you sure`. The text changes; the position does not. Godot's documentation notes that a unique ID per string is what lets the text be revised while it is being translated (<https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_translations.html>).
- Never reuse a key for a different string. A reused key keeps its old translations and shows the wrong text in every language but the source.
- Do not build a key from data at runtime unless the table contains every value. Godot's documentation shows `tr("GAME_STATUS_%d" % status_index)`; a status added without its row shows the raw key in every language, and the pseudo-localised pass is how you find it.
- Mark strings that must not be translated, such as a player's name displayed in a label. Godot's labels translate automatically when their text matches a key, and the documented fix is to disable auto translate on the node.

## Placeholders

- Name them. `{character} picked up the {weapon}` lets the translator choose the order of both; positional `%s` and `%s` fixes it. This is Godot's own recommendation (<https://docs.godotengine.org/en/stable/tutorials/i18n/internationalizing_games.html>).
- Give each placeholder one meaning and say which it is in the entry. A translator who sees `{0}` and `{1}` cannot tell which holds the name.
- Do not put a number into a string by concatenation or by an `if count == 1` branch; see `grammar-and-formatting.md`.
- Keep markup and engine tags out of the translatable text where the engine allows it, and when it does not, mark the tags so a translator leaves them intact and a check can confirm they survived.

## Table layout

- One table per feature or screen, not one file for the game. A single file conflicts on every merge and gives a translator no sense of where a string lives.
- Keep the source language table authoritative. Translations hold the key and the translated text and are never edited to change the source meaning.
- Export to the format your vendor works in. Godot reads CSV and gettext `.po` files (<https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_translations.html>); the choice matters less than that the export carries every field above, including the note and the maximum length, since a spreadsheet column is the only place a translator will see them.
- Version the changes: the status field and a list of keys changed since the last handoff are what keep a live game's delta small.

## Pseudo-localisation

A pseudo-localised build replaces every translated string with a deliberately altered version of itself. Four transformations cover what is worth catching:

1. **Accents on the letters.** The text remains readable but is visibly changed, so any string that still looks plain bypassed the table. It also exercises glyph coverage for accented Latin characters.
2. **Expansion.** Pad the string, or double the vowels, so that a control with no room to grow shows it. Godot offers both: doubling vowels, and an `expansion_ratio` setting that pads with underscores, where a ratio of 0.3 is described as sufficient for most practical cases (<https://docs.godotengine.org/en/stable/tutorials/i18n/pseudolocalization.html>).
3. **Brackets or markers at both ends.** If the closing marker is missing on screen, the string is clipped. This is the quickest way to see truncation at a glance.
4. **Fake right-to-left.** Godot's `fake_bidi` setting simulates right-to-left text to expose layout faults; the pseudolocalisation page describes it as a way to find layout issues, not to test font support.

Placeholders must survive untouched, or the pass breaks the formatting it is testing. Godot's `skip_placeholders` setting exists for this and also makes a missing argument visible.

If the engine has no pseudo-localisation, write one: it is a function over the string table at load time with a toggle in a development menu, not a project.

What it cannot show: whether a font covers Chinese, Japanese, Korean or a right-to-left script, because the text stays readable Latin (stated in the same Godot documentation). It also cannot show whether a translation is correct. Step 5 and step 8 do those.

## Running the pass

1. Turn the pass on in the first build that has a real interface, and leave a toggle in the development menu.
2. Walk every screen and read for three things: unaltered text (a literal or a missing key), clipped or overlapping text (a limit that is too small), and boxes where a character should be (a glyph gap).
3. File each as a defect against the control, not against a language: the fix is in the layout or the code and benefits every language.
4. Run it in CI where the engine allows a headless screenshot or a layout check, so that a new hard-coded string fails a build rather than waiting for a person to see it.
5. When the first real translation arrives, measure the longest string for each entry and replace the assumed expansion with the measured one.
