# Auditing charts, diagrams, icons and SVG

Read this at step 3 of `SKILL.md` when the sample contains a chart, diagram, map, infographic, icon set or inline SVG. `wcag22-checklist.md` already gives the thresholds for 1.4.3 and 1.4.11; this file says what to look at in a graphic, which criterion each failure belongs to, and what the fix looks like. A scanner can confirm that an `alt` attribute exists. It cannot tell you whether the text says what the chart shows, whether the series can be told apart without hue, or whether the bars meet 3:1 against the page in dark mode, so every item below is a manual check.

## Contents

- Classify each graphic first
- Text alternatives: 1.1.1
- SVG markup
- Colour: 1.4.1
- Contrast of the graphic itself: 1.4.11
- Text inside the graphic: 1.4.3 and 1.4.5
- Interactive charts
- Motion in animated charts
- Reporting a graphic finding
- What this file was checked against

## Classify each graphic first

The required fix depends on what the graphic is, so label each one before testing it.

| Kind | What it needs | Criteria |
| --- | --- | --- |
| Decorative: a flourish, a divider, a background shape | Hidden from assistive technology so it adds no noise | 1.1.1 |
| Simple informative: a status icon beside text, a single-idea illustration | A short text alternative that says what it means in context | 1.1.1, 1.4.11 |
| Functional: an icon that is the only content of a button or link | A name that describes the action, not the picture | 1.1.1, 4.1.2, 1.4.11 |
| Complex: a chart, diagram, map or infographic | A short alternative plus a long description, ideally with the data as a table | 1.1.1, 1.4.1, 1.4.11 |
| Interactive: a chart with tooltips, filters, zoom or selectable points | Everything above, plus keyboard operation and a visible focus indicator | 2.1.1, 2.4.7, 4.1.2 |

Judge by the purpose in the page, not the file type. The same icon is decorative beside a text label and functional alone in a button.

## Text alternatives: 1.1.1

The Understanding document for 1.1.1 lists a data chart as an example of non-text content whose short label is paired with a longer description that identifies the chart type, summarises the data, trends and implications, and gives the actual data in a table where that is practical. W3C's Complex Images tutorial calls this a two-part alternative: a short description that identifies the image and says where the long description is, and a long description that is a textual representation of the essential information. Check both parts.

| Check | A failure looks like |
| --- | --- |
| The short alternative identifies what and where | `alt="chart"`, the file name, or a repeat of the caption word for word |
| The long description carries the information, not a restatement of the title | "A line chart of sales" with no values, trend or comparison |
| The data is available as a table where practical | A twelve-series chart with only a prose summary, so exact values are unreachable |
| The long description is reachable by everyone who needs it | A description behind a hover, or a link that exists only for a screen reader |
| The surrounding text points at what the chart shows | A chart dropped in with no sentence that states the finding |

Where the description lives matters. W3C's tutorial notes that content referenced by `aria-describedby` is read as one continuous paragraph: screen readers do not expose headings or tables inside it. Use `aria-describedby` only for a description that is plain text. Put a data table in the page beside the graphic, in a `figcaption` or a section the short alternative names, so its structure survives. Showing the description to everyone is also the more robust choice, because it helps people who find a complex chart hard to read, not only people who cannot see it.

When the chart already has visible labels and values for everything it shows, a shorter alternative can be enough. Judge that against the test in 1.1.1: the text must serve the equivalent purpose, and the user must be able to get the same information.

## SVG markup

For an inline SVG chart that is a single informative image, the pattern to look for is:

```html
<svg role="img" aria-labelledby="c1-title" aria-describedby="c1-desc" viewBox="0 0 400 240">
  <title id="c1-title">Monthly visitors, sites 1 to 3, first quarter</title>
  <desc id="c1-desc">Visitors to site 1 fall each month, site 2 stays level and
    site 3 rises. The values are in the table below the chart.</desc>
  <!-- bars, lines, axes -->
</svg>
```

What to verify, and why:

