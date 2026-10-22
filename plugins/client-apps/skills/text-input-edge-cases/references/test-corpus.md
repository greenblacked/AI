# Text input test corpus

## Contents

- How to use it
- The strings
- Expected handling per field class
- Manual cases: composition and autofill

## How to use it

Keep the corpus as JavaScript escapes in a shared fixture file, not as pasted characters: an editor, a formatter or a copy through a chat tool can silently normalise or strip exactly the characters under test. Run it through the client's counter, handlers and cleaning functions as unit tests, and through the API as a round trip: post each string, read it back, and compare code point for code point with what the contract says should be stored.

Counts below were measured with `Intl.Segmenter` in a current engine. Units are UTF-16 code units (`.length`), code points (`[...s].length`), grapheme clusters, and UTF-8 bytes (`new TextEncoder().encode(s).length`).

## The strings

| Id | Escape | Units | Code points | Graphemes | UTF-8 bytes | What it breaks |
| --- | --- | --- | --- | --- | --- | --- |
| zwj-family | `\u{1F468}\u200D\u{1F469}\u200D\u{1F467}\u200D\u{1F466}` | 11 | 7 | 1 | 25 | `.length` limits, `maxlength`, slicing that splits the sequence |
| flag | `\u{1F1EC}\u{1F1E7}` | 4 | 2 | 1 | 8 | Truncation between the two regional indicators leaves two letters |
| skin-tone | `\u{1F44D}\u{1F3FD}` | 4 | 2 | 1 | 8 | Same, leaving a bare colour swatch |
| keycap | `1\uFE0F\u20E3` | 3 | 3 | 1 | 7 | Digit-only filters that see the `1` and accept it |
| nfd-e | `e\u0301` | 2 | 2 | 1 | 3 | Equality with `é` before normalisation |
| zoe-nfd | `Zoe\u0308` | 4 | 4 | 3 | 5 | Name lookups and uniqueness without NFC |
| stacked | `a\u0301\u0302\u0303` | 4 | 4 | 1 | 7 | Grapheme-only limits with no storage ceiling |
| hangul-nfd | `\u1112\u1161\u11AB` | 3 | 3 | 1 | 9 | Text from decomposed sources, such as macOS file names, failing to match |
| devanagari | `\u0928\u092E\u0938\u094D\u0924\u0947` | 6 | 6 | 3 | 18 | Client and server grapheme counts disagreeing: 3 on engines with Unicode 15.1 or later, 4 on older ones |
| cjk-ext-b | `\u{20BB7}` | 2 | 1 | 1 | 4 | MySQL `utf8` (`utf8mb3`) columns |
| math-bold | `\u{1D400}` | 2 | 1 | 1 | 4 | Identifiers that should fold to `A` under NFKC |
| fullwidth | `\uFF21\uFF22\uFF23` | 3 | 3 | 3 | 9 | Identifiers that should fold to `ABC` under NFKC |
| hebrew-mixed | `\u05E9\u05DC\u05D5\u05DD abc 123` | 12 | 12 | 12 | 16 | Display without `dir="auto"` or `<bdi>` |
| arabic | `\u0645\u0631\u062D\u0628\u0627` | 5 | 5 | 5 | 10 | Right-to-left layout and font fallback |
| rlo | `abc\u202Edef` | 7 | 7 | 7 | 9 | Identifiers and code-like fields: displays reversed |
| zwsp | `ab\u200Bc` | 4 | 4 | 4 | 6 | `trim()` does not remove it; two identifiers that look the same |
| nbsp-edges | `\u00A0name\u00A0` | 6 | 6 | 6 | 8 | `trim()` does remove it, giving 4; a regex trim of `[ ]` does not |
| nul-paste | `abc\u0000def` | 7 | 7 | 7 | 7 | Pasted control characters; some databases reject a NUL outright |
| crlf-tab | `line1\r\n\tline2` | 13 | 13 | 12 | 13 | Single-line fields accepting newlines; `\r\n` is one grapheme |
| lone-surrogate | `ab\uD83D` | 3 | 3 | 3 | 5 with `TextEncoder`, which silently writes U+FFFD; a strict encoder fails | `encodeURIComponent` throws `URIError`, and a lenient encoder replaces the character without telling you; reach it through the API, since typing cannot produce it |
| turkish-I | `\u0130stanbul` | 8 | 8 | 8 | 9 | Locale-sensitive case folding of keys |
| apostrophe-straight | `O'Brien` | 7 | 7 | 7 | 7 | Name patterns; quoting that should have been parameterised |
| apostrophe-curly | `O\u2019Brien` | 7 | 7 | 7 | 9 | Patterns that allow only the straight apostrophe; autocorrect produces this one |
| cyrillic-a | `p\u0430ypal` | 6 | 6 | 6 | 7 | Impersonation: NFKC leaves it unchanged, only a confusables check catches it |

Add a long case per field: the limit in graphemes made of `zwj-family`, which must be accepted by the counter and fit the column, and the same plus one, which must be refused with the counter's message rather than a database error.

## Expected handling per field class

| Id | Display text | Identifier | Code |
| --- | --- | --- | --- |
| Emoji cases | Accept; count as 1 each | Reject unless the contract allows emoji | Reject |
| nfd-e, zoe-nfd, hangul-nfd | Store as NFC | Fold, then compare | Reject |
| devanagari, cjk-ext-b, arabic, hebrew-mixed | Accept and store losslessly | Accept if the script is allowed | Reject |
| math-bold, fullwidth | Accept as typed | Fold to ASCII for the key, keep the original for display | Fold, then check digits |
| rlo | Strip or accept, by decision | Reject | Reject |
| zwsp | Accept | Strip or reject | Strip |
| nbsp-edges | Trim on save | Trim on save | Strip |
| nul-paste, crlf-tab | Strip controls; newlines only if multi-line | Reject | Strip |
| lone-surrogate | Reject at the API | Reject | Reject |
| apostrophes | Accept both | Per contract | Reject |
| cyrillic-a | Accept | Reject a mixed-script key if impersonation matters | Reject |

## Manual cases: composition and autofill

Run these on real devices; scripted key events do not compose and browsers do not autofill under automation. Record the platform, browser and date with the result.

- Japanese input on macOS and on iOS: type a word, press Enter to confirm the conversion. The form must not submit; a second Enter may.
- Korean input on Windows and on Android: type a syllable and press Enter or a button immediately. The last syllable must not be lost or duplicated.
- An accent with a dead key on macOS (Option+E, then E). The field must show one `é`, and a counter must not jump by two.
- Android keyboard with suggestions on: type in a field that filters characters. The filter must still work, since `keydown` reports `"Unidentified"` there.
- Browser autofill of name, email and phone, and an SMS one-time code on iOS and Android. The field must validate as filled without a keystroke.
- Paste from a word processor and from a PDF into a name field and a multi-line field. Smart quotes are kept; control characters, soft hyphens and trailing newlines are handled per contract.
