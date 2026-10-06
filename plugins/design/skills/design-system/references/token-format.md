# Token file, CSS mapping, state layers and glass

Read this during step 2 (the file), step 5 (states) and step 6 (glass) of `SKILL.md`.

## Contents

- The token file format
- Mapping to CSS custom properties
- Themes
- State layers
- A glass material on tokens
- The contrast table

## The token file format

The Design Tokens Community Group's Format Module 2025.10, dated 28 October 2025, is the first version marked Stable. It is a Community Group report, not a W3C Standard. Tools implement different revisions, so before relying on any detail below, check which revision your build tool reads. The example below follows 2025.10, where colour, dimension and duration values are objects rather than strings: a colour is `colorSpace` and `components` (sRGB components run from 0 to 1) with optional `alpha` and `hex`, a dimension is a numeric `value` with a `unit` of `"px"` or `"rem"`, and a duration is a numeric `value` with a `unit` of `"ms"` or `"s"`. Tools written against earlier drafts expect plain strings such as `"#141413"` or `"4px"`; if yours does, it is reading an older revision, and the shapes are the part to convert.

The shape this skill relies on:

- A token is a JSON object with a required `$value`, an optional `$type` and an optional `$description`.
- Tokens nest in groups. A group's `$type` is inherited by the tokens inside it.
- An alias refers to another token with a string in braces, such as `"{color.palette.stone-900}"`.
- Types are `color`, `dimension`, `fontFamily`, `fontWeight`, `duration`, `cubicBezier` and `number`. Composite types are `strokeStyle`, `border`, `transition`, `shadow`, `gradient` and `typography`.
- The recommended file extensions are `.tokens` and `.tokens.json`, and the media type is `application/design-tokens+json`.

An example, with illustrative values that you must replace and measure for your own palette:

```json
{
  "$schema": "https://www.designtokens.org/schemas/2025.10/format.json",
  "color": {
    "$type": "color",
    "palette": {
      "stone-950": { "$value": { "colorSpace": "srgb", "components": [0.0784, 0.0784, 0.0745], "hex": "#141413" } },
      "stone-50": { "$value": { "colorSpace": "srgb", "components": [0.9686, 0.9647, 0.9529], "hex": "#f7f6f3" } },
      "indigo-600": { "$value": { "colorSpace": "srgb", "components": [0.2314, 0.2471, 0.8196], "hex": "#3b3fd1" } },
      "indigo-300": { "$value": { "colorSpace": "srgb", "components": [0.6471, 0.6588, 0.9608], "hex": "#a5a8f5" } }
    },
    "light": {
      "ink": { "$value": "{color.palette.stone-950}", "$description": "Body text" },
      "surface": { "$value": "{color.palette.stone-50}" },
      "accent": { "$value": "{color.palette.indigo-600}" },
      "on-accent": { "$value": "{color.palette.stone-50}" }
    },
    "dark": {
      "ink": { "$value": "{color.palette.stone-50}" },
      "surface": { "$value": "{color.palette.stone-950}" },
      "accent": { "$value": "{color.palette.indigo-300}" },
      "on-accent": { "$value": "{color.palette.stone-950}" }
    }
  },
  "space": {
    "$type": "dimension",
    "1": { "$value": { "value": 4, "unit": "px" } },
    "2": { "$value": { "value": 8, "unit": "px" } },
    "3": { "$value": { "value": 16, "unit": "px" } }
  },
  "font": {
    "body": {
      "$type": "fontFamily",
      "$value": ["Inter", "system-ui", "sans-serif"]
    }
  },
  "motion": {
    "$type": "duration",
    "fast": { "$value": { "value": 120, "unit": "ms" } },
    "base": { "$value": { "value": 200, "unit": "ms" } }
  }
}
```

Note that `light` and `dark` define the same four roles. A build step checks that the two groups have identical keys, and fails when they do not.

## Mapping to CSS custom properties

Components read role tokens only. The primitives stay in the generated file and are not referenced from component CSS.