- **A name exists.** The WAI-ARIA `img` role requires an accessible name, supplied by `aria-label` or `aria-labelledby`. An `<svg role="img">` with neither is a graphic that exposes nothing useful.
- **`aria-labelledby` and `aria-describedby` point at `<title>` and `<desc>`.** SVG-AAM computes a name from `aria-labelledby`, then `aria-label`, then a direct child `<title>`, and a description from `aria-describedby`, then a direct child `<desc>`. Its note says that current best practice for fallback browser support is to link to the `<title>` and `<desc>` children redundantly with `aria-labelledby` and `aria-describedby`. Treat a bare `<title>` without the links as a lead to test with a real screen reader and browser, not as an automatic pass or fail.
- **The `id` values resolve and are unique.** Several charts on one page copied from the same template often share `id="title"`. The second chart then names itself after the first.
- **`<desc>` is plain text.** SVG-AAM records, as an open issue, that structured content inside `<desc>` is not exposed as navigable structure. Do not accept a table or list inside `<desc>`.
- **Children are presentational.** The `img` role has presentational children, so user agents should not expose anything inside it. A text label, a link or a focusable point inside an `<svg role="img">` is invisible to a screen reader. That is correct for a static chart whose description carries the data, and wrong for an interactive one (see below).
- **Decorative SVG is hidden.** An ornamental icon or divider carries `aria-hidden="true"` and is not focusable, so it adds no stop for assistive technology.
- **Icon-only controls are named on the control.** For a button that contains only an SVG, the name belongs on the button, as visible text, `aria-label` or visually hidden text. The icon inside is then decorative.

Check the result in the browser's accessibility tree and with a screen reader before reporting. SVG-AAM is an editor's draft and support varies between browser and reader pairs, so say which pair you tested.

## Colour: 1.4.1

1.4.1 Use of Color asks that colour is not the only visual means of conveying information, indicating an action, prompting a response or distinguishing a visual element. Charts fail it more often than any other kind of content, because series, categories and states are separated by hue.

Test it by looking at the graphic with the colour removed, using a greyscale filter or a vision simulation in browser developer tools, and asking whether you can still tell the series apart, read the legend and see which point is selected or in an error state.

| Where it fails | A fix at the right place |
| --- | --- |
| Lines distinguished only by hue | Add a second visual cue: a dash pattern, a marker shape per series, or a direct label at the end of each line |
| Bars or slices distinguished only by fill colour | Add pattern fills, or direct labels with values on or beside the shape |
| A legend that is a row of colour swatches | Pair each swatch with a marker or pattern that matches the series, or label the series in place |
| Good or bad shown as green or red alone | Add an icon, a sign or a word |
| A selected point or active series shown by a colour change alone | Add size, an outline or a label |

W3C's Understanding document for 1.4.1 says that colours differing in lightness as well as hue count as an additional visual distinction when their contrast ratio is at least 3:1, and that content which relies on accurately perceiving a particular colour, such as a green or red outline for valid or invalid, still needs another visual indicator whatever the ratio. Use that when a design cannot take patterns: check the lightness difference between neighbouring series by measurement, not by eye.

1.4.1 requires a visible alternative. Exposing the same information to a screen reader through the long description does not clear this criterion, because the users it protects do not necessarily use assistive technology. Report the colour failure under 1.4.1 and the missing description under 1.1.1, as separate findings.

## Contrast of the graphic itself: 1.4.11

1.4.11 Non-text Contrast requires 3:1 against adjacent colours for the parts of graphics required to understand the content, and for the visual information needed to identify interactive components and their states. For a chart, work out which parts count before measuring.

1. List the graphical objects the reader must see to understand the chart: lines, bars, slices, markers, and any gridlines needed to read a value.
2. For each, find the adjacent colour: the page or panel behind a bar or line, or the neighbouring slice for the edge of a pie.
3. Take the colour values from the stylesheet or the computed `fill` and `stroke`, not from a screenshot. The Understanding document says to use the colours from the markup or user agent, because anti-aliasing can make thin shapes look fainter than their defined colour. It encourages avoiding very thin lines and shapes or exceeding the minimum.
4. Where the object has a gradient or several colours, test the least contrasting area. If that is under 3:1, imagine that area removed and ask whether the graphic can still be understood.
5. Do not round. The Understanding document treats 3:1 as a threshold, so 2.999:1 does not meet it.

