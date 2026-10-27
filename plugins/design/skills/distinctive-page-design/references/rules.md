# Rules

The rule list behind `scripts/page_lint.py`. `assets/rules.json` is the table the script
reads; this file is the same list for a person, with the reason beside each rule. A test
fails if an id exists in one and not the other, so edit them together.

Each rule has an id, a tier, a kind and a reason. The kind says how it is tested:
`css`, `html` and `copy` rules are mechanical, and a `judged` rule is something only a
reader can decide, so the script lists it as a manual check and never reports it as passed.

## Contents

- Tiers
- Numbers are defaults
- What the lint reads
- Floor rules
- Taste rules

## Tiers

- **Floor** rules cover correctness, accessibility and honesty. They cannot be waived. A
  floor finding is fixed, or the rule was wrong and the table is corrected with a test.
- **Taste** rules name the habits of a default design. Any of them can be waived with a
  reason written in the decision record as `waive: <rule-id> — <reason>`, and a waiver
  stands only once the fresh-context reviewer agrees with it. A waiver with no reason, or
  for a floor rule, is refused and the finding stays.

## Numbers are defaults

Where a rule has a number (a minimum size, a stop count) it is a default, and the decision
record may set another for this project with `override: <rule-id> <parameter>=<number>`,
for example `override: taste-gradient-stops max=5`. A project that wants a long gradient on
purpose says so once in writing rather than having the rules impose one house look. Lists
such as the vague-copy phrases are edited in the table itself.

An override has limits, because one that loosened a floor rule would do the work of a
waiver without anyone asking for a reason:

- **Taste rules** accept an override in either direction.
- **Floor rules** accept an override only in the stricter direction. Each numeric
  parameter of a floor rule names its stricter direction in the table (`stricter`), so
  `override: floor-body-size minimum=18` is applied and `minimum=14` is refused with a
  reported refusal, and the finding stays. A floor parameter with no declared direction
  cannot be overridden. The comparison is always against the table's value, so a chain of
  overrides cannot walk below it.
- A value that is not a finite, non-negative number of the parameter's own kind (a whole
  number for a count) is refused and reported, and the table's value stands.
- Every applied override is listed in the text report and in the JSON `overrides` list with
  rule, parameter, old value and new value, and the fresh-context reviewer confirms each
  one as it does each waiver.

## What the lint reads

The lint is a mechanical aid. It reads the common ways each rule is broken, not every way,
and the limits below list what it does not read. A clean report means none of those
common forms was found; it does not mean the page meets the rule. Floor rules stay binding
on the page whether or not the lint sees a breach, and the fresh-context review and
`accessibility-audit` are the backstop for the forms listed here.

What it normalises before reading: comments are removed, property names and units are
read in any case, a trailing `!important` is dropped from a value, and a selector list is
read one part at a time, so a marker such as `.js` excuses only the part that carries it
and never one inside `:not(...)`, except `html:not(.no-js)` or `:root:not(.no-js)`, which is read as `html.js`.

What it does not read, for every css rule:

- A value built with `calc()`, `min()`, `max()`, `clamp()` or `var()`, so a size, a line
  height or an opacity held in a custom property is not followed. The one exception is
  `floor-viewport-width`, which reads a `100vw` wherever it sits in the value, `calc()`
  included.
- A custom property itself: `--x: 0` is a declaration of `--x`, not of the property that
  later uses it.
- Shorthands that carry a longhand, such as `font`, and the percentage form of a size.
- A value that is zero or hidden only after evaluation, such as `opacity: -1`,
  `opacity: calc(0)` or `opacity: 0e0`.
- A nested or descendant selector such as `html body` or `body.menu`, where a rule names
  `html` (or its alias `:root`) or `body` alone, and a selector built with `:is()` or `:where()`.
- Vendor-prefixed and logical properties, such as `-ms-overflow-x`, `overflow-inline`,
  `inline-size` or `border-inline-width`, other than the prefixed animation and transition
  names `floor-reduced-motion` reads.
- A stylesheet the page loads from elsewhere, and any rule applied by a script.
- A number written in scientific notation, such as `1E1px`.

