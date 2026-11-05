# Design decisions

Keep this file beside the page (for example `design-decisions.md`), never inside the
shipped CSS or HTML. Fill it in before building. The user reads it first and can redirect
here, which costs far less than redirecting a built page.

## Inherited

What the project already had, and was kept: design system, tokens, framework, fonts,
palette. Write "nothing found" if there was nothing.

-

## Brief

- **Audience:**
- **The one action the page must drive:**
- **Tone:**
- **Stated defaults** (anything the user did not answer, and the default taken):

## Material available

Sort what the page can really show. Never invent a number, quote, customer, logo or
testimonial.

- **Real facts and figures** (with sources):
- **Showable things** (photographs, captures, objects, with where each file lives):
- **Missing proof** (left absent on the page):

## Visitor's job and sections

The job (book, buy, sign up, subscribe, visit, read):

The sections that job needs, and why each is there:

## Shape

- **Chosen shape**, or "none fits" with the reason:
- **Fingerprint** (heading, body, divider, button, image, reveal):
- **Neighbour test:** what a different request in this category would get, and the axes
  changed because of it:

## Material

Score each family 0 to 3 on fit to the material available, tone, contrast needs and
legibility for the audience, then show the top three.

| Family | Fit | Tone | Contrast | Legibility | Total |
| ------ | --- | ---- | -------- | ---------- | ----- |
|        |     |      |          |            |       |
|        |     |      |          |            |       |
|        |     |      |          |            |       |

- **Chosen, and why:**
- **Token set** (background steps, ink, muted ink, rule, accent, on-accent, focus):
- **Display face, body face, outlier face:**
- **Radius, rule weight, depth, texture, photo treatment, motion, voice:**

## Signature element

The strongest real thing the content has, shown large on the first screen:

## Overrides

One line per number changed from the lint's defaults, for example
`override: taste-gradient-stops max=5`, with the reason beside it in prose. A floor rule
accepts an override only in the stricter direction, such as `override: floor-body-size
minimum=18`; a looser one is refused. The reviewer confirms every override listed.

## Waivers

One line per taste finding kept on purpose. The line starts with `waive:`, then the rule
id, a dash and the reason, as in `waive: <rule-id> — <reason>`. A floor rule cannot be
waived, and a waiver stands only once the reviewer agrees with it.

-

## Review

- **Floor findings left:** none expected
- **Reviewer's answer on each waiver and each override:**
- **Rendered checks handed on** (contrast, overflow, focus, reflow):
- **The one piece of real material that would most improve the page:**
