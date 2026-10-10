---
name: visual-design
description: "Review or set a screen's visual design: the hierarchy that tells the eye where to go, a type scale, colour and spacing systems, alignment, and the contrast of emphasis that makes one action primary. Use for any \"does this look right\" or \"make this screen work visually\" question. Casual asks include \"the page feels flat\", \"what should be the primary button\", \"the spacing is off\", \"this looks cluttered\", \"set up a type scale\" or \"review the visual hierarchy\". Not for tokens, themes and component states (design-system), a usability review (ui-ux-review), a WCAG conformance audit (accessibility-audit), a responsive layout (responsive-design), or writing the layout code (code-scaffold)."
allowed-tools: Read, Grep, Glob
---

# Visual design

A visual review is finished when the hierarchy, the type scale, the colour roles and the spacing scale are each either stated or fixed, and one action on the screen is unambiguously primary.

A screen fails visually for one of two reasons, and they need opposite fixes. Either everything has the same weight, so the eye has nowhere to land and the user reads the whole page to find the one thing that matters; or too many things are loud, so the hierarchy is noise and the primary action competes with the secondary ones. Both come from designing with values picked one at a time — this blue, that 14px, a 12px gap here and a 13px gap there — instead of from a small system of scales and roles that makes the relationships automatic. This skill builds that system for a screen, or reads a screen against one.

## Scope

Use for: reviewing a screen's visual hierarchy; setting a type scale, a spacing scale and colour roles; deciding which action is primary; fixing a screen that feels flat, cluttered or crowded.

Do not use for: defining tokens, themes and component states so contrast holds across themes, which is `design-system`; a usability review of a flow, which is `ui-ux-review`; a WCAG conformance audit, which is `accessibility-audit`; a responsive layout, which is `responsive-design`; writing the layout and CSS, which is `code-scaffold`.

## Workflow

### 1. Find the one thing the screen is for

Name the primary action and the primary content before touching anything. If you cannot name one of each, the screen has no hierarchy to build, and the fix starts at the flow, not the pixels.

### 2. Read the hierarchy top to bottom

Squint at the screen, or screenshot it and shrink it. What survives the blur is the real hierarchy. If the logo or a secondary button survives and the primary action does not, the emphasis is inverted.

### 3. Set the type scale

Pick a small set of sizes with a consistent ratio and name each by role — caption, body, lead, heading, display. Two adjacent sizes should differ enough to read as a step. Body text at a comfortable measure, usually 45 to 75 characters.

### 4. Set the spacing scale

One scale — 4, 8, 12, 16, 24, 32, 48 — and use it everywhere. Space groups related things and separates unrelated ones, so the gaps carry meaning. A gap that is not on the scale is a decision nobody made.

### 5. Assign colour roles, not colours

Name roles — background, surface, text, muted text, border, primary, danger — and let the theme pick the values. Emphasis comes from contrast against the surrounding surface, so the primary action is the one with the strongest contrast, not the one with the brightest hue.

### 6. Check alignment and rhythm

Everything should share a small number of alignment edges. Misalignment by a few pixels reads as sloppy even when nobody can name why. Check the screen at a narrow width too, or hand it to `responsive-design`.

### 7. Report or apply

For a review, write each finding as the problem, the consequence for the user, the smallest fix and a severity from 0 to 4. For a set-up, produce the scales and the roles, and apply them rather than describing them.

## Anti-patterns

**Everything bold.** Emphasis applied to every element, so nothing is emphasised and the page reads as noise.

**Sizes picked one at a time.** A 13px caption, a 15px body, a 22px heading — no ratio, so no step reads as a step.

**Spacing by eye.** Gaps that vary by a pixel or two, which the eye reads as untidy without being able to say why.

**Colour as emphasis.** Using a bright hue for the primary action while a muted but higher-contrast element actually draws the eye.

**The decorative hero.** A large image or heading that dominates a screen whose job is a form or a list, so the hierarchy serves the brand rather than the task.

**Centring body text.** Long centred lines lose the left edge the eye returns to, so reading slows and lines get skipped.

## References

- `references/visual-hierarchy.md`: read for the hierarchy tests, the type and spacing scales, the colour roles, and the emphasis and alignment checks.