For the html rules, a heading made with `role="heading"` is not part of the outline it
checks, and a boolean attribute counts as set whatever its value, so `muted="false"` still
satisfies `floor-autoplay-muted`.

## Floor rules

### `floor-lang`

Kind html. The document element carries a non-empty `lang`. Why: screen readers pick a
voice and translation tools pick a source language from it.

### `floor-title`

Kind html. The document has a non-empty `<title>`. Why: it names the tab, the history
entry and the search result.

### `floor-meta-description`

Kind html. A `<meta name="description">` with content is present. Why: without one a
search result quotes whatever text comes first, often a navigation label.

### `floor-heading-order`

Kind html. Heading levels start at `h1` and never skip downward. Why: assistive technology
navigates by the outline, and a gap reads as missing content.

### `floor-body-size`

Kind css. Body text (`html`, `:root`, `body`, `p`, `main`, `article`, `li`, `.prose`) is not set
under 16px, reading `rem` and `em` at 16px and `pt` at 4/3 px. Parameter `minimum`. Why: smaller running text
costs everyone reading on a phone. Stated limits: sizes set by the `font` shorthand, in
`pc`, in keywords such as `small` or in percentages are not read, and neither is a changed
root size. The common `html { font-size:
62.5% }` trick makes `1rem` ten pixels, yet the rule still reads `rem` at 16px, so a page
that uses it is checked in rendered pixels by `visual-review`, not here. A rule nested
inside another, as in `main { p { font-size: 12px } }`, resolves to the descendant selector
`main p`, which the selector list above never matches, so a nested or descendant
declaration is not read here either.

### `floor-body-leading`

Kind css. Body line height is not a unitless number under 1.3. Parameter `minimum`. Why:
tight lines make the eye lose its place on the way back to the next line. Stated limits: a
line height set inside the `font` shorthand is not read, and only unitless values are read,
so a leading in `px`, `em` or `%` is not.

### `floor-focus-visible`

Kind css, with a condition on the html. When the page has links, buttons or form controls
and its styles declare anything, some `:focus-visible` style exists. Why: a keyboard user
needs to see where they are, and the browser's own ring is usually removed by a reset.
Stated limit: the text `:focus-visible` anywhere in the styles satisfies it, so a style
that does not draw a ring still passes, and a stylesheet linted alone with no html beside
it is reported because the lint cannot see whether anything there is focusable.

### `floor-focus-border-width`

Kind css. A `:focus` or `:focus-visible` rule does not declare a border or border width.
Why: changing border width moves the layout on every focus change, and the shift is worst
for the people who move by keyboard. Draw the ring with `outline` and `outline-offset`.

### `floor-reveal-hidden`

Kind css. A reveal or fade-in class does not set `opacity` to zero, in any spelling of zero
(`0`, `00`, `.0`, `+0`, `0%`), with or without `!important`, unless the selector is
scoped to a script-enabled marker such as `.js`, or the declaration sits inside a
`@media (scripting: enabled)` query, which applies only where scripts run. That means the
whole query is `(scripting: enabled)`, or it is joined to other conditions with `and`; a
`not`, an `or` or a comma list with another alternative is not excused, because each of
them also applies where scripts do not run. Why: content hidden until a script runs is
simply missing when the script fails, is blocked or is switched off. Stated limits: only
the class and attribute names in the selector list are read, so a hiding class named
anything else is not; only `.js`, `.has-js`, `.js-enabled` and `:not(.no-js)` on `html` or `:root` count as script markers; a
rule nested inside a reveal rule is read as the descendant it is and reported.

### `floor-reduced-motion`

Kind css. When the styles hold an animation, a transition or keyframes, they also hold a
`prefers-reduced-motion` query. Why: motion can make some people ill, and the preference
is one line to honour. Stated limit: the words anywhere in the styles, outside a comment,
satisfy it, whether or not the query turns any motion off; `transition: none` still counts
as a transition. Whether the query actually turns the motion off is for
`accessibility-audit` to confirm rendered.

