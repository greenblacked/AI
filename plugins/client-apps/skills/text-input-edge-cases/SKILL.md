---
name: text-input-edge-cases
description: "Harden text fields against what people type, paste and autofill: count graphemes with Intl.Segmenter rather than .length, ignore Enter during IME composition, normalise to NFC before comparing or storing, trim once when saving, never reject a name with a pattern, keep client and server limits in one unit, and test every field against a fixed corpus - ZWJ emoji, combining marks, right-to-left text, 4-byte characters, autofill. Use when \"emoji breaks the character limit\", \"Enter submits while Japanese users are still typing\", \"names with apostrophes are rejected\", \"two usernames look identical\" or text turns into question marks in the database. Not for form layout and error placement (form-design), the wording of hints and errors (content-design), WCAG conformance (accessibility-audit), or translating and formatting the product's UI per locale (locale-edge-sweep)."
allowed-tools: "Read, Grep, Glob, Edit"
---

# Text Input Edge Cases

Done means every text field has a written contract — the unit its limit is counted in, the normalisation applied, where trimming happens, what is rejected and why — the client and the server enforce the same contract, and an automated test runs the field and its storage round trip against a fixed corpus.

The usual failure is validation written and tested against ASCII: `value.length`, `/^[A-Za-z]+$/`, a `keydown` listener for Enter. Every test passes, and the first user named Zoë, the first person typing Japanese, and the first message with a family emoji all break it. Each fix below is small; the work is in finding every field and every layer that repeats the mistake.

## Scope

Use for fields that accept human text: names, usernames and handles, free-text messages and bios, search boxes, addresses, codes and phone numbers, and the APIs and columns behind them. Covers counting, composition, normalisation, trimming, paste and autofill, right-to-left display and lossless storage.

Leave elsewhere: field order, validation timing and error placement (`form-design`); the words in labels, hints and errors (`content-design`); WCAG conformance of the form (`accessibility-audit`); translating UI strings and formatting numbers, dates and plurals per locale, and mirroring the UI for right-to-left (`locale-edge-sweep`); iOS zooming into inputs with small text and other Safari-only layout bugs (`webkit-only-bug-triage`).

## Gates

1. The contract is written before the code. A field whose limit unit nobody can name will be counted three different ways by the counter, the API and the column.
2. The server is the authority and applies the same contract. A client-only rule is bypassed by every API caller, import and older app version.
3. The corpus test passes for every field, end to end through storage and back. A string that survives the input but not the column is still a bug.

## Workflow

### 1. Inventory fields and write their contracts

Find every input, `contenteditable`, API field and column that holds human text. Classify each, because the classes need different rules:

| Class | Examples | Limit unit | Normalisation | Rejects |
| --- | --- | --- | --- | --- |
| Display text | Name, bio, message, address | Graphemes for the user; code points or bytes as a storage ceiling | NFC | Control characters only |
| Identifier | Username, handle, slug, tag | Code points | NFKC plus case folding, or a PRECIS profile | Whitespace, controls, bidi controls, confusable mixes if impersonation matters |
| Code | One-time code, postcode, phone | Digits after cleaning | Strip spaces and separators | What cannot be cleaned |
| Search | Search box, filter | Generous ceiling | NFC; accent and case handled by collation | Nothing |

Write the table for the feature at hand, with the storage column type beside each row.

### 2. Count what the user sees

The family emoji `"\u{1F468}\u200D\u{1F469}\u200D\u{1F467}\u200D\u{1F466}"` has a `.length` of 11, because `.length` counts UTF-16 code units; spreading it into an array gives 7 code points. The user sees one character. Count user-facing limits in grapheme clusters with `Intl.Segmenter` and the `grapheme` granularity, and show the counter in the same unit the limit is enforced in.

The `maxlength` attribute counts UTF-16 code units, so an emoji uses two and the visible count disagrees with the counter. Do not use it as the user-facing limit where emoji or combining marks are likely; enforce the grapheme limit in script and keep a separate storage ceiling in code points or UTF-8 bytes on the server, with headroom, so a single grapheme stacked with hundreds of combining marks cannot fill the column. Grapheme rules change between Unicode versions — Indic conjuncts changed in Unicode 15.1 — so a browser and a server may disagree by a few on the same string; give the server's limit a margin rather than rejecting on the exact boundary.

Truncate by graphemes, never with `.slice(0, n)`: slicing can split a surrogate pair into a lone surrogate, which `encodeURIComponent` throws on and a database may reject or replace, or split an emoji sequence into a different emoji. `String.prototype.isWellFormed()` detects the lone surrogate.

### 3. Respect input-method composition

Japanese, Chinese and Korean input, dead keys for accents, and many Android keyboards compose text before committing it. The Enter that confirms a candidate is not a submit. In the `keydown` handler, return early when `event.isComposing` is true or `event.keyCode` is `229`; the second check covers WebKit, where the `keydown` for the Enter that ends composition arrives after `compositionend` with `isComposing` already false.

During composition, do not reformat, uppercase, mask, truncate or reset a controlled value; wait for `compositionend`. Filter characters in `beforeinput` or `input` rather than `keydown`, because Android keyboards commonly report `keydown` with `key` set to `"Unidentified"` and `keyCode` 229 for ordinary letters. Test with a real input method on each platform; synthetic key events do not compose.

