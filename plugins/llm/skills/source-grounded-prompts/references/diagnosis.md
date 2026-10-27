# Diagnosis and revision

Read this at steps 7 and 8. Start from the symptom in the output, find the likely cause in the prompt, make one change, and run again.

## Symptom, likely prompt cause, change

| Symptom | Likely prompt cause | Change |
| --- | --- | --- |
| A number in the artefact appears in no source | No grounding block, or one that does not say placeholder figures are forbidden | Add the grounding block; say anything unsupported is left out or marked as absent |
| The same invented number appears on many slides | A sample figure in the spec leaked | Remove every example value from the spec and describe the format in words |
| A quotation reads well but is not in the sources | The prompt asks for a quote per slide, or for "voice" | Ask for a quotation only where a source holds one; require it to name the source and section |
| A citation names a section that does not say that | The assistant cites from memory of the sources | Require the exact passage in the speaker notes, then check it against the text |
| Slides are walls of text | No density cap, or a cap stated as a goal ("concise") | Give a word cap per slide and say what to do over it |
| Every slide has a filler statistic or generic icon | A mandatory layout with a slot for it | Turn the catalogue into options and drop the slot |
| Slides look like different decks | Palette or type given as a list, no roles, no ratio | Restate the palette by role and add the heading-to-body ratio |
| Text contains asterisks or hash signs | The spec was written in markup and the assistant echoed it | Ask for plain text with no markup symbols, once, in the output constraints |
| Some text is in the wrong language | The language rule is repeated and the repeats differ, or is missing | State one language parameter in the output constraints and delete the others |
| Brand colour text is hard to read | A brand colour used for text without a contrast check | Check each pair; substitute the family's text colour and keep the brand colour for shapes |
| The artefact is too long or too short | The count was never derived from the sources | Recompute the length budget from step 1 and state it as a range |
| Facts are right but the tone is wrong | The concept line is missing or names no register | Rewrite the concept line with audience, register and feeling |
| A figure is present in the sources but used for something else | The check is lexical and found the number | Read the slide against the source section; reword the claim and cite the section |
| Audio script is dense with numbers | No cap on numbers per turn | Add the per-turn number cap from `references/artefact-types.md` |

## The revision loop

1. Keep the current prompt and its output, labelled with the run number.
2. Run the checker and read the slides. Write the symptoms down as a list, worst first.
3. Pick the symptom the most other symptoms depend on. Invented figures come before density, density before polish.
4. Find the row above and make that one change. Do not touch the concept line, the palette or the caps in the same run.
5. Run again on the same sources, and compare the two outputs against the same list.
6. If the symptom went and nothing new appeared, keep the change. If something new appeared, revert it and try the next cause for the same symptom.
7. Stop when the checker exits 0, the density caps hold on a read of every slide, and nobody can name a symptom worth another run. Record anything the checker could not decide as unverified.

## Reading the checker's report

An unsupported number is one of: invented, from another document the sources do not include, a rounding or a change of unit (the source says "1.2 million" and the slide says "1,200,000": the checker matches tokens, so this is reported and a person confirms it is the same figure), or a derived figure the assistant computed. A derived figure is a claim; either show the sources it came from in the notes, or leave it out.

An unsupported quotation is one of: invented, paraphrased and put in quotation marks, or taken from a source whose text was not exported with the others. Check the third before deleting.

What the checker covers:

- Every figure it can extract, matched as a whole token after formatting is folded away (thousands separators, `%`, `percent`, `per cent`, case, dash styles). A figure is a number with its sign, currency symbol (`$ € £ ¥ ₹` and similar) and any unit attached with no space: `%`, a degree mark, or letters of any length that may carry digits after the first letter (`3x`, `40ms`, `250k`, `100Mbps`, `18months`, `m²` read as `m2`, `1h30`, `4K60`), not an ordinal (`3rd`). A plus-minus sign counts as a sign: `±3%` is not `3%`.
- A scale word after a number (`thousand`, `million`, `billion`, `trillion`) is folded into the figure as `k`, `m`, `bn`, `tn`, so `$4.2 million` matches `$4.2M` and does not match `$4.2 billion`.
- A range, fraction, date, dimension, exponent or dotted number is one figure: `5-10%`, `3/4`, `2024-05-12`, `12/05/2024`, `1920x1080`, `1e6`, `1.2.3`, `.5`. The two ends of a range in a source count as supplied, with a unit written once applying to both.
- Every span in double quotes, curly single quotes or straight single quotes outside a word, at or above the quote threshold, matched on whole words and followed across line breaks inside one paragraph. A double quote directly after a digit (`27"`) is read as an inch mark and cannot open a span; an apostrophe before a decade (`'90s`) cannot either.
- Bracketed text is read as a claim, link text is read and link addresses are not. A bracket is dropped only when it holds nothing but one or more file names with an optional locator (`[paper.md]`, `[paper.md, section 2.3]`, `[paper.md#intro]`), a numbered reference (`[2]`, `[1, 2]`) or a labelled one (`[source 2]`, `[p. 14]`). `[45% of users, survey.md]` is a claim and is checked. Brackets in a source are never removed.

Not reported, and left to the read:

- a figure that appears in the sources but means something else on the slide;
- a unit or noun written after a space or a hyphen, which is not compared: `12 days` passes against `12 weeks` and `12-month` against `12 months`; a currency code is not part of the figure either (`5 USD` and `US$5` both read as `5`), and a time such as `10:30` is read as `10` and `30`;
- a number glued to a letter or a hyphen before it, which is not extracted: `Q3`, `v2`, `v1.2.3`, `growth-45%`, `pre-2020`; and a list marker or slide label, which are dropped on purpose: one or two digits followed by a full stop or bracket at the start of a line (`7.`, `12)`), so a hard-wrapped line that happens to begin `7.` loses that number (three or more digits are kept), and `slide N` or `slides N-M` unless a unit, letter or decimal follows (`slides 12%` is a figure; `slides 12 points` and `slide 3` are dropped);
- the same figure spelled another way, which is reported as unsupported and confirmed by a person: `1.2 million` against `1,200,000`, `4-6 million` against `4 million to 6 million`, `40 ms` against `40ms`, `12 percentage points` against `12%`, `-45%` against `45%`, `±3%` against `3%`, `20°C` against `20 degrees`, a spelled-out number such as `twelve`; a bare `5m` is the same figure whether it means metres or millions;
- a decimal comma or a number grouped with spaces, which is split and can pass silently: `2,5%` is read as `2` and `5%`, so it passes when the sources hold both, and `1 200 000` is read as three numbers; a sign followed by a space (`± 3%`) is not part of the figure either, so it passes against `3%`;
- quotations shorter than the quote threshold and a quotation that wraps across a blank line;
- a quote mark inside a quotation (an inch mark, a plural possessive apostrophe, an unpaired mark): it can end the span early or pair a later mark with the wrong one, within the same paragraph, and a paragraph break resets the pairing;
- a paraphrased claim with no number, and any image.
