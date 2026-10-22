# Hostile locale set

How to switch to each locale, what to type or load, and what correct looks like. Read
this at step 3, while running the sweep.

## Contents

- [Switching locale](#switching-locale)
- [Per-locale inputs and expected results](#per-locale-inputs-and-expected-results)
- [Screens to walk in every locale](#screens-to-walk-in-every-locale)

## Switching locale

| Platform | Whole device or browser | Just the app, for a test run |
| --- | --- | --- |
| Android | Settings, System, Languages; developer option "Force RTL layout direction" for a quick direction check | Android 13 and later: `adb shell cmd locale set-app-locales com.example.app --locales tr-TR`; pseudo-locales `en-XA` and `ar-XB` appear once `pseudoLocalesEnabled true` is set on the debug build |
| iOS | Settings, General, Language and Region | Xcode scheme, Run, Options: App Language and App Region (including the pseudolanguages); or launch arguments `-AppleLanguages "(tr)" -AppleLocale tr_TR` |
| Web | Browser language preferences | Chrome DevTools Sensors panel locale override; Playwright's `locale` context option for automated runs |

Set language and region separately where the platform allows. A user with English
language and German region expects English words with German number formats, and that
combination finds a different class of bug.

## Per-locale inputs and expected results

### Pseudo-locale (`en-XA`, Xcode accented or double-length, FormatJS `en-XA`)

- Every string accented and bracketed. An unaccented string is hard-coded; a bracket in
  the middle of a sentence is concatenation.
- No clipping, overlap or ellipsis on primary actions at the device's smallest supported
  width.

### German (`de-DE`)

- A long compound such as `Rechtsschutzversicherungsgesellschaften` in a button, a tab
  and a table header: it wraps or hyphenates, it does not push the layout off screen.
- `Straße` uppercased is `STRASSE`: any code that assumes uppercasing keeps the length
  breaks here.
- `1234.5` formats as `1.234,5`; a price input accepts `1.234,50`.

### Turkish (`tr-TR`)

- With the device default set to Turkish: `"title"` uppercased by a default-locale call
  becomes `TİTLE`, and `"INFO"` lowercased becomes `ınfo`. Anything used as a key — enum
  lookup, header name, email comparison, file extension check — must be unchanged.
- A login with `INFO@EXAMPLE.COM` still finds the account.

### Arabic (`ar`, and `ar-EG` for digits)

- Layout mirrors: navigation, progress, swipe direction, back arrow.
- A Latin name or phone number inside an Arabic sentence stays intact and in place.
- Plurals for 0, 1, 2, 3, 11 and 100 each use their own category (zero, one, two, few,
  many, other).
- Some Arabic locales format digits as Arabic-Indic (`١٢٣`); number inputs accept them
  or the product states that it does not.

### Hebrew (`he-IL`)

- The same direction checks with a different script and font, which catches layouts that
  special-case Arabic rather than right-to-left.

### Japanese (`ja-JP`)

- A long sentence with no spaces wraps at sensible points and truncates without breaking
  a character.
- Typing with the Japanese input method: pressing Enter to confirm a conversion does not
  submit the form.
- Full-width digits (`１２３`) in a number field are accepted after normalisation, or
  rejected with a clear message.
- A greeting built from a name shows the family name first when the user enters it that
  way.

### Thai (`th-TH`)

- `ภาษาไทยไม่มีช่องว่างระหว่างคำ` wraps on word boundaries, not mid-word, and not only
  at the end of the string.
- Stacked vowel and tone marks are not clipped by a fixed line height.
- A user whose calendar is Buddhist sees 2569 for 2026; any code that parses a year back
  out of formatted text breaks here.

### Polish (`pl-PL`)

- 1 `plik`, 2 `pliki`, 5 `plików`, 12 `plików`, 22 `pliki`: each from the plural rules,
  not from `count == 1`.

### Swedish (`sv-SE`) against German

- `Andersson`, `Zetterberg`, `Åström`, `Öberg` is the Swedish order; German puts
  `Åström` and `Öberg` before `Zetterberg`. The list, the search and any server-side sort
  agree with each other.
- Searching `Ostrom` finds `Åström` only if the product chose accent-insensitive search
  — decide, then test it.

### French (`fr-FR`), Indian English (`en-IN`), Swiss German (`de-CH`)

- `1234567.89` formats as `1 234 567,89` in French, with a narrow no-break space;
  `12,34,567.89` in Indian English; `1’234’567.89` in Swiss German.
- A number parser accepts what the same locale's formatter produced.

### Hungarian (`hu-HU`)

- Family name first in both display and sort; no greeting that assumes the first token
  is a given name.

## Screens to walk in every locale

Walk the same list each time so locales are comparable: onboarding and sign-in, the main
list or feed, a detail screen, any form with numbers, money or addresses, search and sort,
settings, empty and error states, notifications and emails, and anything with a count in
it.
