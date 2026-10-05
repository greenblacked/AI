---
name: design-system
description: "Set up or tidy a design system's foundations: design tokens named by role (colour, type with fallbacks, spacing, radius, elevation, motion), light, dark and further themes that redefine the same role tokens, and component state rules so buttons and controls stay consistent. Covers where translucent glass belongs, and contrast as a gate in every theme. Use for design tokens, theming and consistent component states. Casual asks include \"set up design tokens\", \"add dark mode\", \"our buttons are all slightly different\", \"clean up our CSS variables\", \"theme this app\", \"how do I do a frosted glass nav bar\" or \"make the hover and pressed states consistent\". Not for reviewing one screen's usability (ui-ux-review), a WCAG audit (accessibility-audit), testing with users (usability-test-plan), or building a new site (website-builder) or a single component from scratch (code-scaffold)."
allowed-tools: "Read, Write, Edit, Glob, Grep, Bash(git:*)"
---

# Design System

A design system's foundations are finished when every colour, size and motion in the product comes from a token named for its job, every theme defines the same set of tokens, every component state is derived from them, and a check has proved that each text and control pair still has enough contrast in every theme.

Systems decay by accretion: a hex value pasted into one component, a second button style for one screen, a dark theme made by inverting the light one. Each is harmless alone, and together they mean a brand colour change touches two hundred files and no one trusts the result. Naming tokens by value (`--black`, `--blue-500` used directly in components) hides that, because the name carries no intent and cannot be re-pointed in a theme. This skill fixes the layering, makes themes a redefinition of the same roles, derives states instead of hand-picking them, and makes contrast a gate.

## Scope

Use for: introducing tokens to a codebase that has none; consolidating drift; adding a dark or other theme; defining state rules for controls; deciding where a translucent glass material belongs and how to build it on tokens.

Do not use for: reviewing one screen for usability, which is `ui-ux-review`; auditing against WCAG, which is `accessibility-audit`; planning a test with users, which is `usability-test-plan`; building a whole site or redesigning one, which is `website-builder`; writing a component's implementation from nothing, which is `code-scaffold`.

## Workflow

### 1. Inventory what exists

Before designing anything, count the raw values in use. Search the styles and components for hex and rgb colours, pixel sizes, font stacks, shadow and duration values, and tally the distinct ones. Use `git grep` on the style and component files so generated and vendored files stay out.

```bash
git grep -nIE '#[0-9a-fA-F]{3,8}\b' -- '*.css' '*.scss' '*.tsx' ':!node_modules' | wc -l
```

Record the number of distinct colours, font sizes, radii and shadows. That is the baseline the finished work is measured against, and a system that ends with the same count has not reduced anything.

### 2. Choose one source of truth

Put the tokens in one file that a person edits and generate everything else from it: the CSS custom properties, the platform constants, the documentation. A generated file is never edited by hand. If the toolchain already reads a format, use it. The shape of a portable token file, and the mapping to CSS custom properties, are in `references/token-format.md`.

### 3. Name tokens by role, in layers

Primitives hold raw values (a palette, a size ramp) and are referenced only by role tokens. Role tokens carry intent and are what components use: `--ink` for body text, not `--black`; `--surface`, `--surface-raised`, `--line`, `--accent`, `--on-accent`, `--danger`. A component never names a primitive. The test is whether a theme can re-point the token without touching a component.

Define the other families the same way, each as a bounded scale rather than free values:

| Family | Roles to define | Rule |
| --- | --- | --- |
| Colour | Text, surfaces, lines, accent and its on-colour, status colours | Every filled colour has a named `on-` colour for its content. |
| Type | Display, heading, body, label, code | Each role has size, weight, line height and a font stack that ends in a generic fallback, so text renders legibly before the web font loads or if it fails. |
| Spacing | One ramp | Components use the ramp, not arbitrary pixels. |
| Radius | A few steps, plus a full-round value | Pick by component class, not by screen. |
| Elevation | A small set of levels | Material Design 3 uses levels 0 to 5, which are 0, 1, 3, 6, 8 and 12 dp. Whatever you choose, keep it short. |
| Motion | Durations and easings | Define a reduced-motion override in the same place. |

