# Materials

A material is the visual substance of a page: its colour, type, edges, texture and
voice. It is chosen after the shape and it never decides the composition. A quiet paper
look can carry a mosaic or a single column; the shape from `references/page-shapes.md`
decides which. If a material seems to demand a layout, you are choosing a template and
calling it a material.

## Contents

- What a material specifies
- Choosing: score, do not match keywords
- The eight families

## What a material specifies

Write all of these down in the decision record, with a value for each.

| Field | What to state |
| --- | --- |
| Background band | Light, mid or dark, by lightness of the main background |
| Display face | A class of face (high-contrast serif, grotesque, slab, rounded, monospace and so on), then the actual font if the project has one |
| Body face | One face chosen for long reading |
| Outlier face | At most one extra, used in one place for one job, or none |
| Accent band and posture | The hue band of the accent and how loud it is, from restrained to saturated |
| Colour tokens | In OKLCH: background with two or three steps, ink, muted ink, rule, accent, the ink that sits on the accent, and the focus colour |
| Radius | One corner radius, used everywhere |
| Rule weight | The thickness of lines and borders |
| Depth stance | Flat, edged or soft shadow, and nothing else |
| Texture | At most one family, at low opacity, or none |
| Photo treatment | How photographs are cropped, toned or framed |
| Motion | One to three lines of what moves and how |
| Voice | How the text sounds, in a sentence |

A found design system supplies these already, and then you inherit it instead of choosing.

## Choosing: score, do not match keywords

Matching a word in the brief to a family ("playful" gets the playful look) gives the same
answer to everyone who writes the same word. Score each family against the content instead,
so the choice can be explained and challenged.

Score every family from 0 to 3 on four questions, add them up, and show the top three with
their scores before choosing.

1. **Fit to the material available.** Does the family suit what the page can really show?
   Photographs, numbers, screenshots and long text each favour different families.
2. **Tone.** Does it sound like the organisation and its audience, not like an idea of them?
3. **Contrast needs.** Will text have to sit on photographs, on tints, or on the accent? A
   family whose palette makes that hard scores low.
4. **Legibility for the audience.** Age, screens, reading in a bright place, reading in a
   second language. When two families tie on the total, break the tie on this question
   first: the family with the higher legibility score wins.

An example for a fictional print shop with forty photographs of finished jobs and a price
list, for an audience of designers choosing a printer:

| Family | Fit | Tone | Contrast | Legibility | Total |
| --- | --- | --- | --- | --- | --- |
| Printed press | 3 | 3 | 2 | 3 | 11 |
| Quiet paper | 3 | 2 | 3 | 3 | 11 |
| Bold poster | 2 | 2 | 1 | 3 | 8 |

The two tie at 11, and both score 3 on legibility, so legibility cannot separate them. The
tie then goes to the family with the stronger link to the trade, printed press, and the
record says that is the reason. Quiet paper stays the named runner-up in case the owner
wants something calmer.

## The eight families

Each family below has one worked token set. They are examples to start from, not fixed
values. Adjust the numbers to the content and check contrast on the rendered page against
real backgrounds, which no token list can promise.

### Quiet paper

A light page with a warm off-white ground, a text serif, a single restrained accent and
almost no ornament. Suits writing, studios, practices and anything where reading is the
point. Avoid for a page that needs to shout.

```css
:root {
  --bg-1: oklch(97% 0.008 85);
  --bg-2: oklch(94% 0.012 85);
  --bg-3: oklch(90% 0.016 85);
  --ink: oklch(24% 0.02 60);
  --ink-muted: oklch(46% 0.02 65);
  --rule: oklch(84% 0.014 80);
  --accent: oklch(48% 0.14 35);
  --on-accent: oklch(97% 0.008 85);
  --focus: oklch(50% 0.17 255);
  --radius: 2px;
  --rule-weight: 1px;
}
```

Display face: text serif. Body face: the same serif at text size. Outlier: none. Posture:
restrained. Depth: flat. Texture: fine paper grain at 4 percent, or none. Photos: natural
colour, uncropped where possible. Motion: a short fade and an 8px rise on entrance, nothing
loops. Voice: measured and plain.

### Warm plain

A friendly light page with a cream ground, a rounded humanist sans and a moderate accent.
Suits local services, food, family businesses and anything meant to feel approachable
without being childish.

```css
:root {
  --bg-1: oklch(96% 0.03 85);
  --bg-2: oklch(92% 0.045 80);
  --bg-3: oklch(87% 0.06 75);
  --ink: oklch(27% 0.03 50);
  --ink-muted: oklch(44% 0.03 55);
  --rule: oklch(80% 0.04 70);
  --accent: oklch(52% 0.15 45);
  --on-accent: oklch(98% 0.01 85);
  --focus: oklch(48% 0.16 250);
  --radius: 10px;
  --rule-weight: 1.5px;
}
```

Display face: humanist sans with a soft finish. Body face: the same family. Outlier: a
handwritten face in one place only, such as a signature. Posture: moderate. Depth: a low,
soft shadow on raised items. Texture: none. Photos: warm tone, rounded crop. Motion: gentle
fades. Voice: warm and direct, in the first person.

### Dark after-hours

A dark page for things that happen in the evening: a venue, a film, an audio product. The
light is in the accent and the photographs, not the background.

```css
:root {
  --bg-1: oklch(17% 0.015 270);
  --bg-2: oklch(22% 0.02 270);
  --bg-3: oklch(28% 0.025 270);
  --ink: oklch(94% 0.01 90);
  --ink-muted: oklch(72% 0.015 90);
  --rule: oklch(36% 0.02 270);
  --accent: oklch(82% 0.17 80);
  --on-accent: oklch(20% 0.03 80);
  --focus: oklch(80% 0.14 200);
  --radius: 4px;
  --rule-weight: 1px;
}
```

