---
name: locale-edge-sweep
description: "Find internationalisation defects by sweeping every screen through a fixed hostile locale set, not whichever language is next on the roadmap. Externalise strings as ICU plural and select messages, then sweep: a pseudo-locale with about 40 percent expansion, Turkish dotless i in case mapping, right-to-left with logical properties, German compound words, Thai and Japanese without spaces, collation for sort and search, name and address formats, and numbers, currency and dates via the platform formatter; then gate it in CI. Use when someone says \"we need to support Arabic\", \"the layout breaks in German\", \"plurals are wrong in Polish\" or \"Swedish names sort wrong\". Not for English UI wording (content-design), breakpoints and screen sizes (responsive-design), a game's localisation pipeline (game-localisation), or dates on the wrong day or hour (datetime-bug-hunt)."
allowed-tools: Read, Grep, Glob, Edit, Write
---

# Locale Edge Sweep

Done means every screen has been seen in each locale of the hostile set below, each
defect is filed against the mechanism that caused it rather than the language it showed
up in, and a CI job fails the build when the same class comes back.

Teams find i18n bugs one language at a time, in the order the business adds markets, so
each launch rediscovers the same classes: a German label that clips, an Arabic screen
whose back arrow points the wrong way, a Turkish user who cannot log in because
`"title".toUpperCase()` produced `TİTLE`. Each locale in the set exists because it breaks
a different mechanism. Sweeping all of them once, before translation starts, is cheaper
than learning them through support tickets in the order markets happen to open.

## Scope

Use for: preparing an app or site for its first non-English locale or a new script;
"the layout breaks in German"; right-to-left support; plural, gender, sort, search,
number, currency, name and address defects that depend on locale; adding an i18n gate to
CI.

Do not use for: the English wording of labels and errors (`content-design`); layout
across screen sizes (`responsive-design`), though expansion and RTL are found here; a
game's string tables, fonts per script, voice and linguistic QA (`game-localisation`); a
date on the wrong day or hour, which is a time-zone bug rather than a locale one
(`datetime-bug-hunt`); WCAG conformance (`accessibility-audit`).

## Hard gates

1. No sweep before user-facing strings are externalised; a pseudo-locale cannot reach a
   hard-coded string, which is exactly what it is meant to expose.
2. No plural built by concatenation or by `count == 1`; every count goes through the
   platform's plural rules.
3. No number, currency, date or list formatted by hand; every one goes through the
   platform formatter with an explicit locale.
4. Every defect names its mechanism (expansion, case mapping, direction, segmentation,
   collation, format), so the fix lands once rather than per language.

## Workflow

### 1. Externalise strings as messages, not fragments

Find hard-coded strings and concatenation first: Android Lint's `HardcodedText` and
`SetTextI18n` checks, the `i18next/no-literal-string` ESLint rule, or Xcode's
localizability analyser (`CLANG_ANALYZER_LOCALIZABILITY_NONLOCALIZED`). Then rewrite each
sentence as one message with its variables inside it, in ICU MessageFormat or the
platform equivalent:

```text
{count, plural, =0 {No files} one {# file} other {# files}}
{gender, select, female {She replied} male {He replied} other {They replied}}
```

English has two plural categories; Polish and Russian have four, Arabic has six, Japanese
has one. A message that branches on `count == 1` is wrong for most of the world. Give
each key a translator note and its maximum length, and never reuse one key for two
contexts — "Open" as a verb and as a status translate differently.

*Gate:* the lint step reports no hard-coded user-facing string, and no message is
assembled from translated fragments.

### 2. Run the pseudo-locale on every screen

A pseudo-locale accents every character, pads each string by about 40 percent and wraps
it in brackets, so in one pass you see which text is not externalised (no accents),
which clips or wraps badly (padding), and which strings are glued together (brackets in
the middle of a sentence). Short strings grow proportionally more than long ones in real
translation, so a 40 percent pad is a floor for buttons and tabs, not a ceiling.

Android ships `en-XA` (accented, expanded) and `ar-XB` (mirrored, right to left) once
`pseudoLocalesEnabled true` is set on the debug build type. Xcode's scheme options offer
double-length, accented, bounded and right-to-left pseudolanguages. On the web, the
FormatJS CLI's `formatjs compile --pseudo-locale` generates one from the message
catalogue.

*Gate:* every screen captured in the pseudo-locale, with each clipped, overlapping or
unaccented string filed.

### 3. Sweep the hostile set, one mechanism per locale

Switch the app to each locale and walk the same screens. Each locale targets a mechanism:

| Locale | Mechanism it breaks | Look for |
| --- | --- | --- |
| `de-DE` | Long compound words, `ß` uppercasing to `SS` | Words that overflow instead of wrapping; buttons that grow off screen |
| `tr-TR` | Case mapping: `i`↔`İ`, `ı`↔`I` | Identifiers, keys, enum names or emails uppercased or lowercased with the default locale |
| `ar`, `he-IL` | Right-to-left layout and mixed-direction text | Physical left/right in layout; arrows that do not mirror; a Latin username or phone number scrambling the sentence around it |
| `ja-JP`, `th-TH` | No spaces between words; input methods | Truncation or word counts that split on spaces; Enter submitting a form mid-composition; clipped tall glyphs in Thai |
| `pl-PL`, `ar` | Plural categories beyond one and other | Polish needs `2 pliki` but `5 plików`, so a one-or-other message is wrong for one of them; Arabic has a dual |
| `sv-SE`, `de-DE` | Collation | `å`, `ä`, `ö` sort after `z` in Swedish but beside `a` in German |
| `fr-FR`, `en-IN`, `de-CH` | Number grouping and separators | Narrow no-break space as a group separator in French; `12,34,567` in Indian English; a parser that only accepts `.` |
| `ja-JP`, `hu-HU` | Family name first | "Hello, Tanaka Taro" built as first-plus-last |

