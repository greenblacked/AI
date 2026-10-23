# Image inventory and triage

Read this when building the inventory of docs images and deciding what happens to each.

## Contents

- [Finding every image reference](#finding-every-image-reference)
- [Inventory columns](#inventory-columns)
- [Triage questions](#triage-questions)
- [Alt text by image type](#alt-text-by-image-type)

## Finding every image reference

Search the docs source, not the built site, so each hit points at a file someone can edit.
Patterns to run as regular expressions over the docs tree. Run them in multiline mode
(`rg -U`), because an `<img>` tag often wraps its attributes across lines and a
line-by-line search misses the `src` on the second one:

| Form | Pattern |
| --- | --- |
| Markdown inline image | `!\[[^\]]*\]\([^)\s]+` |
| Markdown reference image | `!\[[^\]]*\]\[[^\]]*\]`, then resolve the label's definition |
| HTML image | `<img[^>]*\bsrc=` |
| Framework image components | the component name your docs framework uses, such as an `Image` or `Figure` element in MDX |
| Images set in CSS or theme config | `url\(` in the docs theme's stylesheets |

Then list every file under the docs image directories and check each against the hits.
A file no page references is an orphan: delete it. Images hosted outside the repository,
on a CDN or a wiki attachment store, are still in scope; list them by URL.

Read each page's hits in context rather than trusting the regular expression alone: an
image inside a code block that demonstrates image syntax is not an image on the page.

## Inventory columns

One row per image file:

| Column | Content |
| --- | --- |
| File | Path or URL |
| Pages | Every page that shows it |
| Last changed | `git log -1 --format=%cs -- <file>` |
| Shows | Terminal, code, setting location, table, diagram, layout, visual result, illustration |
| Decision | Text, code block, table, diagram source, scripted capture, hand-made, delete |
| Owner | Team, for scripted and hand-made images |
| Alt text | Current text, and whether it states the point |

The `Last changed` column is the quickest ranking: the oldest images of the UI are the most
likely to be wrong, and the place to start checking against the live product.

## Triage questions

Ask in order and stop at the first that decides:

1. **Does any page use it?** No: delete.
2. **Is it text in a picture?** Terminal output, code, config, an error message, a table.
   Replace it with the text. An error message as text is also what a reader searching for
   that message finds.
3. **Is the point a location?** If one sentence naming the menu path, with labels exactly
   as the UI shows them, gets the reader there, write the sentence. Keep an image only where
   the screen is busy enough that the sentence alone would leave the reader hunting.
4. **Is it a diagram?** Recreate it as a text source and delete the export.
5. **Is the point visual?** A chart's appearance, a layout, a before-and-after. Keep it as a
   scripted capture.
6. **Can it be scripted at all?** A photo, an illustration, a capture from hardware or a
   third-party app the automation cannot drive. Keep it by hand with an owner and date.

Where a page has several screenshots walking through one flow, check whether one capture
of the final state plus numbered text steps would serve better. A screenshot per click is
the pattern that rots fastest, because any change anywhere in the flow invalidates one of
them.

## Alt text by image type

Alt text states what the reader should take from the image at that point in the page.

| Image | Weak | Better |
| --- | --- | --- |
| A setting's location | Screenshot of settings | The Send invoices by email switch, in the Invoices section of Billing, turned on |
| A result to compare against | Dashboard screenshot | The Requests chart after setup: one line, rising from zero at the time of the first call |
| A layout | Image of the editor | The editor with the file tree on the left, the code in the centre and the preview on the right |
| A diagram | Architecture diagram | Requests pass from the load balancer to three API instances, which share one Postgres primary |
| A decorative banner | Banner image | Empty alt text, so screen readers skip it |

For a complex diagram, give a short alt text and put the full description in the text of
the page, where every reader benefits from it. If the page text already says everything
the image shows, the image is redundant: remove it, or keep it with empty alt text.
