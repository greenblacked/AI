# Navigation patterns

## Contents

- Choosing a pattern
- Global navigation
- Local navigation
- Utility navigation
- Contextual navigation
- Breadcrumbs
- Facets and filters
- Mega-menus
- Footers
- Mobile navigation
- Navigation states

## Choosing a pattern

A pattern is chosen for a job, not for a look. Name the job before picking: moving between top-level areas is global nav; moving within an area is local nav; account, help and legal is utility; linking from one page's content to another is contextual; showing depth is breadcrumbs; narrowing a large set is facets.

## Global navigation

The top level, on every page, in the same place.

- Keep it to about five to seven items, ordered by how many people need them.
- Each item is a label in the users' words, not a team or a product name.
- The current area is marked, and its item stays visible on every page inside it.
- Do not put a call to action ("Sign up") in the same list as navigation areas; it is a different kind of thing.

## Local navigation

The sections within one area.

- Appears when a user is inside a global area, and names its siblings.
- Follows the global nav in position and weight so the hierarchy reads.
- Sub-items with their own children use expand/collapse or a landing page, not a third level in the global bar.

## Utility navigation

Account, help, language, cart, sign out.

- Kept visually apart from the global areas, usually top-right or in the footer.
- Rarely used, so it can be smaller, but it must not disappear at narrow widths.
- "Sign in" and the account name occupy the same slot; one replaces the other.

## Contextual navigation

Links inside the content that move along a journey.

- "Related articles", "Next step", "See also" — the words say where they go.
- The most valuable kind for findability and SEO, because it connects by meaning rather than hierarchy.
- Do not use it as a substitute for real navigation; a page reachable only from another page's body is hard to return to.

## Breadcrumbs

Depth, from the root to the current page.

- Show hierarchy, not history. They answer "where am I", not "how did I get here".
- The last crumb is the current page and is not a link.
- Omit them when the hierarchy is one level deep; they add noise without information.

## Facets and filters

Narrowing a large set by attributes.

- Facets are the attributes users actually choose by (price, size, brand, date), not every field in the database.
- Show the count per option, and hide or disable options with zero results.
- Filters are applied and cleared visibly; the URL carries them so a result can be shared and returned to.
- Facets replace categories when the set has many valid groupings; they do not replace the base taxonomy.

## Mega-menus

A large panel opened from a top-level item.

- Use when a top-level area has many destinations that need showing at once, such as a catalogue.
- Group the panel's columns by the same taxonomy as the area, not alphabetically or by team.
- Keyboard-navigable, dismissible with Escape, and not dependent on hover alone.
- Past a couple of dozen links, the panel is a symptom that the top level is doing too much.

## Footers

The catch-all, and the place the utility nav lands on mobile.

- Hold the links that belong nowhere else: legal, careers, contact, social, sitemap.
- A second, fuller sitemap in the footer helps people and crawlers find deep pages.
- Do not move primary navigation to the footer to keep the header clean; it costs findability.

## Mobile navigation

- The top level moves behind a menu button or a tab bar; pick one and stay consistent.
- A tab bar holds about five destinations and only the ones used most; everything else goes in the menu.
- Keep the current area marked when the menu is closed.
- Never hide navigation behind a gesture with no visible affordance.

## Navigation states

- **Current** — the page you are on, marked with more than colour: weight, a marker, or an underline.
- **Ancestor** — a parent of the current page, marked in the global nav so the hierarchy reads.
- **Visited** — where the platform supports it, so users can retrace.
- **Focus** — visible for keyboard users on every item.
- **Disabled or unavailable** — explained, not just greyed, when a user would expect to reach it.

Every state must be distinguishable without colour alone, for the same reason the rest of the interface must.