What does not need 3:1:

- Parts that duplicate information given in text. The Understanding document says a graphic with visible labels and values conveying the same information does not need its shapes to meet 1.4.11, and its pie chart example is marked not applicable when the slices carry visible labels and values. The same pie chart, with labels but with slices you must tell apart to read the proportions and with slice contrast under 3:1, is marked as a failure.
- Information available in another form that is really offered, such as a table that follows the graph.
- Graphics whose particular presentation is essential. The document gives flags, screenshots and heat maps as examples. Do not extend this to ordinary bar or line colours, which can nearly always be changed.
- Decorative graphics.

Adjacent colours inside the chart count too. Neighbouring slices, stacked bars and overlapping areas that need to be told apart need 3:1 against each other, or a border that does the work, as in the document's pie chart where a darker border around the yellow slice makes the pass. Lines that rarely overlap do not need to contrast with each other or with the gridlines, according to the document's graph example, but the lines still need 3:1 against the background.

For interactive charts, the Understanding document says that the default, unfocused version must already have sufficient contrast for someone to know the graphic exists. Hover or focus can then add contrast or reveal values. It does not require every hover change to meet 3:1, but the focus indicator and any selected-state cue must.

### Both themes

A palette that passes on a light surface does not pass on a dark one because it came from the same token set. Re-measure every series colour, gridline that carries meaning and marker against the dark surface, and against any panel or card background the chart sits on. Look for colours that were lightened for dark mode and now fail against each other, and for series that pass on white and disappear on a dark card. Fix it in the chart palette tokens, once, and list every chart that uses them.

## Text inside the graphic: 1.4.3 and 1.4.5

Axis labels, tick labels, data labels, legends and annotations are text, so 1.4.3 applies: 4.5:1, or 3:1 for large-scale text (at least 18 point, or 14 point bold). The Understanding document for 1.4.3 states that its scope is text and that charts, graphs and diagrams are otherwise covered by 1.4.11.

- Measure labels placed inside bars or slices against the fill behind them, not the page. Labels that sit across a series boundary need the worse case.
- Grey tick labels and axis titles are the usual failure, set in a muted colour to push them back visually.
- Text that is only decoration has no requirement, but chart labels are not decoration.
- Text that has been flattened into an image, such as an exported chart in PNG form, falls under 1.4.5 Images of Text as well. Prefer live text in SVG or HTML, so the user can restyle and resize it. Report a PNG chart with its text baked in, and fix it by rendering the text as text.
- Text set so ornately that it reads as a symbol is treated as non-text content, and then 1.4.11 applies to it.

## Interactive charts

Where hover shows values, filters change series or the user can zoom, test these:

- **Operable from the keyboard (2.1.1 Keyboard).** Hover-only tooltips are the common failure. The Understanding document does not require every mouse-operable control to be focusable, only that keyboard users can perform the same or comparable actions. A focusable data table or a list of the points is an acceptable route, and often a better one than making every bar a tab stop.
- **Focus is visible (2.4.7 Focus Visible).** Check the indicator on custom points and controls, in both themes. An author-styled indicator must also meet 3:1 under 1.4.11, while the user agent default on an unmodified control is exempt.
- **Name, role and value (4.1.2).** A custom control built from SVG shapes needs a name and a role, and its state, such as selected, must be programmatically determinable. This conflicts with `role="img"` on the container, because the children of `img` are presentational. For a chart with focusable or labelled parts, use a container whose semantics allow children, and give each operable part its own name. Record the pattern the chart actually uses and test it with a screen reader.
- **Values reachable without a pointer.** Anything a tooltip reveals must also be reachable on focus, or be in the table.
- **Filter and zoom controls** are ordinary controls: name, state, target size (2.5.8) and, for drag-to-zoom or brush selection, a non-dragging alternative (2.5.7).

## Motion in animated charts