Display face: grotesque sans, tightly spaced. Body face: a neutral sans at a slightly
larger size, since light text on a dark ground reads smaller. Outlier: none. Posture:
saturated, used sparingly. Depth: none, edges only. Texture: none. Photos: full-bleed with
a dark scrim only where text sits. Motion: slow fades; autoplaying video, if any, is muted
and stops under reduced motion. Voice: short and confident.

### Bold poster

A loud, high-contrast page with huge condensed type, hard edges and a saturated accent.
Suits events, campaigns and sales with a date that matters. Avoid for anything that has to
read as calm or careful.

```css
:root {
  --bg-1: oklch(95% 0.04 100);
  --bg-2: oklch(88% 0.1 100);
  --bg-3: oklch(20% 0.02 30);
  --ink: oklch(18% 0.02 30);
  --ink-muted: oklch(40% 0.03 30);
  --rule: oklch(18% 0.02 30);
  --accent: oklch(55% 0.22 28);
  --on-accent: oklch(98% 0.01 90);
  --focus: oklch(40% 0.17 255);
  --radius: 0px;
  --rule-weight: 4px;
}
```

Display face: heavy condensed sans, set very large. Body face: a plain sans at a generous
size. Outlier: none. Posture: saturated. Depth: none; thick rules do the work. Texture:
none. Photos: high-contrast crops, cut-outs on flat bands. Motion: a fast, hard entrance,
no easing flourishes. Voice: imperative and short.

### Technical linework

A precise page of fine lines and measured spacing, for tools, hardware and engineering. The
structure is visible as hairlines and the type is compact.

```css
:root {
  --bg-1: oklch(96% 0.004 240);
  --bg-2: oklch(92% 0.006 240);
  --bg-3: oklch(86% 0.008 240);
  --ink: oklch(22% 0.015 250);
  --ink-muted: oklch(44% 0.02 250);
  --rule: oklch(70% 0.02 250);
  --accent: oklch(50% 0.12 195);
  --on-accent: oklch(98% 0.005 240);
  --focus: oklch(48% 0.17 285);
  --radius: 0px;
  --rule-weight: 1px;
}
```

Display face: a narrow grotesque or a monospace. Body face: a clear sans. Outlier: a
monospace for values and units only. Posture: restrained. Depth: flat. Texture: a faint
measurement grid at 5 percent. Photos: technical, even light, with callout lines. Motion:
lines draw in, nothing bounces. Voice: exact, with units.

### Soft playful

A light, rounded page with large radii and soft colour, for things that are meant to be
fun: classes, children's products, creative tools.

```css
:root {
  --bg-1: oklch(97% 0.02 330);
  --bg-2: oklch(93% 0.05 330);
  --bg-3: oklch(89% 0.08 200);
  --ink: oklch(25% 0.04 300);
  --ink-muted: oklch(45% 0.04 300);
  --rule: oklch(82% 0.05 320);
  --accent: oklch(55% 0.2 340);
  --on-accent: oklch(98% 0.01 330);
  --focus: oklch(46% 0.17 255);
  --radius: 20px;
  --rule-weight: 2px;
}
```

Display face: a rounded sans. Body face: a friendly sans, larger than usual. Outlier: none.
Posture: moderate to saturated. Depth: soft shadows. Texture: none. Photos: rounded
crops with real faces and hands. Motion: small, springy entrances are allowed here because
the tone is playful; nothing on interface state. Voice: simple words and short sentences.

### Retro screen

A dark page that borrows from early terminals and game screens: monospace type, a
phosphor accent, a hint of scanlines. Suits games, hobbyist projects and developer culture.

```css
:root {
  --bg-1: oklch(16% 0.02 150);
  --bg-2: oklch(21% 0.03 150);
  --bg-3: oklch(27% 0.04 150);
  --ink: oklch(88% 0.12 145);
  --ink-muted: oklch(68% 0.09 145);
  --rule: oklch(40% 0.07 150);
  --accent: oklch(85% 0.19 95);
  --on-accent: oklch(18% 0.03 95);
  --focus: oklch(80% 0.13 220);
  --radius: 0px;
  --rule-weight: 2px;
}
```

Display face: a monospace or a bitmap face, kept to large sizes. Body face: a clean
monospace at a comfortable size. Outlier: none. Posture: saturated on the accent only.
Depth: none. Texture: scanlines at 6 percent, switched off under reduced motion and
forced colours. Photos: low-resolution on purpose, with a border. Motion: a blinking
cursor is the only loop and it stops under reduced motion. Voice: dry and literal.

### Printed press

A page that reads like a printed publication: warm newsprint ground, a high-contrast serif
for headings, tight columns and rules between them. Suits journals, newsletters, print
trades and anything with a lot of real text.

```css
:root {
  --bg-1: oklch(95% 0.02 90);
  --bg-2: oklch(91% 0.03 88);
  --bg-3: oklch(86% 0.04 85);
  --ink: oklch(19% 0.015 60);
  --ink-muted: oklch(40% 0.02 60);
  --rule: oklch(30% 0.02 60);
  --accent: oklch(46% 0.17 25);
  --on-accent: oklch(96% 0.015 90);
  --focus: oklch(45% 0.15 255);
  --radius: 0px;
  --rule-weight: 1px;
}
```

Display face: high-contrast serif. Body face: a text serif set in columns where the width
allows. Outlier: a small-caps sans for datelines. Posture: restrained, one spot colour.
Depth: none; rules, including double rules, separate content. Texture: halftone dots at 5
percent on large image areas. Photos: black and white or a single tone. Motion: none beyond
a fade. Voice: editorial and specific.
