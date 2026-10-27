# Style families

Read this at step 3. Choose by audience and content density first. A family is a starting point for the spec, written as roles so a supplied brand can replace the values without changing the structure. The values are examples: each text and background pair listed here has a contrast ratio above 4.5 to 1, and any replacement needs the same check.

How to read an entry: **Suits** names the audience and content; **Palette** gives role then example value; **Type** is a pairing class, not a font file; **Density** is the per-slide word cap to put in the spec; **Avoid** goes into the avoid list.

## 1. Plain Report

- **Suits:** research reviews, technical results, a sceptical or expert audience, high content density.
- **Palette:** background #FFFFFF; text #1F2933; accent #1F5C99; highlight #B45309.
- **Type:** serif headings over a humanist sans body.
- **Density:** up to 45 words per slide, 4 bullets.
- **Avoid:** decorative imagery, colour as the only signal, more than one callout per slide.

## 2. Editorial Serif

- **Suits:** argument-led narratives, essays turned into decks, an audience that reads.
- **Palette:** background #FAF6EF; text #2B2623; accent #8A2D2D; highlight #5B6B4F.
- **Type:** high-contrast serif headings, a book serif body.
- **Density:** up to 40 words, long pull-quotes allowed at 30 words alone on a slide.
- **Avoid:** bullet stacks, sans-serif captions mixed with serif body, red used for both emphasis and warning.

## 3. Technical Blueprint

- **Suits:** systems, architecture, processes with parts; engineering audiences.
- **Palette:** background #F3F6FA; text #16202C; accent #0B5CAD; highlight #C2410C.
- **Type:** geometric sans headings, a monospace class for identifiers only.
- **Density:** up to 35 words plus one diagram description.
- **Avoid:** monospace for body text, grid lines behind text, invented component names.

## 4. Warm Workshop

- **Suits:** teaching, onboarding, informal sessions; a mixed-experience audience.
- **Palette:** background #FFF8EC; text #33291F; accent #B4470F; highlight #2F6F5E.
- **Type:** rounded humanist sans headings and body.
- **Density:** up to 30 words, one question per slide at most.
- **Avoid:** cartoon clip-art, handwriting fonts for body text, more than one accent per slide.

## 5. Data Slate

- **Suits:** number-heavy material shown on a screen in a dim room; analysts.
- **Palette:** background #14181F; text #EEF1F5; accent #6CB6FF; highlight #F2B84B.
- **Type:** neutral sans with tabular figures for numbers.
- **Density:** up to 35 words plus one table of at most six rows.
- **Avoid:** pure white text on pure black, red and green as the only difference between two series, shadows.

## 6. Clinical Light

- **Suits:** health, regulated and safety material where restraint signals care.
- **Palette:** background #FFFFFF; text #22303C; accent #0F6B74; highlight #8B3A62.
- **Type:** clear sans throughout, a single weight step for emphasis.
- **Density:** up to 40 words; any caveat stated on the slide it qualifies.
- **Avoid:** stock images of people, alarm colours without a text label, rounded decorative shapes.

## 7. Poster Bold

- **Suits:** short pitches and kickoffs where one idea per slide is the point; low content density.
- **Palette:** background #111111; text #FFFFFF; accent #FFD43B; highlight #FF6B6B.
- **Type:** heavy condensed sans headings, a plain sans body used sparingly.
- **Density:** up to 15 words per slide; no bullets.
- **Avoid:** more than one accent colour on a slide, small captions, any slide the sources cannot fill without padding.

## 8. Archive Paper

- **Suits:** history, humanities, source-heavy material built on quotations.
- **Palette:** background #F1EADB; text #2A2418; accent #7A2E1B; highlight #3F5A45.
- **Type:** old-style serif headings and body, small caps for labels.
- **Density:** up to 50 words; a quotation always shows its source on the same slide.
- **Avoid:** faux-aged textures behind text, ornamental borders, quotations shortened without an ellipsis.

## 9. Civic Plain

- **Suits:** public bodies, mixed-ability audiences, material that must meet strict accessibility expectations.
- **Palette:** background #FFFFFF; text #000000; accent #00508A; highlight #8F2D00.
- **Type:** an open-aperture sans with large sizes; headings bold, body regular.
- **Density:** up to 30 words, body at least 28 pt.
- **Avoid:** colour-only status, text over images, abbreviations not defined on first use.

## Mapping a brand onto a family

Fill the same roles from the brand's own colours, type families and logo rules, then run the contrast check on every pair that carries text. Where a brand colour fails as text on its intended background (a pale accent on white is the usual case), keep it for non-text shapes and substitute the family's accent for text, and tell the user which colour was substituted. Logo rules go into the spec as constraints (clear space, minimum size, one placement), and the logo appears only if the user supplied it.