### `floor-autoplay-muted`

Kind html. A `<video>` with `autoplay` also has `muted`. Why: browsers refuse unmuted
autoplay, and where one allows it, sound nobody asked for is a reason to leave.

### `floor-lazy-largest`

Kind html. The image with the largest declared area (the first image when none declares a
size) is not `loading="lazy"`. Why: the largest image is usually the first screen's main
content, and lazy loading defers exactly that.

### `floor-hidden-overflow`

Kind css. `html` and `body` do not hide the horizontal axis: `overflow-x` set to `hidden`
or `clip`, or `overflow` whose first value is `hidden` or `clip`, as in
`overflow: hidden auto`. `overflow: auto hidden` hides only the vertical axis and is not
reported.
Why: it hides sideways scrolling instead of finding the element that causes it, and the
cropped content is lost to the people who needed to scroll. A nested form such as
`html { body { overflow-x: hidden } }` resolves to the descendant selector `html body`,
which this rule does not match, so it is not read; write the declaration on `body` itself.

### `floor-viewport-width`

Kind css. No `width`, `min-width` or `max-width` uses `100vw`. Why: `100vw` includes the
scrollbar, so the page is wider than its window wherever scrollbars take space. Stated
limit: the whole words `100vw`, `100dvw`, `100svw` and `100lvw` are read, so `100.0vw`, a `100vw` held in a custom property
and the logical `inline-size` are not.

### `floor-placeholder-block`

Kind html. No image points at a placeholder address, and no element classed as a
placeholder is empty. Why: a large block that shows nothing is a defect a visitor sees at
once.

### `floor-placeholder-copy`

Kind copy. Filler text such as lorem ipsum or "your company here" is not on the page. Why:
it is the clearest sign that nobody read the page before shipping.

### `floor-invented-proof`

Kind judged. Every figure, quote, customer, logo and testimonial comes from the user's own
material. Why: an invented number or endorsement is a false claim made in someone else's
name, and a page that has no proof yet should say less rather than make some up.

### `floor-image-urls-from-memory`

Kind judged. Every image address was supplied by the user or exists in the project. Why: an
address written from memory is a broken image or someone else's photograph.

### `floor-reflow-200`

Kind judged, handed to `accessibility-audit`. The page reflows at 200 percent zoom and at
a 320px wide viewport without sideways scrolling. Why: low-vision users zoom instead of
using a bigger screen, and a layout that overflows takes the text out of reach.

### `floor-forced-colors`

Kind judged, handed to `accessibility-audit`. Under `forced-colors` the page stays usable:
borders, focus rings and state that colour alone carried are still visible. Why: forced
colours replace the palette, and anything drawn with a background colour alone disappears.

### `floor-contrast-preference`

Kind judged, handed to `visual-review`. The page honours `prefers-contrast` and keeps its
contrast against real backgrounds, including text over photographs. Why: contrast depends
on what is behind the text, which a stylesheet read cannot know.

### `floor-chart-alternatives`

Kind judged, handed to `accessibility-audit`. Every chart or diagram has a text alternative
that says what the picture shows. Why: a page organised around a diagram is empty to
anyone who cannot see it unless the text carries the finding.

## Taste rules

### `taste-gradient-hue`

Kind css. No gradient uses a saturated purple, blue or pink, by hex, `hsl()`, `oklch()` or
colour name; `rgb()` and `rgba()` are read in both comma and space syntax. Parameters: the
hue bands and the saturation floor. Stated limit: `hwb()`, `lab()`, `lch()`, `oklab()` and
`color()` are not read inside gradients. Why: it is the colour a generated page reaches
for first, so it says nothing about this page.

### `taste-gradient-clip-text`

Kind css. Text is not filled by `background-clip: text`. Why: gradient-filled headlines are
a familiar template tell and are fragile when the gradient fails.

### `taste-gradient-stops`

Kind css. A gradient has at most three stops. Parameter `max`. Why: more stops read as a
rainbow rather than a choice.

### `taste-glow-halo`

Kind css. No `filter: blur()` of 40px or more. Why: a large blurred shape behind text is
the glow or blob that stands in for a design decision.

