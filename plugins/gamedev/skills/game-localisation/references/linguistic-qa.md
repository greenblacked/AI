# Linguistic QA

Read this at step 8 when the first translation arrives and again before each milestone. Linguistic QA is a native reader playing the game in the target language and reporting what is wrong with the text on the screen where the player sees it. It is separate from functional QA, which asks whether the game works, and from the translator's own review, which saw a spreadsheet.

No external standard defines the taxonomy below. It is this repository's working scheme; adapt the categories to your vendor's if they already have one, and keep the principle that every defect has a type, a severity and a screenshot.

## Contents

- [The review build](#the-review-build)
- [Who reviews](#who-reviews)
- [Capturing a defect](#capturing-a-defect)
- [The taxonomy](#the-taxonomy)
- [Severity](#severity)
- [Triage and the loop back](#triage-and-the-loop-back)
- [Sign-off](#sign-off)

## The review build

A reviewer cannot reach everything by playing from the start. Give them:

- Every shipped language selectable at runtime, switchable without restarting where the engine allows. Godot lets you run with a given locale from the command line (`godot --language fr`) and set a test locale in the project settings, which should be cleared before the setting is committed (<https://docs.godotengine.org/en/stable/tutorials/i18n/internationalizing_games.html>).
- A way to reach any screen, state and dialogue without replaying the game: a debug menu, saves at known points, a list of triggers.
- A toggle that shows the string key beside or instead of the text, so the defect report names the exact entry.
- A toggle for the pseudo-localised build from step 3, so a reviewer can tell an untranslated literal from a translated one.
- A screenshot key that writes the language, the build number, the key under the cursor and the time into the file name or an overlay.
- A list of changed keys since the last review, so a delta pass can focus.

## Who reviews

A native reader of the target language, ideally one who plays games of the same type, because the register of a shooter's chat differs from that of a story game. The translator who produced the text is a poor reviewer of it, so use a second person. Give the reviewer the glossary, the style guide, the character sheet and the tone notes, and tell them what they are not judging: art, balance and functional bugs are reported to the people who own them, not to the translators.

## Capturing a defect

One defect per report, with:

1. The language and the build.
2. The key, from the key toggle.
3. A screenshot showing the whole screen, not a crop, so the context is visible.
4. The category from the taxonomy and a severity.
5. What is wrong, and a suggested correction where the reviewer has one.
6. How to reach the screen, if it is not obvious.

For voice, add the clip name and the time in the clip. For a layout fault, add the display mode and resolution, since a clip that fits at one size may not at another.

## The taxonomy

| Category | What it is | Typical cause | Fixed by |
| --- | --- | --- | --- |
| Missing translation | Source text, a key, or a fallback language is shown | Key absent in that language, or a hard-coded literal | Translator, or an engineer for a literal |
| Truncation or overflow | Text is cut off, spills out of its box, or wraps onto something | Length limit too tight, or a control that cannot grow | Layout first, translator second |
| Overlap | Text collides with other text or an icon | Layout fixed to the source width | Engineer or UI artist |
| Wrong meaning | Correct language, wrong sense | Ambiguous source, no context, a missing note | Translator, with a better note |
| Placeholder fault | A raw placeholder shows, the wrong value appears, or the order reads wrongly | A placeholder altered or dropped in translation | Translator or engineer |
| Plural or agreement fault | Wrong number form, wrong gender, a missing case | Message not structured for the language | Engineer and translator together; see `grammar-and-formatting.md` |
| Inconsistent term | The same thing called two names | Glossary not followed or not provided | Translator |
| Register or tone | Too formal, too casual, out of character | Style guide missing or unclear | Translator |
| Font or glyph fault | Boxes, wrong glyph, wrong shaping | Coverage or fallback gap | Engineer; see `scripts-fonts-and-rtl.md` |
| Direction fault | Layout, order or icons wrong in a right-to-left language | Mirroring or bidirectional handling | Engineer |
| Format fault | A date, number, unit or currency shown in the wrong form | Formatting by hand | Engineer |
| Audio or subtitle fault | Subtitle does not match the voice, timing too short or too long, wrong clip | Table change not carried to the recording | Audio lead and translator |
| Untranslated asset | Text inside an image or a video | Localised texture missing | Artist |
| Cultural or regional | Content or an image that is wrong for the territory | Content not reviewed for the region | Publisher or legal; see `regions-and-store-text.md` |
| Platform term | A platform's name for a feature, button or setting is wrong or inconsistent | Terminology not taken from the platform's list | Translator; see `game-certification` |

## Severity

Define these before the pass so reviewers agree, and tie each to a consequence, not to a feeling.

| Severity | Meaning | Example |
| --- | --- | --- |
| Blocker | Blocks release, a platform check, or the player's progress | A required legal or system string is missing or wrong, a tutorial prompt cannot be read, a quest instruction is incorrect |
| Major | Misleads or confuses the player, or breaks the experience in an obvious way | A wrong item description, an untranslated menu, clipped text on a core screen |
| Minor | Noticeable but understandable | An inconsistent term, a clumsy phrase |
| Cosmetic | Polish | A spacing or punctuation inconsistency |

A cluster of the same category across a language or a screen is a cause, not a number of separate defects; fix the cause once.

## Triage and the loop back

1. A coordinator reads the reports daily during the pass, merges duplicates and routes each by the "fixed by" column.
2. Translators receive the key, the note and the screenshot, not a vague description.
3. Layout and code defects come back as engineering tasks against the control or the message, since they affect every language.
4. Each fix updates the table's status so the changed keys are known; the next build is then rechecked for exactly those keys.
5. Record the root cause of every Blocker and Major in the style guide, the glossary or the table's notes, so the next language starts better than the last.

## Sign-off

A language is ready to ship at the depth recorded in step 1 when:

- Every screen has been visited in the target language by a native reader, and the final build has been checked, not only an earlier one.
- No open Blocker or Major remains, and open Minor and Cosmetic items are listed and accepted by someone with the authority to accept them.
- Every key changed since the review has been rechecked.
- The fonts, direction handling and formatting have been confirmed on each target platform's hardware or its closest equivalent, not only in the editor.
- Strings read by platform and store checks have been reviewed against the platform's own terminology; see `regions-and-store-text.md`.

A language that does not meet this is either withheld or shipped with a visible label that it is incomplete, decided in the open.
