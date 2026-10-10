# Visual hierarchy, type, spacing and colour

## Contents

- The hierarchy tests
- The type scale
- The spacing scale
- Colour roles and emphasis
- Alignment and rhythm
- Reviewing a screen

## The hierarchy tests

Three cheap tests, in order:

1. **The squint.** Blur the screen or step back. What survives is the hierarchy. The primary action and the primary content should survive; the logo and secondary controls should not.
2. **The five-second.** Show it to someone for five seconds and ask what the screen is for. If they cannot say, the hierarchy is not communicating the task.
3. **The grayscale.** Remove colour. If the primary action no longer stands out, the hierarchy depends on hue alone and will fail for a colour-blind user or in a theme.

A screen passes when one action is clearly primary and one block is clearly the content. A screen with two primaries has none.

## The type scale

- Pick a ratio — 1.2 for dense UI, 1.25 for a marketing page, 1.333 for display work — and derive sizes from it.
- Name sizes by role, not number: caption, body, lead, heading, display. Roles survive a theme change; "16px" does not.
- Keep the body at a comfortable measure: 45 to 75 characters a line. Wider loses the return sweep; narrower breaks rhythm.
- Line height falls as size rises: around 1.5 for body, 1.2 for headings, 1.1 for display.
- Two weights are usually enough. A third is a decision; five is a mess.

## The spacing scale

One scale, used everywhere:

```text
4 · 8 · 12 · 16 · 24 · 32 · 48 · 64
```

- Space is meaning: related elements sit close, unrelated ones sit far. The gap is the grouping.
- The step between scales is the nesting: an 8px gap inside a group, a 24px gap between groups.
- A gap off the scale is a one-off nobody will remember; put it on the scale or make it a named exception.

## Colour roles and emphasis

Name roles, let the theme hold the values:

```text
background · surface · text · muted text · border · primary · danger
```

- Emphasis is contrast against the surrounding surface. The primary action is the element with the strongest contrast, not the brightest colour.
- On a light theme that usually means a filled dark button; on a dark theme it may mean the opposite. Check the role pair, not the hue.
- Keep the palette small. Each added role is another pair to check for contrast in every theme.
- Never carry meaning by colour alone — pair it with a label, an icon or a shape.

## Alignment and rhythm

- Choose a few alignment edges — a left margin, a grid, a baseline — and make everything share one of them.
- A misalignment of two or three pixels reads as sloppy even when nobody can name the cause.
- Vertical rhythm: let the spacing scale set the gaps between blocks so the page has a repeatable beat.
- Optical alignment beats mathematical alignment for icons and punctuation; adjust by a pixel where the eye demands it.

## Reviewing a screen

Write each finding as:

```text
Problem: <what is wrong>
Consequence: <what it costs the user>
Fix: <the smallest change>
Severity: 0-4
```

Order findings by the primary task first, polish last. A screen that is beautiful and unusable is a failed screen.
