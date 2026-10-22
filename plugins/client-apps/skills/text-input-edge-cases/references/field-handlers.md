# Field handlers

## Contents

- Counting and truncating graphemes
- A composition-safe Enter handler
- Transforms that wait for composition to end
- Save-time cleaning for display text
- Identifier keys
- Matching in search
- Displaying user text

Each snippet is the smallest version that holds against the corpus. Run them against the skill's corpus before adopting them, and keep the server's copy authoritative.

## Counting and truncating graphemes

```js
const graphemes = new Intl.Segmenter(undefined, { granularity: 'grapheme' });

export function graphemeCount(text) {
  let count = 0;
  for (const _ of graphemes.segment(text)) count += 1;
  return count;
}

export function truncateGraphemes(text, max) {
  let out = '';
  let count = 0;
  for (const { segment } of graphemes.segment(text)) {
    if (count === max) break;
    out += segment;
    count += 1;
  }
  return out;
}
```

Show the counter from `graphemeCount`, and refuse or warn at the limit rather than silently truncating what the user typed. Use `truncateGraphemes` only where truncation is the product decision, such as previews. Grapheme rules follow the engine's Unicode version, so a server on an older runtime may count a few Indic strings differently; that is the reason for the server margin in the skill.

## A composition-safe Enter handler

```js
messageInput.addEventListener('keydown', (event) => {
  if (event.key !== 'Enter' || event.shiftKey) return;
  // Composing, or WebKit's late keydown for the Enter that ended composition.
  if (event.isComposing || event.keyCode === 229) return;
  event.preventDefault();
  send();
});
```

In React, read `event.nativeEvent.isComposing`; the synthetic event does not carry it. `keyCode` is deprecated but is still the only signal for the WebKit ordering, so keep it with a comment saying why.

## Transforms that wait for composition to end

Uppercasing, masks, character filters and length enforcement must not touch the value mid-composition, or the input method loses its place and the user sees duplicated or vanished characters.

```js
let composing = false;
field.addEventListener('compositionstart', () => { composing = true; });
field.addEventListener('compositionend', () => { composing = false; applyTransforms(field); });
field.addEventListener('input', () => { if (!composing) applyTransforms(field); });
```

In a controlled React input, keep the raw value in state during composition and apply transforms in `onCompositionEnd` and in `onChange` only when not composing.

## Save-time cleaning for display text

Run on the server, at the boundary, once:

```js
const CONTROLS = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]/g; // keeps \t \n \r

export function cleanDisplayText(raw, { multiline = false, maxCodePoints }) {
  if (!raw.isWellFormed()) throw new ValidationError('text contains a lone surrogate');
  let text = raw.replace(/\r\n?/g, '\n').replace(CONTROLS, '');
  if (!multiline) text = text.replace(/[\n\t]+/g, ' ');
  text = text.normalize('NFC').trim();
  if (text.length === 0) throw new ValidationError('required');
  if ([...text].length > maxCodePoints) throw new ValidationError('too long');
  return text;
}
```

Normalise after stripping, not before: a control character between a letter and its combining mark blocks composition, so `Zoe\u0000\u0308` normalised first and stripped second is stored as `Zoe\u0308`, which is not NFC and does not match `Zoë`. `maxCodePoints` is the storage ceiling, set above the user-facing grapheme limit with the margin the contract records. The function never rejects a character for being unusual, only for being a control character, unpaired or over the ceiling.

## Identifier keys

```js
const BIDI_CONTROLS = /[\u202A-\u202E\u2066-\u2069]/;
const INVISIBLES = /\p{Default_Ignorable_Code_Point}/u;

export function identifierKey(raw) {
  const folded = raw.normalize('NFKC').trim().toLowerCase().normalize('NFKC');
  if (BIDI_CONTROLS.test(folded) || INVISIBLES.test(folded) || /\s/u.test(folded)) {
    throw new ValidationError('identifier contains invisible or whitespace characters');
  }
  return folded;
}
```

The key is trimmed before the whitespace check, so an autofilled `\u00A0name\u00A0` becomes `name` as the corpus expects rather than being rejected. `INVISIBLES` uses the Unicode default-ignorable property rather than a hand-picked range, because NFKC leaves the soft hyphen U+00AD, the combining grapheme joiner U+034F, the invisible separator U+2063 in place and turns the Hangul filler U+3164 into another invisible filler, and each of those lets `ali\u00ADce` register beside `alice`. The property also covers U+200C and U+200D, which Persian and some Indic names need; if the contract admits those scripts, exempt the two joiners for them. Keep these patterns without the `g` flag: a global regular expression used with `.test()` remembers `lastIndex` between calls and will pass every other bad input. `toLowerCase()` is a case mapping, not full Unicode case folding, which is close enough for most products; where it is not, use a library implementing the RFC 8265 PRECIS username profiles. NFKC does not catch cross-script look-alikes such as a Cyrillic `\u0430` in a Latin name; that needs a confusables skeleton per Unicode Technical Standard 39, compared against the skeletons of existing keys. Store the key in its own column with the unique index, and the user's original text for display.

## Matching in search

Compare with a collator rather than by lowercasing both sides:

```js
const matcher = new Intl.Collator(undefined, { sensitivity: 'base' });
matcher.compare('resume', 'Résumé'); // 0: equal ignoring case and accents
```

On the database side, the equivalent is an accent- and case-insensitive collation or a normalised search column, not a `LOWER()` on both sides.

## Displaying user text

```html
<input name="display_name" dir="auto" autocomplete="name">
<p><bdi>{{ user.displayName }}</bdi> posted 3 comments</p>
```

`dir="auto"` picks the direction from the first strong character of the value. `<bdi>` isolates the user's text so a right-to-left name does not reorder the number and punctuation around it. Both are needed: the first fixes the field, the second fixes every sentence that quotes it.
