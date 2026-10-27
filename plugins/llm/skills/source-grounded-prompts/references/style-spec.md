# The style spec

Read this at step 4 of the workflow. The spec is the half of the prompt that controls look and shape. It is short on purpose: every field either removes a choice the assistant would otherwise make at random, or states a limit it would otherwise exceed. A field that does neither does not belong in it.

## Shape of the spec

Open with the concept line from step 2, in prose, then a labelled block. Prose carries intent; labels carry limits the assistant can be held to.

| Field | What it holds | Why it exists |
| --- | --- | --- |
| Concept line | Audience, register, the one feeling the artefact leaves | The tie-breaker for every choice the spec does not cover |
| Palette by role | Background, text, heading, accent, highlight, muted, each as a role with a value | Roles survive a brand swap; a list of colours does not say which carries text |
| Type classes | A heading class, a body class, a label class, and a heading-to-body size ratio | Without a ratio, hierarchy is decided slide by slide |
| Layout rules | Margins, alignment, a grid, and one rhythm rule | One rule about pacing (for example, a full-bleed statement after every few content slides) gives variety without chaos |
| Imagery | What images may be, how they are cropped, what they never are | Stops stock-photo filler and invented diagrams |
| Layout catalogue | Named layouts offered as options | Gives a vocabulary without forcing a slot to be filled |
| Density caps | A word cap per slide, a bullet cap, a line-length cap | The assistant fills space up to the cap it is given, and past it when none is given |
| Avoid list | Specific things not to do | Naming a failure is cheaper than describing its opposite |
| Output constraints | Slide count, aspect ratio, language, plain text | The checkable part of the prompt |

## Rules for writing each field

Palette by role, not by name. Write "text on background" and "accent for one emphasised word per slide", then give the value. Every colour that carries text is paired with its background and checked against a contrast ratio of at least 4.5 to 1 for body text and 3 to 1 for large text.

Type by class, not by font file. A notebook assistant may not have the font you name. State a class ("a humanist sans for body, a serif for headings") and a fallback, and keep the ratio explicit: a heading-to-body ratio of about 1.6 to 2.2 reads as hierarchy; below 1.3 it reads as a mistake.

One rhythm rule. Several rules compete and the assistant satisfies the most recent one. Choose the single pacing rule that matters most.

Layout catalogue as options. Write "layouts you may use where the content calls for them" and list five or six with a clause each. Never write "include a key-figure slide" or a fixed running order of named slides; a required slot is a request for filler.

Density caps as numbers the assistant can count: a word cap per slide, a bullet cap, and what to do over the cap (split the slide, never shrink the type).

Avoid list as concrete failures: decorative gradients behind text, more than two typefaces, emphasis by capitals, a closing slide that restates the title, clip-art icons for abstract nouns.

Output constraints in one place. State the slide count as a range, the aspect ratio, and the language once as a single parameter that governs all on-artefact text. Say that slide text is plain text with no markup symbols (no asterisks, hash signs or backticks), because the assistant often echoes the markup it was prompted in.

## A filled example

The values below are parameters of the artefact, such as a size cap. No figure about the sources appears in a spec; those come only from the sources.

```text
Concept line: A review board that distrusts the method sits down with this deck and
leaves certain of exactly where the method stops working. Register: plain, exact,
unhurried. Every claim on a slide is one the sources make.

STYLE
Family: Plain Report.
Palette (roles): background #FFFFFF; text #1F2933; heading #1F2933; accent #1F5C99
(one emphasised phrase per slide at most); highlight #B45309 (a single callout per
slide at most); muted #5F6C7B for captions only.
Type: heading in a clean serif, body in a humanist sans, captions in the body face.
Heading-to-body size ratio about 2 to 1. Body never below the minimum in ACCESSIBILITY.
Layout: left-aligned text, one idea per slide, wide margins. Rhythm: after every run of
content slides, one slide holding a single sentence and nothing else.
Imagery: only figures, tables and diagrams that appear in the sources, redrawn plainly
or described; no stock photography, no people.
Layouts you may use where the content calls for them: title and one statement; claim
with evidence; comparison of two things; table of at most six rows; quotation with its
source; section divider.
Density: at most 40 words per slide, at most 4 bullets, no bullet over 15 words. Over
the cap, split the slide.
Avoid: gradients behind text, more than two typefaces, emphasis by capitals, a closing
slide that repeats the title, icons standing in for abstract nouns.

OUTPUT
Slides: 10 to 14. Aspect ratio 16:9. Language: English, for all text on the slides.
Slide text is plain text; no asterisks, hash signs, backticks or other markup symbols.

GROUNDING
Every number, quotation and named claim comes from the uploaded sources, with the
source and section named in the speaker notes. What the sources do not support is left
out or marked "not stated in the sources". No sample or placeholder figures. No real
people, product mockups or logo walls unless a source supplies them.

ACCESSIBILITY
Body text at least 24 pt and regular weight or heavier; contrast of at least 4.5 to 1
for body text; meaning never carried by colour alone; alt text for every image; reading
order follows the visual order.
```

The slide count, word caps and point size above are the author's choices for that audience; recompute them from step 1 rather than copying them.