- A chart that animates in on load and runs for more than five seconds, alongside other content, falls under 2.2.2 Pause, Stop, Hide (Level A): it needs a way to pause, stop or hide it. The criterion applies to moving, blinking or scrolling content that starts automatically, lasts more than five seconds and is presented in parallel with other content, unless it is essential.
- A live chart that refreshes on its own is auto-updating information. 2.2.2 has no five-second exception for it: the user needs to pause, stop or hide it, or control the frequency of the update, unless the updating is essential.
- Animation that a user's interaction triggers, such as a transition when switching a series or range, is 2.3.3 Animation from Interactions (Level AAA), so advisory when the target is AA. The Understanding document gives three ways to meet it: avoid unnecessary animation, give a control that turns it off, or honour the reduce-motion setting of the user agent or operating system. Technique C39 uses the `prefers-reduced-motion` media query for the third.
- To test, turn on the system reduced-motion setting, reload and interact with the chart. The entry animation, the transitions and any auto-refresh should stop or reduce. If the chart is drawn by a script, check that the script reads the preference, because the CSS media query does not reach animation driven from script.

## Reporting a graphic finding

Report the defect at the chart component or palette token, and list every chart it covers. Use the finding format in `wcag22-checklist.md`, with the criterion number, title and level copied from the standard. Two examples of the shape:

```text
[Serious] Series in the revenue chart are distinguished by hue only
Criterion: 1.4.1 Use of Color (A)
Where: components/Chart/palette.ts, used by 9 charts
Found by: greyscale simulation; the three lines are indistinguishable
Impact: a user who cannot tell the hues apart cannot match a line to its legend entry.
Fix: add a marker shape and end-of-line label per series in the chart component.
Retest: greyscale view of each chart; confirm the series can be matched to the legend.
```

```text
[Serious] Bar fill in the dark theme is under 3:1 against the card background
Criterion: 1.4.11 Non-text Contrast (AA)
Where: dark theme tokens, chart-series-2, used by 4 charts
Found by: measured fill against the card background in the dark theme
Impact: the second series is hard to see for a user with low vision, and the chart has no value labels.
Fix: darken or lighten the token to reach 3:1, or add value labels, in the token file.
Retest: re-measure all series in both themes; rerun the page in dark mode.
```

Severity follows what the user loses. A complex chart with no text alternative and no table is a blocker for a screen reader user whose task depends on the data. A series that fails by hue alone while the same numbers sit in an adjacent table is moderate.

## What this file was checked against

The criteria were read in the Understanding documents and normative text of WCAG 2.2, the Complex Images tutorial in W3C WAI's Images tutorials, SVG Accessibility API Mappings (an editor's draft) and WAI-ARIA (the `img` role). The checks used the source files in the `w3c/wcag`, `w3c/wai-tutorials`, `w3c/svg-aam` and `w3c/aria` repositories on GitHub, because the published pages at `www.w3.org` and `w3c.github.io` could not be reached from the environment this was written in. Those pages are built from the same files, but a published page can differ from a later edit, so confirm a number or a threshold at the published page before quoting it in a report.

- <https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html>: 1.1.1, the data chart example, short and long alternatives.
- <https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html>: 1.4.1, the lightness exception and the green or red outline case.
- <https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html>: 1.4.11, graphical objects, the pie chart and graph examples, testing principles.
- <https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html>: 1.4.3, large-scale text and the pointer to 1.4.11 for charts.
- <https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html> and <https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html>: 2.2.2 and 2.3.3.
- <https://www.w3.org/WAI/WCAG22/Understanding/keyboard.html>: 2.1.1 and the comparable-actions reading.
- <https://www.w3.org/WAI/tutorials/images/complex/>: two-part alternatives, and the plain-text limit of `aria-describedby`.
- <https://www.w3.org/TR/svg-aam/>: name and description priority for `<title>`, `<desc>` and the ARIA attributes, and the redundant-linking note.
- <https://www.w3.org/TR/wai-aria/>: the `img` role, its required name and its presentational children.
- <https://www.w3.org/WAI/WCAG22/Techniques/css/C39>, <https://www.w3.org/WAI/WCAG22/Techniques/general/G111> and <https://www.w3.org/WAI/WCAG22/Techniques/general/G207>: reduced motion, colour and pattern, and 3:1 for icons.
