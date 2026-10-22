# Platform APIs by mechanism

The call that handles each mechanism correctly, per platform. Read this at step 4, when
writing a fix. Pass the locale explicitly wherever the API takes one; relying on the
process default is how a server renders every user in its own locale.

## Contents

- [Messages and plurals](#messages-and-plurals)
- [Case mapping](#case-mapping)
- [Direction](#direction)
- [Segmentation and length](#segmentation-and-length)
- [Collation and search](#collation-and-search)
- [Numbers, currency, lists and dates](#numbers-currency-lists-and-dates)
- [Names and addresses](#names-and-addresses)

## Messages and plurals

| Platform | Use |
| --- | --- |
| Web | ICU MessageFormat through a library (FormatJS, i18next with its ICU plugin); `Intl.PluralRules` where you only need the category |
| Android | `<plurals>` resources with `getQuantityString`; `android.icu.text.MessageFormat` for select and nested messages |
| Apple | String Catalogs (`.xcstrings`) with plural and device variations; `String(localized:)` |

Every translated string is a whole sentence. Variables go inside the message so a
translator can move them.

## Case mapping

| Platform | Identifier, key, protocol value | Text shown to a person |
| --- | --- | --- |
| Web | `toUpperCase()` / `toLowerCase()` (locale-invariant) | `toLocaleUpperCase(locale)` |
| Java | `toUpperCase(Locale.ROOT)` | `toUpperCase(userLocale)` |
| Kotlin | `uppercase()` / `lowercase()` (invariant) | `uppercase(locale)` |
| Swift | `uppercased()` (invariant) | `uppercased(with: locale)` |

For case-insensitive comparison of identifiers, compare a case-folded or invariant
lowercase form, never the default-locale form.

## Direction

| Platform | Use |
| --- | --- |
| Web | `dir` on the root element; logical properties (`margin-inline-start`, `padding-inline-end`, `inset-inline-start`, `border-start-start-radius`, `text-align: start`); `:dir(rtl)` to mirror directional icons; `<bdi>` or `dir="auto"` around user-supplied text |
| Android | `android:supportsRtl="true"` in the manifest; `start`/`end` attributes; `layoutDirection`; `autoMirrored` on vector drawables that show direction; `BidiFormatter` for interpolated text |
| Apple | Leading and trailing constraints; SwiftUI mirrors by default; `imageFlippedForRightToLeftLayoutDirection()` on directional images; the layout direction environment value for previews |

Unicode isolates for plain text: first-strong isolate U+2068 before and pop directional
isolate U+2069 after an interpolated value.

## Segmentation and length

| Platform | Words and line breaks | Grapheme clusters |
| --- | --- | --- |
| Web | `Intl.Segmenter(locale, { granularity: "word" })` | `Intl.Segmenter(locale, { granularity: "grapheme" })` |
| Android | `android.icu.text.BreakIterator.getWordInstance(locale)` | `BreakIterator.getCharacterInstance(locale)` |
| Apple | `enumerateSubstrings(in:options:)` with `.byWords` | Swift `String.count` already counts grapheme clusters |

JavaScript `length`, Java `length()` and HTML `maxlength` count UTF-16 code units. Use
grapheme counts for any limit a person sees, and code units only for a storage limit, and
say which one each limit is.

Composition events and Enter handling during an input method conversion belong to the
field, not the locale: see `text-input-edge-cases`.

## Collation and search

| Platform | Sort | Accent- or case-insensitive match |
| --- | --- | --- |
| Web | `Intl.Collator(locale).compare`, or `localeCompare(other, locale)` | `Intl.Collator(locale, { sensitivity: "base" })` |
| Java, Android | `java.text.Collator.getInstance(locale)` or `android.icu.text.Collator` | Collator strength `PRIMARY` |
| Apple | `localizedStandardCompare`, or `compare(_:options:range:locale:)` | `.caseInsensitive` and `.diacriticInsensitive` options |
| Database | A column or query collation for the locale (ICU collations in PostgreSQL) | A normalised search column, or the engine's accent-insensitive collation |

A list sorted on the client and paginated on the server must use the same collation on
both, or items move between pages.

## Numbers, currency, lists and dates

| Need | Web | Android | Apple |
| --- | --- | --- | --- |
| Number | `Intl.NumberFormat(locale)` | `android.icu.text.NumberFormat.getInstance(locale)` | `.formatted(.number)` with a locale |
| Currency | `Intl.NumberFormat(locale, { style: "currency", currency: "EUR" })` | `NumberFormat.getCurrencyInstance(locale)` with `setCurrency` | `.formatted(.currency(code: "EUR"))` |
| List ("A, B and C") | `Intl.ListFormat(locale)` | `android.icu.text.ListFormatter` | `ListFormatter` |
| Relative time | `Intl.RelativeTimeFormat(locale)` | `android.icu.text.RelativeDateTimeFormatter` | `RelativeDateTimeFormatter` |
| Date | `Intl.DateTimeFormat(locale, options)` | `DateTimeFormatter.ofLocalizedDate` or ICU skeletons | `.formatted(date:time:)` or `Date.FormatStyle` |

Parse what the user typed with the same locale's parser, after Unicode NFKC normalisation
so full-width digits are read. Store money as an integer in the currency's minor unit and
take the number of decimals from the currency, not from the locale.

## Names and addresses

- Names: one full-name field where possible, plus an optional "what should we call you"
  field when the product addresses people by name. On Apple platforms
  `PersonNameComponentsFormatter` orders parts by locale. The W3C article "Personal
  names around the world" covers the variations worth designing for.
- Addresses: lay out and validate from per-country metadata, such as the data behind
  Google's libaddressinput, rather than one form. Postcode, state and even street number
  are optional in some countries. On Apple platforms `CNPostalAddressFormatter` formats a
  stored address for the user's region.
- Phone numbers: store E.164 and format for display with a maintained library such as
  libphonenumber.
