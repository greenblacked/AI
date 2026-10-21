# Choosing the chart

Read this in step 2 of the workflow, and again when a chart is being rejected as misleading. Start from the question the reader brings, then check the data's shape fits.

## The table

| The reader's question | Data shape | Chart | Watch for |
| --- | --- | --- | --- |
| How big is each, and which is largest? | One category column, one number | Bars, horizontal when labels are long, sorted by value | Zero baseline; alphabetical order hides the ranking |
| How did it change over time? | Time column, one or more numbers | Line, time on the x axis | One line per series, labelled at the end; a gap in the data is a gap in the line |
| How did it change over a few periods, with totals that matter? | A handful of periods | Bars, one per period | Zero baseline; too many periods turns it into a line |
| What is each part of the whole? | Parts that sum to a total | Stacked bar, or one 100 per cent bar; a pie only when the point is that one part is about half or nearly all | Only the bottom segment of a stack shares a baseline, so keep the segment being compared at the bottom |
| How are the values spread? | One number, many rows | Histogram, box plot, or the points themselves (strip or dot plot) when there are few rows | Bin width changes the shape; show the rows when there are too few to bin |
| Do two numbers move together? | Two numeric columns | Scatter | Overplotting: use transparency or bin the points. Add a fitted line only if the claim needs it |
| How did each item change between two moments? | Category, before, after | Slope chart or dumbbell (dot plot) | A dot plot need not start at zero; bars must |
| How far is each from a reference? | Category, value, reference | Bars diverging from the reference | The reference line is the baseline; label which side is good |
| Where is it? | Values by place | Map only when location is the point; otherwise a sorted bar | A filled region encodes by area, so large empty regions dominate |
| What is the one number? | A single value | The number, large, with its comparison | A gauge spends ink on an angle where text would do |
| What are the exact values? | A handful of numbers, or lookup | A table | Align numbers on the decimal point; sort by what the reader looks up |
| How do two categories combine? | Two category columns, one number | Heatmap with the value printed in each cell, or grouped bars when there are few categories | A heatmap's light end approaches the background, so print values in the cells |

When two rows fit, take the one higher in the encoding list below.

## Encodings ranked by how accurately readers judge them

From most to least accurate, following Cleveland and McGill, "Graphical Perception: Theory, Experimentation, and Application to the Development of Graphical Methods", Journal of the American Statistical Association, 1984:

1. Position along a common scale (bars from one baseline, points on shared axes)
2. Position along non-aligned scales (the same axis repeated in separate panels)
3. Length, direction and angle
4. Area
5. Volume, curvature, and shading or colour intensity

Two consequences. A pie chart asks the reader to compare angles where a bar chart asks them to compare positions, and a bubble chart asks them to compare areas where a scatter plot asks for positions. Use the weaker encoding for a third variable that you accept the reader will estimate only roughly, never for the variable the finding depends on.

## When a second measure seems to need a second axis

Pick the alternative that fits, in this order:

1. Two panels stacked, sharing the x axis. Each measure keeps its own honest axis and the shared time reads straight down.
2. Index both series to 100 at a common start, so the reader compares change in the same unit on one axis. State the base period.
3. One axis, with the second series labelled directly, when the units are the same or convertible.
4. A scatter of one measure against the other, when the question is whether they move together rather than how each moved.

If a dual axis is demanded anyway, give each axis the colour of its series, label the series on the lines, and begin both at zero unless the data sits far from it. Say in the note that the crossing point is arbitrary.

## 3D and decoration

Do not use a 3D bar, pie or surface chart for data that has two or three variables. The third dimension is spent on perspective, which changes how long a bar looks depending on where it sits, and it encodes nothing. If there are three variables, use position for two and a small multiple, a colour or a size for the third. Drop shadows, gradient fills and background images for the same reason: ink that carries no data competes with ink that does.

## How many series

There is no fixed ceiling, but each series past the few the eye can follow without a legend costs a look-up. When the series outnumber what the palette carries (see `palettes.md`), choose one: highlight the series the finding is about in colour and draw the rest in grey, split into small multiples with shared scales, or aggregate the tail into "other" and say what it holds.
