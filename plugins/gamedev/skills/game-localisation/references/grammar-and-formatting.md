# Plurals, gender and formatting

Read this at step 4 when messages are being written. It covers how plural categories differ by language, how to structure a message so a translator can handle them, and how numbers, dates and currency are formatted.

## Contents

- [Plural categories](#plural-categories)
- [Structuring the message](#structuring-the-message)
- [Quoting and apostrophes](#quoting-and-apostrophes)
- [Ordinals](#ordinals)
- [Gender and other agreement](#gender-and-other-agreement)
- [Numbers, dates and currency](#numbers-dates-and-currency)
- [Testing](#testing)

## Plural categories

CLDR defines six plural categories, `zero`, `one`, `two`, `few`, `many` and `other`. `other` is mandatory, and a language may have any combination of the others (Unicode TR35, Language Plural Rules: <https://unicode.org/reports/tr35/tr35-numbers.html#Language_Plural_Rules>). The names are labels for rules, not meanings: `few` in Russian is not the same set of numbers as `few` in Arabic, and a category does not mean "a small amount".

The rules live in CLDR's `common/supplemental/plurals.xml` (<https://github.com/unicode-org/cldr/blob/main/common/supplemental/plurals.xml>). Read from the main branch on 19 October 2026, the cardinal categories for some common languages are:

| Language | Categories | What the rule does |
| --- | --- | --- |
| Chinese, Japanese, Korean | `other` | No grammatical plural; one form serves every number |
| English, German, Dutch, Swedish | `one`, `other` | `one` is exactly 1 with no decimal places |
| French, Portuguese | `one`, `many`, `other` | `one` covers 0 and 1; `many` is for numbers in millions and above |
| Hebrew | `one`, `two`, `other` | `two` is exactly 2 |
| Russian, Ukrainian | `one`, `few`, `many`, `other` | `one` is 1, 21, 31 and so on, but not 11; `few` is 2 to 4, 22 to 24 and so on; `many` is 0 and 5 to 19, with the rest by last digits; `other` is fractions |
| Polish | `one`, `few`, `many`, `other` | Close to Russian, but `one` is only exactly 1 |
| Arabic | `zero`, `one`, `two`, `few`, `many`, `other` | All six, with `few` for 3 to 10 and `many` for 11 to 99, repeating on the last two digits |

That table is a snapshot to show the range, not data to copy into a game. Take the rules from your formatting library or the current CLDR release, because they change between releases. Two consequences hold regardless: a message with `one` and `other` is not translatable into Russian, and one with a hard-coded `if count == 1` is wrong for French, where 0 takes the singular, and for Russian, where 21 does.

Godot's documentation states the same constraint: some languages have more than two plural forms, and it applies pluralisation to positive or zero integers only, because negative and floating-point values usually represent physical quantities for which singular and plural do not clearly apply (<https://docs.godotengine.org/en/stable/tutorials/i18n/internationalizing_games.html>). Decimals therefore need a decision of their own: CLDR's `other` is the category for fractions in several of the languages above.

## Structuring the message

ICU MessageFormat puts the choice inside the message, so the translator receives one unit (<https://unicode-org.github.io/icu/userguide/format_parse/messages/>). The documentation's advice, which is the structure to follow:

- Make the complex argument the outermost structure and write full sentences in every branch. Covering only a fragment makes it hard for the translator to see how the fragment joins the rest, and to know whether they may lengthen or shorten the part inside the branch.
- When `select` and `plural` nest, put `select`, with its fixed set of choices, outside and the `plural`, ideally only one, inside.
- Give the source plural the branches the source language needs and expect the translator, with the translation system, to add `few`, `many` and the others per target language. The documentation notes that an English message with `=0` and `=1` branches needs no `one` branch, because it would never be selected, and always needs `other`.
- The `choice` argument type is discouraged: it cannot handle plural rules for many languages.

A message in this shape, using the documentation's own pattern for plural with an offset:

```text
{num_guests, plural, offset:1
  =0 {{host} does not give a party.}
  =1 {{host} invites {guest} to their party.}
  other {{host} invites {guest} and # other people to their party.}}
```

When the engine is not ICU, check what it supports before choosing a message shape. Godot's `tr_n` takes a singular and a plural form plus a count, and its gettext `.po` format has a `msgid_plural` entry with one `msgstr[n]` per form; check in the engine's documentation which plural rule it applies for each target language, and test every shipped language, because a file that holds a slot for each form does not by itself prove the engine picks the right one. If an engine offers only singular and plural, restate the message so it does not need a count (for example by showing the number in a label beside the noun) rather than leaving the unsupported languages wrong.

## Quoting and apostrophes

ICU treats the apostrophe as quoting syntax. A pair of ASCII apostrophes always stands for one apostrophe; since ICU 4.8 a single apostrophe only starts quoted text when it immediately precedes a character that needs quoting. The documentation's recommendation is to use the typographic apostrophe, U+2019, in human-readable text and the ASCII one only in program syntax. An apostrophe directly before a brace, as in `l'{name}`, is the case that breaks, and French text is where it is most likely to appear. Fix it in the style guide, not message by message.

## Ordinals

"1st", "2nd" and "3rd" are a separate rule set from the cardinal plurals: TR35 defines `ordinal` rules next to `cardinal`, with the same six categories. ICU's message pattern grammar has a `selectordinal` argument for them (<https://github.com/unicode-org/icu/blob/main/icu4c/source/i18n/unicode/msgfmt.h>). Do not build ordinals by appending `st` or `nd` in code. German, for instance, writes an ordinal as a number followed by a full stop (CLDR's minimal pairs include `{0}. Abzweigung nach rechts nehmen`, in TR35), and a message gives the translator that choice.

## Gender and other agreement

Plurals are one case of agreement. In many languages an adjective, a verb or a pronoun changes with the gender of a person or item it refers to, and sometimes with grammatical case. CLDR documents grammatical inflection as a topic of its own (<https://cldr.unicode.org/translation/grammatical-inflection>).

- Decide in the data model whether a character, an item or the player has a grammatical gender, and store it as an attribute the message can `select` on. Nothing in the translation spreadsheet can supply what the game does not know.
- Give the translator the cases that arise: "the player is addressed", "an item is the object of a verb", and the like, as notes on the entry, with the values the select can take.
- Where the game never knows (a player-chosen name with no declared gender), write the sentence so it does not depend on it, and tell the translator that the neutral form is intended.
- Do not insert a variable inside a sentence that must agree with it, such as an item name placed after an article. Either store the name with its article and agreement as part of the item data, or restructure the sentence so the name stands alone.

## Numbers, dates and currency

- **Format through locale data.** ICU recommends formatting the argument yourself before passing it to the message, and, where a message formats a date or number, using skeletons rather than patterns. The skeleton is a locale-independent description that each locale renders in its own style.
- **Do not let translators edit the pattern.** The documentation's reasons: translators make mistakes in format syntax, CLDR's curated patterns are lost, and a translation into a general language such as French or Arabic would then be applied in every country that uses it, whereas skeletons follow the regional locale such as `fr-CA`.
- **Use the locale, not just the language,** when units, spelling and currency matter. Godot's documentation uses English in the United States and Great Britain as the example.
- **Digits can differ.** Some locales use a different numbering system. Godot's `TextServer.format_number` converts 0 to 9 to the localised numbering system and `parse_number` converts back; its number-input controls do so automatically.
- **Decimal and grouping separators differ,** so a number is never built by string joining. Parse player input with the same locale data.
- **Take prices from the store where it provides them.** Where the platform's purchase interface returns a localised price string, display that rather than formatting a price yourself, and keep only the surrounding words in the table. Check the platform's documentation for what it returns.
- **Units** such as distance, weight and temperature are a presentation choice per locale; convert at display time and keep the stored value in one unit.

## Testing

For each plural message, run the numbers that CLDR lists as samples for each category of each shipped language through the real formatter, at least one number per category, and read the result. For the languages in the table above, 0, 1, 2, 5, 11, 21, 100, 1000000 and a decimal such as 1.5 between them reach every category. For gender, run every combination the `select` allows. This is a few lines of test code per message type, and it is the only check that finds a missing `few` or `many` branch before a player does.