`references/hostile-locale-set.md` has, per locale, how to switch to it on Android, iOS
and the web, the exact strings and values to try, and the expected result. Read it when
running the sweep.

### 4. Fix by mechanism

- **Expansion and compound words:** let text wrap; never fix a width to the English
  string. On the web, `hyphens: auto` only works when the element has a `lang`
  attribute, and `overflow-wrap: anywhere` is the backstop for a single long word.
- **Case mapping:** use a locale-invariant conversion for anything that is not prose —
  `toUpperCase(Locale.ROOT)` in Java, `uppercase()` in Kotlin, plain `toUpperCase()` in
  JavaScript — and the locale-aware one (`toLocaleUpperCase("tr")`) only for display
  text. Android Lint's `DefaultLocale` check flags the Java form.
- **Direction:** logical properties (`margin-inline-start`, `padding-inline-end`,
  `inset-inline-start`, `text-align: start`) on the web; `start`/`end` and
  `android:supportsRtl="true"` on Android, with Lint's `RtlHardcoded`; leading and
  trailing constraints on iOS. Mirror icons that show direction (back, forward, reply);
  leave clocks, checkmarks and media playback controls alone. Isolate user-supplied text
  inside a sentence with `<bdi>`, `dir="auto"` or the Unicode first-strong isolate.
- **Segmentation:** break, count and truncate with the platform's segmenter —
  `Intl.Segmenter`, ICU `BreakIterator` (`android.icu.text.BreakIterator`), or
  `enumerateSubstrings(in:options:)` with `.byWords` on Apple platforms — and truncate by
  grapheme cluster so an emoji or a combining mark is not cut in half. In a web form, do
  not act on Enter while `event.isComposing` is true.
- **Collation and search:** sort with `Intl.Collator` or `localeCompare` with an
  explicit locale, `java.text.Collator.getInstance(locale)`, or `localizedStandardCompare`;
  match search with a collator at base sensitivity so `é` finds `e`. Check the database
  collation too; a sort done in SQL ignores the client's collator.
- **Formats:** `Intl.NumberFormat`, `Intl.DateTimeFormat`, `Intl.ListFormat` and
  `Intl.PluralRules` on the web; `android.icu.text` and resource `<plurals>` on Android;
  `FormatStyle`, String Catalogs and `PersonNameComponentsFormatter` on Apple platforms.
  The currency is a property of the price, not of the locale: a German user paying in
  US dollars sees `1.234,50 $`. Minor units differ — the yen has none, the Kuwaiti dinar
  has three.
- **Names and addresses:** one full-name field unless the product genuinely needs the
  parts; a postcode that is optional where the country has none; address layout from
  per-country metadata such as Google's libaddressinput data rather than a US form.

`references/platform-apis.md` maps each mechanism to the API on the web, Android and
Apple platforms. Read it when writing a fix.

### 5. Gate the sweep in CI

1. The hard-coded-string lint from step 1, failing the build.
2. Message catalogue checks: ICU syntax compiles (`formatjs compile` fails on a bad
   message), Android Lint's `MissingTranslation`, and no key present in the source
   locale but missing from a shipped one.
3. Screenshot tests of the key screens in the pseudo-locale and one right-to-left
   locale, so clipping and mirroring regressions show as a diff.
4. Unit tests for case mapping, sort and number parsing run with the default locale set
   to `tr-TR`, which catches every default-locale conversion at once.

*Gate:* each mechanism in step 3 has at least one automated check, or a written reason
why it is checked by hand each release.

## Anti-patterns

**Sweeping only the next market's language.** It finds that language's bugs and leaves
the mechanism in place for the next one. The set is fixed so each mechanism is tested
once.

**Asserting formatter output as a literal string.** Formatter output changes with CLDR
updates — English time formats gained a narrow no-break space before AM and PM in ICU 72
— so a test comparing against `"1:30 PM"` breaks on a runtime upgrade. Assert on parts
(`formatToParts`) or compare against the formatter's own output.

**Mirroring everything for RTL.** A flipped clock or play button is as wrong as an
unflipped back arrow. Mirror direction, not objects.

**Truncating by `.length`.** JavaScript and Java count UTF-16 code units, so a
`maxlength` or `substring` can split an emoji or a Devanagari conjunct. Count graphemes.

**Inferring currency, language or region from each other.** A locale is a formatting
preference. A Swiss user may read French, pay in euros and live in Germany.

## Output format

```markdown
## Coverage
[Screens swept, locales in the set, platform and build.]

## Defects by mechanism
| Mechanism | Screen | Locale seen in | Evidence (screenshot or string) | Fix |

## Gate
[Each CI check added, what it catches, and any mechanism left to a manual pass with the
reason.]
```

## Reference files

- `references/hostile-locale-set.md` — read at step 3, when running the sweep: per
  locale, how to switch to it on Android, iOS and the web, the exact inputs to try, and
  the expected result.
- `references/platform-apis.md` — read at step 4, when writing a fix: the API for each
  mechanism (messages, plurals, case, direction, segmentation, collation, numbers,
  currency, names, addresses) on the web, Android and Apple platforms.