### 4. Make themes redefine the same roles

A theme is a second set of values for the same role tokens, selected by an attribute or a media query. Light, dark and any additional theme must define every role. A role missing from one theme is a silent fallback to something unintended, so list the roles and diff the themes against the list. Do not generate dark mode by inverting light: surfaces, elevation and the accent usually need their own values. Honour the user's system preference as the default and let them override it.

### 5. Derive the component states

Hand-picked hover and pressed colours drift. Derive them from tokens with a state layer: an overlay of the content colour (`on-*`) over the base colour at a fixed opacity. Material Design 3's token set (v0.192) uses 8 percent for hover, 12 percent for focus, 12 percent for pressed and 16 percent for dragged. Use those or choose your own, but define the opacities once as tokens and apply them to every control, so a button, a menu item and a list row react alike. Focus gets its own visible indicator and is not just a state layer. The recipe is in `references/token-format.md`.

Define the size rules as tokens too. Platform guidance for control size differs: iOS and iPadOS list 44 by 44 pt as the default and 28 by 28 as the minimum; Material's filled button has a 40 px container, and Material Web's implementation enforces a 48 px touch target. A visible control may be smaller than its hit area, so define the hit-area minimum as its own token and stay at or above the platform default on touch.

### 6. Decide where glass belongs

A translucent glass material is a floating-layer tool, not a content style. Apple's guidance on Liquid Glass sets the pattern: it "forms a distinct functional layer for controls and navigation elements — like tab bars and sidebars — that floats above the content layer", and says "Don't use Liquid Glass in the content layer" with the exception of transient interactive controls like sliders and toggles, and to "Use Liquid Glass effects sparingly". Its regular variant "blurs and adjusts the luminosity of background content to maintain legibility". Take the rule across platforms as practice:

- Apply glass only to the layer that floats over content: navigation bars, tab bars, toolbars, sheets and popovers. Never to cards, list rows, article bodies or tables.
- Use it on few surfaces at once. Stacked glass over glass loses the separation it exists to provide.
- Build it from tokens (a fill role, a blur amount, an edge role) so every theme defines it, and give it an opaque fallback for when blur is unavailable or the user asks to reduce transparency.
- Measure contrast for text and icons on the glass against the worst content that can scroll behind it, light and dark, not against the average.

### 7. Gate on contrast, then migrate

Before shipping, check the contrast of every role pair in every theme: each text role on each surface it can sit on, each `on-` colour on its fill, each line and control border on its surface, and the glass layer over its worst backdrop. Thresholds are 4.5:1 for text, 3:1 for large text and 3:1 for user interface components and graphical objects (WCAG 1.4.3 and 1.4.11). Write the pairs as a table and fill every cell, including the states.

Then migrate in order of frequency, most-used raw values first, and re-run the step 1 count. Add a gate that fails when a raw colour appears outside the tokens file, so the system does not decay again.

## Anti-patterns

**Naming by value.** `--blue-500` in a component cannot be re-pointed by a theme. Name the role.

**Two sources of truth.** Tokens in a design tool and again in CSS, edited separately, diverge within a quarter. Generate one from the other.

**A theme that skips a role.** The gap falls back to the wrong colour on one screen, found by a user.

**Hand-picked state colours.** Twelve buttons with twelve hover greys. Derive them.

**Glass everywhere.** It lowers contrast on every surface and removes the layering it was meant to show.

**Checking contrast in the default theme only.** The failures live in dark mode and in disabled, hover and error.

## References

- `references/token-format.md`: read at steps 2, 5 and 6 for a token file in the Design Tokens Community Group format, its mapping to CSS custom properties, the state-layer recipe and a glass material built on tokens.
