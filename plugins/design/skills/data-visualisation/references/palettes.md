# Palettes and contrast

Read this in step 4 of the workflow. Colour is a second channel; it never carries a distinction alone. The three jobs are different, so use a different palette for each: categorical (which series), sequential (how much), diverging (how far from a midpoint).

## Categorical: Okabe-Ito

Okabe and Ito designed this set of eight as a "Color Universal Design" palette, one meant to be told apart by readers with colour-vision deficiency. The hex values below match the `palette_OkabeIto_black` vector in the `colorblindr` R package, which takes them from Okabe and Ito's article.

The contrast figures are computed with the WCAG relative-luminance formula (the snippet below reproduces them), against white `#FFFFFF` and against a dark page `#121212`. The threshold for a mark needed to read the chart is 3:1 (WCAG 1.4.11).

| Name | Hex | On white | On `#121212` |
| --- | --- | --- | --- |
| Orange | `#E69F00` | 2.25 fails | 8.32 |
| Sky blue | `#56B4E9` | 2.31 fails | 8.12 |
| Bluish green | `#009E73` | 3.42 | 5.48 |
| Yellow | `#F0E442` | 1.32 fails | 14.17 |
| Blue | `#0072B2` | 5.19 | 3.61 |
| Vermilion | `#D55E00` | 3.87 | 4.84 |
| Reddish purple | `#CC79A7` | 3.06 | 6.12 |
| Black | `#000000` | 21.00 | 1.12 fails |

The whole set does not hold 3:1 on either background. Four colours hold it on both: bluish green `#009E73`, blue `#0072B2`, vermilion `#D55E00` and reddish purple `#CC79A7`. Use those four as the core for any chart that will appear on a light and a dark page, and for a fifth or sixth category do one of these instead of inventing colours:

- Use the theme-specific extras: orange, sky blue and yellow on the dark page only, black on the light page only, and keep a per-theme map rather than one list.
- Outline light marks in a dark stroke, or fill and outline, so the shape holds contrast even where the fill does not. State this in the report as a contrast treatment, since the fill still fails on its own.
- Reduce the categories: highlight one in colour and draw the others in grey, or use small multiples.

The same colours on a different background need the check again. Do not invert a light palette for dark mode: re-pick from the table above and test.

The core four, picked by contrast, are a subset of a palette designed as a whole. A subset is not automatically as separable as the set, so run a colour-vision simulation on the rendered image where one is available (the Python library `colorspacious` can convert an image to how a deuteranomalous, protanomalous or tritanomalous reader sees it, through its `sRGB1+CVD` colour space), and say in the report if none was available.

Colour does not replace labels: end-of-line labels, direct bar labels, marker shapes or dash patterns carry the identity, and the colour reinforces it (WCAG 1.4.1).

## Neutral and context ink

Greys for de-emphasised series and for axes are still graphical objects when the reader needs them to read the chart. Measured the same way, `#767676` gives 4.54 on white and 4.12 on `#121212`; `#999999` gives 2.85 on white, so it fails there. Gridlines the reader uses to read values need 3:1 too, and the simpler route is to print the values on the marks and drop the gridlines, which turns them into decoration.

## Sequential and diverging

Use a ramp where the amount is the message and a categorical palette would invent categories.

- Prefer a perceptually uniform sequential map. matplotlib's documentation recommends one for many applications, because lightness changes are read as changes in the data better than changes in hue; its default colormap is `viridis`. Vega-Lite accepts `viridis`, `magma`, `inferno`, `plasma` and `cividis` as scheme names. Avoid `jet`, `turbo` and other rainbow maps for quantities: their lightness rises and falls along the scale, as matplotlib's documentation notes, so equal steps in the data do not read as equal steps.
- ColorBrewer (colorbrewer2.org) lists sequential, diverging and qualitative schemes and lets you filter to colour-blind-safe ones; use its filter rather than guessing. Five-class Blues, for example, is `#eff3ff #bdd7e7 #6baed6 #3182bd #08519c`, and five-class RdBu, a diverging scheme with a light midpoint, is `#ca0020 #f4a582 #f7f7f7 #92c5de #0571b0`.
- The light end of a sequential ramp approaches the page colour by design, so it cannot hold 3:1. Print the value in each cell or on each mark, and outline cells, so the encoding does not rest on the lightest step. On a dark page, run the ramp in the opposite lightness direction so that low still means near the page.
- Diverging maps need a meaningful midpoint (zero, a target, the average). Centre the scale on it, and keep both arms the same length.

## Contrast check

Compute it; do not eyeball it. Pass the marks and the backgrounds as arguments and read the table it prints.

```python
import sys


def luminance(hex_colour):
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


marks, backgrounds = sys.argv[1].split(","), sys.argv[2].split(",")
for m in marks:
    ratios = [contrast(m, b) for b in backgrounds]
    row = "  ".join(f"{r:5.2f}" for r in ratios)
    print(f"{m:8} {row}  {'ok' if min(ratios) >= 3 else 'FAILS 3:1'}")
```

Save it outside the repository under a name of your choosing and run `python3 contrast.py "#009E73,#0072B2" "#FFFFFF,#121212"`. WCAG says to compare the unrounded ratio with the threshold, so 2.999 does not pass 3. Anti-aliasing can make a thin line render fainter than its nominal colour; the WCAG guidance encourages avoiding very thin lines, or exceeding the minimum, so use a stroke width a reader can see at the shipped size.
