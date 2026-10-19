# Tables and charts

Read this at step 4 when the document contains a table or a chart. Both look like data and are structure and drawing, and each has a way of producing a confident wrong answer that the field-level checks do not see.

## Tables

The cell-level format is in `references/extraction-schema.md`. The checks that go with it:

1. Coverage. Every grid position from `0..n_rows-1` by `0..n_cols-1` is covered by exactly one cell once spans are expanded. A gap or an overlap means a cell was dropped or a span was misread, and every value after it is suspect.
2. Count against the page. Count the printed rows and columns yourself, on a crop, or take the count from the text layer, and compare with `n_rows` and `n_cols`. Do not let the extraction be the only source of its own dimensions.
3. Column arithmetic. Sum each numeric column and compare it with a printed totals row, and check any row whose cells relate (quantity, price, amount).
4. Header alignment. Each numeric column has a header cell above it whose span covers it. A value under the wrong header is the usual outcome of a merged cell, and the sums will often still look reasonable.
5. A second reading. For a born-digital PDF, extract the table from the text layer with a library such as pdfplumber (`extract_tables` returns rows of cells; https://github.com/jsvine/pdfplumber) and compare it cell by cell. For a scan, use an OCR pass and compare the text of each cell, or re-extract the table a row band at a time.

Common failures to look for:

- A merged header read as one column, shifting the values below it.
- A wrapped cell read as two rows, or two rows read as one wrapped cell.
- A row across a page break read as two tables.
- A dash, blank or "n/a" read inconsistently: keep the printed text, decide the meaning in a later pass.
- A thousands separator read as a decimal point, so that a column mixes scales.

Do not flatten a table into Markdown or CSV between the reader and the checks. If a consumer needs CSV, derive it from the verified cells at the end, and repeat any merged-cell content explicitly rather than leaving the cell blank.

## Charts

A chart states some of its numbers and implies the rest. The model can produce a precise-looking value for a bar that the chart never printed, and nothing about the output marks it as an estimate.

Return a chart value only when it ties to something the chart prints:

- A data label on the bar, point or slice.
- A value that sits on an axis tick or a gridline, so that the position and the printed tick agree.
- A value in an accompanying table, caption or note on the same page.

Otherwise the value is `null`, with a `confidence_basis` that says the chart prints no value for it. A bar that falls between two ticks has no value the document asserts.

If the caller explicitly wants approximate reads, put them in a field named `estimate`, separate from `value`, with the axis calibration used (the two ticks measured and their pixel positions) and an uncertainty stated in the units of the axis. An estimate is never written into a column that downstream code treats as a stated value. Say plainly in the output that the figure is read from the drawing.

Checks for a chart:

1. Read the axis first: its label, unit, scale (linear or log), whether it starts at zero, and the tick values. Record these as fields, because a misread unit or a truncated axis changes every value.
2. For each printed label, confirm that it belongs to the mark it sits on. Labels can be offset or can collide, and a legend can swap two series.
3. Where the chart gives labels and a total (a pie chart in percentages, a stacked bar with a printed total), check that the parts sum to the whole.
4. Where the same figures appear as text in the document, prefer the text and use the chart only to confirm.
5. Where the chart has dual axes, record which axis each series uses.

Measure your own pipeline on charts like the ones you will process before relying on any published figure, as `references/verification.md` sets out.

## Screenshots and forms

A screenshot is a document with no printed totals to cross-check, so the second reading carries the weight: OCR the same region and compare. For a form, read each field's printed label and its value separately, record the label so a reviewer sees which box was read, and treat a checkbox you cannot see clearly as `unclear` rather than unchecked.