```css
:root {
  --ink: #141413;
  --surface: #f7f6f3;
  --accent: #3b3fd1;
  --on-accent: #f7f6f3;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 16px;
  --font-body: "Inter", system-ui, sans-serif;
  --motion-fast: 120ms;
}

[data-theme="dark"] {
  --ink: #f7f6f3;
  --surface: #141413;
  --accent: #a5a8f5;
  --on-accent: #141413;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ink: #f7f6f3;
    --surface: #141413;
    --accent: #a5a8f5;
    --on-accent: #141413;
  }
}

@media (prefers-reduced-motion: reduce) {
  :root { --motion-fast: 0ms; }
}
```

The theme blocks repeat values by design, because the generator writes both; neither is edited by hand. The system preference is the default, and the attribute is the user's override.

## Themes

A third theme (high contrast, a brand variant) is another group with the same roles. The rule is the same: a role missing from a theme is a failing check, not a fallback.

## State layers

A state is the base fill with a layer of the `on-` colour over it at a fixed opacity. Define the opacities once:

```css
:root {
  --state-hover: 8%;
  --state-focus: 12%;
  --state-pressed: 12%;
  --state-dragged: 16%;
}

.button--filled {
  background: var(--accent);
  color: var(--on-accent);
  min-height: 40px;
  border-radius: 9999px;
}
.button--filled:hover {
  background: color-mix(in srgb, var(--on-accent) var(--state-hover), var(--accent));
}
.button--filled:active {
  background: color-mix(in srgb, var(--on-accent) var(--state-pressed), var(--accent));
}
.button--filled:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
```

The four opacities are Material Design 3's state-layer values from the token set v0.192: hover 8 percent, focus 12, pressed 12 and dragged 16. The filled button's 40 px container height and fully rounded shape are also from that set. Material Web's button enforces a 48 px touch target in its own implementation, which is not an M3 token; if you want that hit area, give it its own token and extend the control's clickable area to it without changing how it looks.

Every control uses the same variables, so a menu row and a button respond alike. The focus indicator is a separate rule, because a faint overlay alone is not a visible focus. Check the indicator's contrast in each theme.

## A glass material on tokens

Use this only on the floating layer, as the step 6 rules say. These values are starting points to tune against your content, not recommendations.

```css
:root {
  --glass-fill: color-mix(in srgb, var(--surface) 70%, transparent);
  --glass-blur: 20px;
  --glass-edge: color-mix(in srgb, var(--ink) 12%, transparent);
}

.nav-bar {
  background: var(--glass-fill);
  backdrop-filter: blur(var(--glass-blur));
  border-bottom: 1px solid var(--glass-edge);
}

@supports not (backdrop-filter: blur(1px)) {
  .nav-bar { background: var(--surface); }
}
```

Because the fill reads `--surface`, each theme gives the glass its own tint with no extra work. Before shipping, scroll the lightest and darkest real content behind the bar and measure the text and icons on it. If a worst-case backdrop fails contrast, raise the fill's opacity or use the solid surface there. Honour the user's reduced-transparency setting where the platform exposes one, by switching to the solid fallback.

Apple's Liquid Glass guidance is the model for the intent. It is "a dynamic material that unifies the design language across Apple platforms", a distinct functional layer for controls and navigation floating above the content layer, to be used sparingly and not in the content layer. The CSS above is an approximation of the layering idea on the web, not an implementation of Apple's material. Source: <https://developer.apple.com/design/human-interface-guidelines/materials>

## The contrast table

Fill every cell before shipping. One row per pair and state, one column per theme, so a hover colour that passes in light and fails in dark has a cell of its own to fail in. Add a column for every further theme and a row for every further state your components define. Thresholds: 4.5:1 for text, 3:1 for large text, 3:1 for user interface components and graphical objects.

| Pair | State | Needs | Light | Dark |
| --- | --- | --- | --- | --- |
| `ink` on `surface` | rest | 4.5:1 | | |
| `on-accent` on `accent` | rest | 4.5:1 | | |
| `on-accent` on `accent` | hover | 4.5:1 | | |
| `on-accent` on `accent` | pressed | 4.5:1 | | |
| `line` on `surface` | rest | 3:1 | | |
| focus indicator on `surface` | focus | 3:1 | | |
| focus indicator on `accent` | focus | 3:1 | | |
| `ink` on glass over the worst backdrop | rest | 4.5:1 | | |

A disabled control is exempt from both minimums in WCAG 2.2 (1.4.3 and 1.4.11 exclude inactive components), so it has no row; check instead that it still reads as disabled in every theme.