### 4. Normalise before comparing or storing

`"é"` can arrive as one code point (U+00E9) or as `e` plus a combining acute (U+0301). They look identical and compare unequal. Apply `normalize("NFC")` to display text at the server boundary before storing, comparing or hashing it.

Identifiers need more. Two usernames that render the same must map to the same key: apply NFKC, which folds compatibility forms such as fullwidth `ＡＢＣ` and mathematical bold letters to plain ones, then case-fold — or use a library implementing the PRECIS username profiles of RFC 8265. If impersonation matters, add a confusables check from Unicode Technical Standard 39 so `p\u0430ypal`, with a Cyrillic `а` in second place, is caught. Store the user's original form for display and the folded form for uniqueness, with the unique index on the folded form. Use the locale-independent `toLowerCase()` for keys; `toLocaleLowerCase("tr")` turns `I` into dotless `ı`, which is right for Turkish display and wrong for an identifier.

### 5. Trim once, at the boundary

Trim when the value is saved, not on every keystroke: a controlled input that trims on change deletes the space the user just typed between two words. `trim()` removes Unicode whitespace including the no-break space and the byte-order mark, but not the zero-width space U+200B or other format characters; strip those explicitly for identifiers and codes. Collapse internal runs of whitespace only for identifiers. Do not trim or alter passwords.

### 6. Stop rejecting real names and text

Do not validate a name with a pattern. Real names contain apostrophes in two forms (`O'Brien`, `O’Brien`), hyphens, spaces, particles, one letter, one word, many words, combining marks and non-Latin scripts, and every pattern written so far has excluded someone. Prefer one full-name field to a required first and last name. Check only that it is non-empty after trimming, within the storage ceiling, and free of control characters.

Rejecting `'` or `<` to prevent injection is the wrong layer: parameterise queries and encode on output, and accept the text. For email, note that the browser's `type="email"` check rejects non-ASCII local parts, so decide deliberately whether internationalised addresses are supported.

### 7. Clean pasted and autofilled input

Strip C0 and C1 control characters on save, keeping tab and newline only in multi-line fields. In identifiers, codes and anything rendered as code, reject the bidirectional embedding, override and isolate characters U+202A to U+202E and U+2066 to U+2069; they make text display in a different order from how it is stored. For codes and phone numbers, accept pasted spaces and separators and clean them rather than rejecting the paste.

Autofill sets the value and fires `input` and `change`, not `keydown` or `keyup`, so validation hung on key events shows an autofilled field as empty or invalid. Listen on `input`. Set the right `autocomplete` token on every field (`name`, `given-name`, `family-name`, `email`, `tel`, `username`, `new-password`, `one-time-code`), and on identifiers and codes set `autocapitalize="none"` and `spellcheck="false"` so the keyboard does not edit them.

### 8. Display it back without reordering

Mirroring the surrounding UI for right-to-left locales is `locale-edge-sweep`; this step is only about text users typed. Set `dir="auto"` on text inputs and on elements that display user text, so a Hebrew or Arabic name is laid out right to left. Wrap user text embedded in a sentence in `<bdi>`, so `שלום posted 3 comments` does not pull the surrounding punctuation and numbers into the wrong order. Check the corpus renders without empty boxes in the product's fonts.

### 9. Store without loss

Check the storage path for the corpus's 4-byte characters. MySQL's `utf8` is the three-byte `utf8mb3` and cannot hold most emoji or CJK Extension B; the column, table and connection all need `utf8mb4`, or the value is rejected or mangled into question marks depending on the SQL mode. PostgreSQL's `varchar(n)` counts characters (code points). SQL Server's `nvarchar(n)` counts UTF-16 code units, so an emoji uses two. Size each column so the client's grapheme limit fits at a realistic code points per grapheme, and enforce the server's ceiling before the database does.

### 10. Run the corpus

Run every field through `references/test-corpus.md`: as client unit tests on the counter, normaliser and handlers, and as an API test that posts each string and reads it back byte for byte. The skill does not pre-approve `node` or `npx`, which run arbitrary code; the user approves each run. Composition and autofill need a short manual pass on real devices, recorded with the date and platforms. `references/field-handlers.md` has the code for the grapheme counter, the composition-safe Enter handler, the save-time cleaning pipeline and the identifier key; read it when writing or reviewing those pieces.

## Output format

- The field contract table, with the storage column for each field.
- What changed per field and per layer: counter, handlers, server validation, column type.
- The corpus results: automated pass or fail per field, and the manual composition and autofill pass with platforms and date.
- Known disagreements left in place, such as a grapheme count that differs between the browser and the server on Indic text, and the margin chosen to absorb it.

## Reference files

- `references/test-corpus.md` — read when writing the tests: every corpus string as a JavaScript escape with its code-unit, code-point, grapheme and byte counts, what each one breaks, and the manual cases for composition and autofill.
- `references/field-handlers.md` — read when writing or reviewing the code: grapheme counting and truncation, the composition-safe Enter handler, save-time cleaning, and building identifier keys.