### `taste-pure-black-white`

Kind css. Colour properties outside the token block do not use `#000`, `#fff`, `black` or
`white`. A file name inside `url()` is not read as a colour. Why: pure extremes sit hard
against any tinted palette. Declare them as tokens if the palette really needs them.

### `taste-literal-colours`

Kind css. Colour properties outside the token block use the declared tokens, not hex or
colour functions. Why: a palette written in two places drifts.

### `taste-literal-fonts`

Kind css. `font-family` outside the token block uses a declared token. Why: the same drift,
for type.

### `taste-system-display-face`

Kind css. Headings and display classes are not set in a default system sans. Why: the
display face carries the most personality on a page, and the default carries none.

### `taste-family-count`

Kind css. At most three font families across the styles. Parameter `max`. Why: a fourth
family rarely adds anything a weight or a size could not.

### `taste-weight-count`

Kind css. At most three font weights. Parameter `max`. Why: the same reasoning, and each
weight is another file to download.

### `taste-card-trio`

Kind html. No container holds three or more equal cards that each open with an icon over a
heading. Parameter `min_count`. Why: it is the layout a model reaches for when the content
has three items, whether or not the items deserve equal weight.

### `taste-nested-card`

Kind html. No card sits inside a card. Why: two borders and two shadows around one idea.

### `taste-eyebrow-heading`

Kind html. A small label does not sit directly above nearly every section heading.
Parameters: a count and a share of headings. Why: a label that appears everywhere stops
carrying information. The label is found by its class name.

### `taste-emoji-icon`

Kind copy. An emoji does not lead a heading, list item, button or link, or sit in an icon
element. A character that defaults to text style, such as the check mark and the cross, is
not an emoji until it carries the emoji variation selector, so a plain tick in a list is
left alone. A pair of regional indicator letters, which draws a flag, counts as an emoji.
Why: it renders differently on every system and cannot be styled.

### `taste-icon-sets`

Kind html. Only one icon library loads. Only `link rel="stylesheet"` and `script src`
addresses count, so a favicon or touch icon beside a library is not a second set. An address counts when it contains `icon`, `fontawesome` (so
`kit.fontawesome.com` too) or `lucide`, in a script or a package URL. Why: two
sets disagree on stroke and corner, and the mismatch reads as carelessness.

### `taste-transition-all`

Kind css. No `transition` names `all`. Why: it animates properties nobody chose, including
ones added later.

### `taste-transition-layout`

Kind css. No transition runs on a layout property. Why: size, position and spacing changes
reflow the page on every frame. Move `transform` or `opacity`.

### `taste-bounce-easing`

Kind css. Interface state does not use overshooting or elastic easing. Why: it makes
controls feel toy-like, and the overshoot reads as a glitch on a small element.

### `taste-hover-lift`

Kind css. A card does not rise or scale on hover, including inside a nested `&:hover`
rule. Why: the effect on every card says there is no difference between them.

### `taste-repeated-sections`

Kind html. Neighbouring sections do not share one structure. Parameter `min_nodes`. Why:
the page reads as a template filled in, and the eye stops reading in the third copy.

### `taste-email-close`

Kind html. An email field is not in the last section or the footer. Why: a mailing-list
band closing the page is the default ending. Waive it, with the reason, when the page's job
is the mailing list.

### `taste-hero-vh`

Kind css. A hero is not sized in `vh`, unless the same selector in the same file also sets
that property in `svh`, `dvh` or `lvh`, the usual fallback pair. Why: on a phone the
address bar changes the height of `vh` and the hero jumps. Use `svh` or `dvh`.

### `taste-vague-copy`

Kind copy. Visible text avoids the phrases in the table, such as "seamless" and "next
level". Why: a vague superlative could describe any product, which is the problem. The
list is data to edit, not a ban.

### `taste-neighbour-test`

Kind judged. A different request in the same category would not land on the same shape and
material. If it would, change at least two fingerprint axes. Why: distinctiveness is
measured against the neighbours, not against the previous draft.
