# Preprocessing and image limits

Read this at step 3, before sending a scan or photo to a model, and again when a request is rejected for size or a field comes back wrong on a small print region.

The figures below are from Anthropic's vision documentation (<https://platform.claude.com/docs/en/build-with-claude/vision>) and PDF documentation (<https://platform.claude.com/docs/en/build-with-claude/pdf-support>), read when this file was written. Limits change between models and platforms, so read the current page for the model you call before relying on a number, and prefer to leave headroom.

## What the API accepts

| Limit | Value | Note |
| --- | --- | --- |
| Formats | JPEG, PNG, GIF, WebP | An animated GIF uses only its first frame. |
| Per-image dimensions | 8000 x 8000 px | |
| Per-image size | 10 MB base64-encoded on the Claude API; 5 MB on Amazon Bedrock and Google Cloud | The encoded size counts, not the file on disk. |
| Images per request | 100 for models with a 200k-token context window, 600 for others on the API | Request size limits can be reached first. |
| Many-image requests | More than 20 images in one request brings a stricter per-image dimension limit | Keep each side at or under 2000 px, or keep the request to 20 images or fewer. Resent images from earlier turns count. |
| PDF | Standard PDF without a password; 600 pages, or 100 when the request's context window is under 1M tokens; 32 MB request | Each page is converted to an image and its text extracted alongside. |

## How the model resizes

The model sees an image as 28 x 28 pixel patches and an image costs `ceil(width / 28) x ceil(height / 28)` visual tokens. An image beyond the model's long-edge or token limit is downscaled with its aspect ratio kept.

| Resolution tier | Models | Max long edge | Max visual tokens |
| --- | --- | --- | --- |
| High-resolution | Claude 4.7 and later | 2576 px | 4784 |
| Standard | All other models | 1568 px | 1568 |

The tier changes what survives. A 1920 x 1080 image is downscaled on the standard tier and left alone on the high-resolution one, at a higher token cost. Pick the tier for the smallest print you must read, not for the document's pixel count, and downsample when the fidelity is not needed to keep cost down.

The documentation also warns that the model may hallucinate or make mistakes on low-quality, rotated or very small images under 200 px. Treat a field read from a region that small as held for review.

## Preprocessing order

Do these in order, and keep the original so a reviewer can see what the model did not.

1. Orient. Rotate to upright using the page's own orientation; the documentation names rotated input as a known cause of mistakes.
2. Deskew and crop to the document. Remove the table, the hand and the background; they cost tokens and offer the model things to misread.
3. Remove what is not needed. Crop out regions you must not send (account numbers beyond what the task needs, faces on an identity card) before the image leaves the machine, not after.
4. Size for legibility, not for the limit. Measure the smallest text you need to read, and make sure it survives the resize. If it does not, cut the page into strips instead of shrinking it.
5. Encode within the size limit. Prefer PNG for text and line art and JPEG for photographs; check the base64 size, which is larger than the file.

## Tiling a tall or dense page

A long receipt, a ledger page or a dense form shrinks to illegible when it is fitted to a single image. Cut it into strips along the long axis, each within the long-edge limit with a margin of overlap that spans at least one full line of text, so that no row is cut in half without appearing whole in a neighbour.

- Keep the strip's offset in the original page with each strip, so that a region a model reports maps back to page coordinates.
- Extract each strip independently, then merge. A row that appears in two strips is the same row when its text and its offset agree; keep one and note the other as the overlap.
- Do not carry a running total across strips for the model. Total the strips yourself, in the verification step.

## OCR as a reader

A local OCR engine is the right first reader when the document may not leave the machine, and the right second reader when a vision model is the first.

- Tesseract's output formats include hOCR, TSV, ALTO, PAGE and a searchable PDF, selected by a config name after the output base (<https://github.com/tesseract-ocr/tesseract/blob/main/doc/tesseract.1.asc>). hOCR carries a bounding box and a word confidence (`x_wconf`) for each word (<https://github.com/tesseract-ocr/tessdoc/blob/main/Command-Line-Usage.md>), which is the source-region and confidence data the schema asks for.
- The page segmentation mode (`--psm`) tells the engine what shape of page to expect: 3 is the fully automatic default, 4 assumes a single column of variable sizes, 6 a single uniform block of text, and 11 finds sparse text in no particular order. A receipt column and a form often read better in a mode other than the default; try the candidate modes on a few pages and compare against what you can see.
- OCR output is character recognition without any understanding. It does not repair a smudged digit into a plausible one, which is why it is a useful independent reader, but it confuses visually similar characters (0 and O, 1 and l, 5 and S, 8 and B). Let the format check decide, by field type, which of those is possible.
- An OCR engine's word confidence is its own estimate. Use it to rank what to review, and calibrate it against your labelled sample before treating a threshold as meaningful.

## Text-layer PDFs

pdfplumber documents that it works best on machine-generated PDFs rather than scanned ones, returns words with bounding boxes through `extract_words`, and returns table cells through `extract_tables` (<https://github.com/jsvine/pdfplumber>). Poppler's `pdftotext` and `pdfimages` command-line tools read the text layer and the embedded images; check their manual pages for options rather than copying flags from memory.

To decide whether a PDF is born-digital, compare three things for each page: the extracted text length, whether an image object covers most of the page, and whether a sample of extracted words appears in the rendered page. A page with a text layer and a page-sized image is a searchable scan, and takes the scan path.
