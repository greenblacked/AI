---
name: game-localisation
description: "Take a game from one language to many without shipping broken text. Moves every player-facing string into keyed tables with a translator note and a length limit from day one, pseudo-localises early to expose hard-coded and clipped text, handles plurals and gender with ICU MessageFormat rather than concatenation, plans fonts and fallback per script, right-to-left layout, voice and subtitle timing and locale formats, then runs linguistic QA in context with screenshots and a bug taxonomy. Use whenever someone says \"we are adding German and Japanese\", \"the text overflows the button\", \"I see boxes instead of characters\", \"how do I do plurals in Russian\", or \"translators have no context\". Not for ratings and store submission (game-certification), English UI wording (content-design), season or patch comms (game-live-ops), or build size and audio import (game-assets)."
allowed-tools: Read, Glob, Grep
---

# Game Localisation

A game reaches a new language with every string translated in context, every line fitting the space it was given, every character drawn, and nothing the translator could not have known about assembled in code.

Localisation fails late and in public because the defects are invisible in the source language. A string typed straight into a UI script works perfectly in English and is simply never offered to a translator. A button sized to its English label clips the German one. A sentence built from three fragments cannot be reordered by a language whose verb comes last. A plural written as "if count is 1" is wrong for every language whose rules differ. Each of these is cheap to prevent in the first month and expensive to find in the last, because by then the strings are scattered through scripts, scenes and assets and every fix touches content that has already been signed off. The order below puts the structural decisions first, while changing them is still cheap, and the human review last, because it is the only step that catches what no tool can.

## Scope

Use for: deciding which languages ship and at what depth; building the string table and its conventions; pseudo-localisation; plural, gender and ordinal handling; number, date and currency formatting; fonts and fallback per script; right-to-left layout; localised voice and subtitles; the linguistic QA pass; and the localisation-specific parts of regional release.

Do not use for: the age rating route, platform terminology tests, store submission and rejection recovery, which are `game-certification` — this skill supplies the translated strings those checks read, and that skill owns the checklist. Writing or improving the English wording itself, its tone and its error messages is `content-design`; a string that reads badly in the source language will be translated badly in every other. Patch notes, roadmaps and live-service communications are `game-live-ops`, though the pipeline that gets them translated starts here. Build size, texture compression and audio import settings are `game-assets`, including the size cost of a localised texture or voice bank. A contrast or colour-blindness audit is `accessibility-audit`.

## Scale and game type

Scale here means what the work requires rather than a headcount or a budget: indie/A is one small team wearing every hat; AA adds a localisation vendor and a publisher's language list; AAA adds a dedicated localisation team, several vendors and a simultaneous multi-language launch.

| | Indie/A | AA | AAA |
| --- | --- | --- | --- |
| Translation (steps 1, 2) | A few languages, often one freelance translator per language, working from a spreadsheet export | A vendor per language group with a shared glossary and translation memory | In-house language leads directing several vendors, with style guides per language |
| In-context review (step 8) | The team plays each language itself, or asks a native-speaking friend | The vendor's testers play a build per language | Dedicated linguistic QA per language against a bug taxonomy, on every milestone |
| Voice (step 6) | Subtitles over the original voice | Localised voice for the largest markets, subtitles elsewhere | Localised voice for most shipped languages, recorded to picture |

Narrative-heavy games spend their risk in steps 2 and 4: variables, speaker gender and branching text. Live-service games add a continuous delta in step 8, because strings change every season. UI-dense games such as strategy and role-playing games spend theirs in step 3, where limited space meets longer languages. Mobile games add the store listing in step 9.

## Workflow

### 1. Decide the language list and what supported means for each

A language is not one decision. For each, record which of these ships: interface text, subtitles, localised voice, localised textures and store listing. A language with interface text only is a different cost and a different quality promise from one with full voice, and writing that down stops "we support Korean" from meaning three different things to three people.

Then list what each script demands before any translation exists: whether the language needs glyphs the base font lacks, whether it is written right to left, whether it separates words with spaces, and whether it has more than two plural forms. Those four answers decide the plural work in step 4 and the font and layout work in step 5, and they are far cheaper to learn from the language list than from a bug report. The platform or store may also require particular languages for some strings; that requirement comes from the platform, through `game-certification`, not from this skill.

### 2. Externalise every player-facing string into keyed tables from day one

Every string a player can read leaves the code and enters a table, whether or not a translation is planned. Retrofitting this is the single largest avoidable cost in the discipline, because the work is not translation, it is finding the strings.

