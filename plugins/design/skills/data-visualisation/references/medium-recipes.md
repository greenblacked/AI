# Recipes by medium

Read this when building the chart. Each section covers the same five points: pin the baseline, label directly, apply the palette, attach the text alternative, and render a PNG you can read back in step 7. The rules do not change between media; only the spelling does.

A zero baseline means the value axis includes 0 and both extremes of the data, not that 0 is always its minimum: when the data has negative values, the lower bound is the smallest value, and the bars hang below the zero line. Each recipe below keeps both.

Every medium below takes the colours from `palettes.md`. Set them explicitly, per theme, instead of trusting a library default.

## matplotlib

- Baseline: after plotting, `lo, hi = ax.get_ylim(); ax.set_ylim(min(lo, 0), max(hi, 0))` for vertical bars (the same with `get_xlim` and `set_xlim` for horizontal). `ax.bar` draws from 0 by default (`bottom` defaults to 0), but autoscaling can still change the limits when other artists are added, so pin it and check it in step 7. `set_ylim(bottom=0)` is the same only for data with no negative values; with any, it clips those bars out of the chart.
- Direct labels: `ax.bar_label(container, fmt="%g")` on the `BarContainer` that `ax.bar` returns, and widen the axis limit so labels fit, since the method does not. For lines, `ax.annotate` or `ax.text` at the last point, with a small offset, in the series colour. Do not call `ax.legend()` when every series has a label.
- Palette: set `axes.prop_cycle` from the table for the theme, as in `plt.rcParams["axes.prop_cycle"] = cycler(color=[...])`. The default cycle is `tab10`, which is not the palette in `palettes.md`.
- Dark variant: `plt.style.context("dark_background")` flips the text, axes and background, and it does not choose your series colours, so apply the dark-theme colours yourself.
- Text alternative: matplotlib writes an image file, so the alternative lives in the document that embeds it: the `alt` text on the image, a caption, and the table beside it.
- Render: `fig.savefig("chart.png", dpi=200)`, then Read the file.

## Vega-Lite

- Baseline: `"scale": {"zero": true}` on the quantitative axis encoding. Vega-Lite's documented default is `true` for x and y when the field is quantitative, not binned and has no custom `domain`; a custom domain turns the default off, so set it explicitly whenever you give a domain. It does not apply to log, time or UTC scales.
- Sort: `"sort": "-y"` on the nominal axis sorts by the value, descending.
- Direct labels: a second layer with a `text` mark placed at each bar end or the last point of a line. Remove the legend with `"legend": null` in the colour encoding.
- Palette: `"scale": {"range": ["#009E73", "#0072B2", ...]}` on the colour encoding, or the same list in the config.
- Text alternative: the top-level `description` property holds a short description of the chart. Put the longer description and the data table in the page that embeds the chart.
- Render: the `vl-convert` package (`import vl_convert as vlc; vlc.vegalite_to_png(spec, scale=2)`) writes a PNG without a browser.

## Plotly

- Baseline: `fig.update_yaxes(rangemode="tozero")`. The attribute's default is `normal`, which computes the range from the data's extremes; `tozero` extends it to 0 whatever the data is. It applies only to linear axes.
- Direct labels: `text=` on the trace with `textposition` for bars, and an annotation at the last point for lines; set `showlegend=False` once the marks are labelled.
- Palette: `layout.colorway` takes the list of colours and sets the default trace colours.
- Text alternative: Plotly figures carry no alt-text field of their own that this skill has verified; put the alternative, the long description and the table in the embedding page.
- Render: `fig.write_image("chart.png")` needs Kaleido, which in version 1.0.0 or later looks for a Chrome or Chromium already on the machine. If that is not installed, say so and fall back to checking the figure's data and layout with `fig.to_dict()`, and report that the image was not read.

## D3

- Baseline: `d3.scaleLinear().domain([Math.min(0, d3.min(data, d => d.value)), Math.max(0, d3.max(data, d => d.value))])` for the value scale of bars. Taking the domain from `d3.extent` alone leaves 0 out whenever every value has the same sign, and fixing the lower bound at 0 drops the negative bars.
- Direct labels: append `text` elements positioned from the same scales as the marks, so the labels move with the data. Skip the legend.
- Palette: pass the colour list to an ordinal scale, `d3.scaleOrdinal(domain, range)`.
- Text alternative: put `<title>` and `<desc>` elements as the first children of the root `<svg>`, with `role="img"` and `aria-labelledby` pointing at them, and put the table in the page.
- Render: open the page in a headless browser and screenshot it, then Read the PNG. The code runs without error whatever the picture looks like.

## Spreadsheet

- Baseline: set the vertical axis minimum by hand for bar and column charts, to 0, or to just below the smallest value when the data has negative values. Some applications start the automatic axis above 0 once the data sits far from it, so do not rely on the automatic setting.
- Direct labels: turn on data labels for bars and delete the legend; for lines, label the last point with the series name.
- Palette: set each series colour by hex value. The default chart styles are not the palette in `palettes.md`.
- Text alternative: use the application's alt-text field on the chart, and keep the source range on the sheet as the data table.
- Render: ask for a screenshot or an exported image of the chart and Read it. If you cannot see the chart, you cannot do step 7; say so.

## Choices that apply in every medium

- Size the text for the size the chart will be shown. A label that is legible at full width and a smudge in the half-width slot of the report has failed.
- Export the same rows as a CSV beside the chart, so the table and the marks come from one source.
- Keep one script, or one sheet, that produces the light and dark variants from the same data and a per-theme colour map, so the two cannot drift apart.
