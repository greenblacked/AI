# Scripts, fonts and right-to-left layout

Read this at step 5 when a language with a new script, or a right-to-left direction, is added to the list. It covers how to test that a font draws the translated text, how to build a fallback chain, how text breaks into lines, and what changes when the layout direction flips.

## Contents

- [Per-script questions](#per-script-questions)
- [Font coverage](#font-coverage)
- [Fallback chains](#fallback-chains)
- [Line breaking](#line-breaking)
- [Right-to-left layout](#right-to-left-layout)
- [Bidirectional text](#bidirectional-text)
- [Directional icons and images](#directional-icons-and-images)
- [Checklist per new language](#checklist-per-new-language)

## Per-script questions

Ask these of each language before any translation arrives, and write the answers next to the language list:

1. Which script does it use, and does the current font cover it?
2. Does it read right to left, or mix directions?
3. Does it separate words with spaces, or need dictionary or rule data to break lines?
4. Does it join or reshape characters depending on their neighbours, so that the glyph drawn depends on the surrounding text? Godot's documentation notes this for Arabic and Hebrew contexts: in some languages the shape of a glyph changes with its surroundings (<https://docs.godotengine.org/en/stable/tutorials/i18n/internationalizing_games.html>).
5. Does it have more than two plural forms? See `grammar-and-formatting.md`.

## Font coverage

A font either has a glyph for a character or the engine draws a placeholder, commonly called tofu. Godot's documentation describes the placeholder boxes for missing emoji, and the same behaviour applies to any missing character (<https://docs.godotengine.org/en/stable/tutorials/ui/gui_using_fonts.html>). A language name tells you little about coverage; the characters actually in your strings tell you everything.

- **Test against the real strings.** Extract every distinct character from each language's translation table and check each against the font's character map. Do it as a script in CI so that a new translation cannot add an uncovered character unnoticed. Pseudo-localisation cannot do this for CJK or right-to-left scripts, because it keeps the text in readable Latin; Godot's documentation says so directly.
- **Include text that is not in the table:** player names, chat, user-generated content and platform account names, which arrive in any script regardless of the interface language.
- **Choose a family built for coverage** when one font cannot cover your list. Godot's documentation names Noto Fonts as a resource for multilingual fonts and tells you to download the correct variation for less common languages (<https://docs.godotengine.org/en/stable/tutorials/i18n/internationalizing_games.html>). Check each font's licence for embedding and redistribution in a game before shipping it.
- **Pre-render deliberately.** If the engine pre-renders glyphs for speed, the set has to come from the translations. Godot can source it from the project's translations, and notes that the list of pre-rendered glyphs is not updated automatically when translations change, so repeat the step after each handoff or the new characters are drawn late or not at all.
- **Account for size.** A font that covers CJK is much larger than a Latin one, and a localised font bundle is a download-size decision; hand the number to `game-assets`.

## Fallback chains

A fallback chain lists fonts to try, in order, when the first lacks a glyph. Two uses are standard, and Godot's documentation names both: a font with only a Latin character set backed by another font for a different script such as Cyrillic, and a text font backed by an emoji or icon font (<https://docs.godotengine.org/en/stable/tutorials/ui/gui_using_fonts.html>).

- Use a chain for text that can be in any language at once, such as chat. The chain works whatever the current language is, whereas a per-language font replacement does not apply to text in a different language. Godot's note on resource remapping says exactly this about fonts.
- Put a per-language font choice only where the design needs a different look per language, such as a display typeface that exists in Latin only, and keep the chain behind it.
- System fonts as fallbacks avoid bundling large fonts. Godot's documentation says the engine uses them automatically, which makes CJK and emoji display without a custom font, with two caveats it states: appearance differs by platform, and loading system fonts is not supported on all platforms. On a console or a locked-down platform, confirm what exists before relying on it.
- Icons inside text, such as controller button glyphs, belong in the chain as an icon font or as inline images; Godot notes that icon fonts use the private use area, which is why they combine safely with a text font.

## Line breaking

Languages written without spaces between words cannot be wrapped by looking for spaces. The engine needs dictionary or rule data. Godot includes it but does not put it in exported projects by default; the setting must be enabled and the data adds to the export (<https://docs.godotengine.org/en/stable/tutorials/i18n/internationalizing_games.html>). Whatever the engine, test a long paragraph in each such language in a build that was exported, not only in the editor, since a missing data file shows only there.

Do not insert manual line breaks into translatable text. A break placed for one width forces an odd ragged line in another, and the layout engine can wrap correctly given room.

## Right-to-left layout

Mirroring is the visible part of right-to-left support. Godot describes what it does automatically: it mirrors left and right anchors and margins, swaps left and right text alignment, mirrors the horizontal order of children in containers and of items in lists, and mirrors the internal order of controls such as dropdown buttons and checkboxes. It does not mirror the coordinate system, and non-UI nodes such as sprites are not affected (<https://docs.godotengine.org/en/stable/tutorials/i18n/internationalizing_games.html>).

From that, the checks that matter in any engine:

- **Use container-based and anchor-based layout,** not absolute positions on the left, because mirroring works on the structure. A screen built from absolute coordinates will not flip.
- **Decide for each element whether it should mirror.** A health bar that fills toward the opponent, a timeline, a minimap, a joystick or a chart can carry meaning in its direction, and mirroring it may be wrong. Make that a decision in the design, not an accident of the engine default.
- **Check non-UI content that carries text,** such as signs in the world and in-world menus, which an interface-level mirror will not touch.
- **Alignment is not direction.** Right-aligned English text is not right-to-left text. Test with real strings in the real language.
- **Keep an override.** Godot lets you override the text direction (`text_direction`), the language and the control layout direction (`layout_direction`) per control. Use it for elements such as a code or a name that must keep a fixed direction.

## Bidirectional text

Right-to-left text routinely contains left-to-right runs: numbers, Latin brand and product names, and player names. The Unicode Bidirectional Algorithm (UAX #9) orders these runs, and Godot's documentation notes that with a base direction of "auto" the direction depends on the first strong directional character according to that algorithm.

- Test every message that mixes a placeholder into right-to-left text with a Latin name and with a number, because the position of punctuation and the order of the runs is where mistakes appear.
- Structured text, such as file paths, URLs and email addresses, is not natural text, and the algorithm is incapable of handling the higher-level order in it. Godot gives a structured text override for this and an example with a directory path. Apply the same idea wherever a string has its own order: a code, a match identifier or a username with symbols.
- Digits may be shown in a different numbering system in some locales. Keep the choice consistent between the interface and the data you display; see `grammar-and-formatting.md`.

## Directional icons and images

Icons that point left or right and indicate movement or direction, such as back and forward buttons, may need to be reversed for Arabic and Hebrew; otherwise they can stay as they are (Godot's documentation says exactly this). The test is whether the arrow means "direction of reading" or something absolute. A play button or a checkmark usually does not mirror; decide each one rather than reversing the whole set.

Text inside a texture is not covered by any of this: a localised image is a separate asset per language. Godot's resource remapping serves alternative images and voices per locale; count each one in the size budget with `game-assets`.

## Checklist per new language

1. The font covers every character in the translation table, checked by script.
2. A fallback chain is in place for text that can arrive in any script.
3. Line breaking works in an exported build for a long paragraph.
4. For right-to-left: the layout mirrors, directional icons are reviewed, and mixed-direction strings are read by a native reader.
5. The language was reviewed in a build, not in a spreadsheet; see `linguistic-qa.md`.