- **Key by stable identifier, not by English text.** Godot's documentation weighs both approaches and concludes that games generally give each string a unique ID because it lets the text be revised while it is being translated, and calls the English-as-key approach a nightmare when many languages are worked at once (<https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_translations.html>).
- **Give every entry the fields a translator needs:** the key, the source text, a note on where it appears and who is speaking, the maximum length, the placeholders and what each one holds, and a screenshot reference. A string with no note is translated from its words alone, and the same English word can need different translations; engines provide a context field for this (Godot's `tr("Close", "Actions")` against `tr("Close", "Distance")`).
- **Include what is not in a script:** text baked into textures, subtitles, achievement names and descriptions, error messages, tutorial prompts, save-slot labels, store listing text and the strings the platform requires.
- **Never concatenate.** A sentence is one entry with named placeholders, so a translator can move or reorder them. Godot's documentation recommends named placeholders over positional ones for exactly this reason. Anything assembled from fragments in code fails in step 4.
- **Block a literal at review.** A repository check for string literals in UI code, or a pseudo-localised build that is part of CI, turns hard-coded text from a late discovery into a failed build.

`references/string-tables.md` has the entry fields in full, key naming rules, the placeholder rules, and the table-per-feature layout that keeps merge conflicts down. Read it at this step.

### 3. Pseudo-localise early and keep it on

Pseudo-localisation transforms the source strings into a readable but altered form so that localisation defects appear before any translation is paid for. Turn it on in the first build with a real UI, and keep a toggle in the development menu.

It finds three things: strings that never pass through the table, which stay unaltered; UI that cannot hold longer text; and glyphs the font lacks. Godot's own documentation gives the cases: it replaces characters with accented ones, pads the string by an expansion ratio, wraps it in brackets and can fake right-to-left text, and it lists a ratio of 0.3 as sufficient for most practical cases (<https://docs.godotengine.org/en/stable/tutorials/i18n/pseudolocalization.html>). Treat 30 per cent as a starting assumption, not a measurement. Replace it with real lengths as soon as the first translation arrives. Keep each entry's length limit derived from what its control can render, measured in pixels on the real font: a translation longer than the limit is a defect, so resize the control or revise the wording, and raise the limit only to the new rendered capacity. A limit reset to the longest translation seen would let the overflowing string pass its own check.

The same page says what it does not do: because the text stays readable, it does not test whether a font covers Chinese, Japanese, Korean or a right-to-left script. Step 5 does that with real strings.

`references/string-tables.md` covers the transformations to implement when the engine has none, and how to run the pass.

### 4. Handle plurals, gender and formatting in the message, not in code

Write each message as one unit and let the message format choose the words. ICU MessageFormat does this with `plural` and `select` arguments, keeping the choices together so that one translator sees the whole sentence (<https://unicode-org.github.io/icu/userguide/format_parse/messages/>). Use the engine's equivalent where ICU is not available, and check that it covers more than singular and plural.

- **Plurals follow the language, not the number one.** Unicode CLDR defines the categories `zero`, `one`, `two`, `few`, `many` and `other`; `other` is mandatory and a language has any combination of the rest (<https://unicode.org/reports/tr35/tr35-numbers.html#Language_Plural_Rules>). Chinese and Japanese have only `other`, English has `one` and `other`, and Arabic uses all six, so the source language's two forms cannot carry the target's.
- **Put `select` outside and `plural` inside, and write full sentences in each branch.** ICU recommends exactly this, because a fragment inside a branch leaves the translator unable to see how it joins the rest.
- **Format numbers, dates and currency through locale data**, not by hand. Pass the formatted value into the message as a separate argument, which ICU lists as the recommended way to control formatting.
- **Carry gender as data.** If a character, a player or an item changes the words around it, the message needs a `select` on that attribute, which means the game must know it. Decide that in the data model, not in a translation spreadsheet.

`references/grammar-and-formatting.md` has the CLDR category table for common languages with its source and date, the apostrophe and quoting traps, ordinals, and the number and date rules. Read it at this step.

### 5. Plan fonts, scripts and layout direction per language

Fonts fail in a way that looks like missing text: boxes, or blanks, where characters should be. Check coverage against the actual translated strings rather than against a language name.

- **Give every script a font that covers it and a fallback chain behind that.** Godot supports defining fallbacks for exactly this case, a Latin-only font backed by another for a different script, and uses system fonts as fallbacks, which lets CJK and emoji display without a custom font, with documented restrictions (<https://docs.godotengine.org/en/stable/tutorials/ui/gui_using_fonts.html>). The fallback system also works regardless of the current language, which matters for chat where the sender's language may differ from the player's.
- **Check text that does not go through the table:** player names, chat and user-generated content, which can contain any script.
- **Do not assume spaces.** Some languages are written without spaces, so line breaking needs dictionary or rule data. Godot ships that data but leaves it out of exported projects until it is enabled.
- **Right-to-left is a layout, not a text alignment.** Mirror the interface, keep directional icons correct and treat numbers and Latin words inside right-to-left text as the exception the Unicode Bidirectional Algorithm handles. Godot mirrors anchors, container order and alignment automatically, leaves the coordinate system and non-UI nodes alone, and documents which icons need reversing.
- **Test with the real language.** A fake right-to-left pass in step 3 finds layout faults, but only an Arabic or Hebrew build, read by someone who reads it, finds the shaping and ordering ones.

`references/scripts-fonts-and-rtl.md` has the per-script checklist, the glyph-coverage test and the bidirectional traps. Read it when a language with a new script or direction is added.

### 6. Treat voice and subtitles as separate deliverables

Localised voice and subtitles are different strings with different constraints, and both are tied to timing. A translation that runs longer than the English line does not fit the animation, the cut-scene or the dialogue window that the English line was timed to.

- **Give recording a script with context:** who speaks, to whom, the emotion, the preceding line, and a time budget from the English take. Context-free voice scripts are the voice equivalent of a string with no note.
- **Keep the subtitle as its own entry** linked to the clip by key, with its own timing stored beside the localised audio, not computed from the English one.
- **Set a reading-time rule per language** from your accessibility targets and the platform's guidance, then check it per clip, since the same on-screen time does not read the same in every language.
- **Plan the fallback.** Decide what plays when a clip is missing for a language: the original voice with subtitles is a different promise from silence or a visible key.

`references/voice-and-subtitles.md` has the recording script fields, the timing method and the review checks. Read it before any voice session is booked.

### 7. Handle regions as well as languages

A language is not a market. Spelling, units and currency differ inside one language, and which content, ratings and legal text apply depends on the territory rather than the language. Godot's documentation illustrates it with English in the United States and Great Britain, and notes that content variations per region multiply the translation work.

Hand the rating route, the rating artwork, the required languages and the platform's mandatory terminology to `game-certification`, and keep on this side the strings those checks read: rating descriptors, legal and privacy text, platform names and the store listing, each as a table entry with an owner who is not the translator. `references/regions-and-store-text.md` sets out the split and what to ask legal or the publisher about content that differs by territory.

### 8. Run a linguistic QA pass in context, with screenshots

A translator sees a spreadsheet, not the game. Only a native reader playing the build sees a string on the screen it was written for, so schedule a pass in which a reader per language plays each feature and reports defects against a fixed taxonomy.

- **Build for review:** a build with every language selectable, a way to jump to any screen, and a way to show the key beside each string.
- **Capture the screenshot with every defect,** with the key, the language and the build number, because the fix needs the context the reviewer had.
- **Classify each defect** by type and severity so that fixes are triaged and so that a systematic cause, such as a missing font, is visible as a cluster. The taxonomy is in the reference file below.
- **Re-run on every string change.** A new feature and a changed English line both reopen the translation, so keep a list of changed keys and recheck exactly those; for a live game this is the delta in each season.

`references/linguistic-qa.md` has the taxonomy with severity rules, the review build checklist, the screenshot capture format and the sign-off criteria. Read it when the first translation arrives.

### 9. Ship the language list you tested

Before release, confirm that each shipped language has passed the pass in step 8 at the depth recorded in step 1, that the store listing and its screenshots exist in each listed language, and that anything not reviewed is either withheld or labelled as such. A language shipped without review is a promise the game cannot keep.

## Anti-patterns

**Retrofitting externalisation.** The cost is not translation, it is finding every string in scripts, scenes and assets after the game is built.

**Using English text as the key.** Fixing a typo then changes every language's key, and the same English word cannot map to two meanings.

**Building sentences from fragments.** It fails in every language whose word order differs, and no translator can fix it from the table alone.

**Writing plurals as a two-way branch on one.** It encodes the source language's grammar and is wrong for any language with a different rule.

**Treating pseudo-localisation as proof of CJK or right-to-left support.** It keeps text readable, so it cannot test font coverage or shaping for those scripts.

**Sizing the UI to the English text and checking later.** The longest translation decides the size of the control, and later is when the art is locked.

**Translating from a spreadsheet alone.** Without context and a screenshot the same word is translated by guess, and the error ships because nobody reads the result in the game.

**Letting translators edit format patterns.** A date pattern or number format changed in translation breaks the formatter; use locale data and skeletons instead.

**Calling a language supported without saying how far.** Interface text, subtitles and voice are different deliverables, and the player assumes the widest.

**Reviewing once.** The English text keeps changing after the first review, and each changed key is a new chance for a broken line.

## References

- `references/string-tables.md` — read at step 2: the entry fields, key and placeholder rules, table layout, and the pseudo-localisation transforms and how to run the pass at step 3.
- `references/grammar-and-formatting.md` — read at step 4: CLDR plural categories for common languages with their source, ICU quoting traps, ordinals, gender data, and number, date and currency formatting.
- `references/scripts-fonts-and-rtl.md` — read at step 5 when a new script or a right-to-left language is added: coverage tests, fallback chains, line breaking, mirroring and bidirectional traps.
- `references/voice-and-subtitles.md` — read at step 6 before a recording session is booked: recording script fields, timing method, subtitle rules and the missing-clip fallback.
- `references/linguistic-qa.md` — read at step 8 when the first translation arrives: the review build, screenshot format, bug taxonomy with severities and the sign-off criteria.
- `references/regions-and-store-text.md` — read at steps 7 and 9: the split between this skill and `game-certification`, store listing localisation, and the questions to put to legal or the publisher.
