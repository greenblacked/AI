# Selector strategy in awkward cases

The ladder in `SKILL.md` covers the common case. This file covers the elements that have no accessible name, the applications where text is not stable, and the frameworks that do not offer a role-based locator.

## Contents

- [When the element has no accessible name](#when-the-element-has-no-accessible-name)
- [Where the accessible name comes from](#where-the-accessible-name-comes-from)
- [Localised and user-generated text](#localised-and-user-generated-text)
- [Naming test ids so they survive](#naming-test-ids-so-they-survive)
- [Scoping instead of indexing](#scoping-instead-of-indexing)
- [The ladder in other frameworks](#the-ladder-in-other-frameworks)
- [Canvas, iframes and shadow DOM](#canvas-iframes-and-shadow-dom)

## When the element has no accessible name

An interactive element with no accessible name is an accessibility defect, so the first question is whether to fix the product instead of working around it in the test. An icon-only button with no label is unusable with a screen reader, and adding `aria-label` fixes both the product and the test in one change. Prefer that.

Work around it only when the element is genuinely not interactive — a status region, a total, a chart caption — or when the product change is out of scope for the current task. Then use a test id, and note in the test why the rung above was unavailable.

## Where the accessible name comes from

Knowing the precedence prevents a common surprise: a button with visible text "Save" that is located as "Save changes" because an `aria-label` overrides the text. In rough order, the name comes from `aria-labelledby`, then `aria-label`, then the native mechanism for the element — a `label` element for a form control, `alt` for an image, the caption for a table, the content of a `legend` for a fieldset — then the element's own text content, then `title`.

Two consequences worth holding. An `aria-label` silently replaces visible text, so a locator written from the screen can fail against a DOM that names the element differently; read the accessibility tree rather than the rendered page when a role-based locator will not match. And an accessible name assembled from `aria-labelledby` changes when any referenced element changes, which makes it less stable than visible text for dynamic content.

Playwright matches accessible names case-insensitively and with whitespace collapsed, and offers an exact-match option when the loose match is ambiguous. That tolerance is deliberate and it is what makes role-based locators survive a copy edit that changes capitalisation.

## Localised and user-generated text

Text-based locators break under localisation and under user-generated content. Three approaches, in order of preference:

1. **Run the suite in one pinned locale** and locate by text in that locale. Simplest, and correct when the suite's job is functional coverage rather than translation coverage. Pin the locale in configuration so the runner cannot disagree with the laptop.
2. **Locate by role with a name drawn from the same translation catalogue the application uses.** The test then reads the key rather than the string, and a translation change updates both sides at once. This is worth the wiring when the suite must run in several locales.
3. **Test ids for the localised elements only**, keeping role and name for everything else. The cost is that those particular assertions no longer verify what the user sees.

For user-generated content — a customer's name, an order reference — locate by the value the test itself created. That value is unique to the test, which solves isolation and locating in one move.

## Naming test ids so they survive

A test id earns its place by being deliberate. Name it for the thing, not for its position or its styling: `order-total`, not `summary-row-3` or `bold-price`. Keep them stable across a redesign by treating them as an interface — a rename is a breaking change and should appear in the diff as one.

Put the id on the element whose identity you mean. An id on a wrapper `div` forces every assertion to traverse into it, and the traversal is the brittle part you were trying to avoid.

Configure the attribute once rather than per call. Playwright reads `data-testid` by default and accepts another attribute through the `testIdAttribute` option, which matters when a team already standardises on something else and does not want two conventions in the same markup.

## Scoping instead of indexing

`.first()`, `.last()` and `.nth(2)` resolve an ambiguous locator by taking a position, which means the test passes until the order changes and then asserts confidently about the wrong element. Reach for scoping first:

- Scope to the region that contains the element: find the row by the unique text the test created, then find the button inside it.
- Scope by role landmark — navigation, main, the named dialog — when the same control appears in a header and a body.
- Filter by content rather than by index: the list item that has the text you are looking for.

Indexing is defensible only where position is the thing under test, such as an assertion that a sort order is correct. Say so in a comment when you use it, so the next reader knows it was a decision.

## The ladder in other frameworks

| Framework | Role and accessible name | Test id | Notes |
| --- | --- | --- | --- |
| Playwright | `getByRole`, `getByLabel`, `getByText` built in | `getByTestId`, attribute configurable | Locators are strict by default: two matches is an error, not a silent first-match. |
| Testing Library, in any of its bindings | `getByRole`, `getByLabelText` are the documented priority | `getByTestId`, documented as the last resort | The priority order that the Playwright ladder mirrors. |
| Cypress | No built-in role locator; `@testing-library/cypress` adds `findByRole` and the rest | `cy.get('[data-cy=...]')` is the common house convention | Without the Testing Library plugin, teams default to test ids everywhere, which loses the accessibility contract. |
| Selenium | None; build it by hand | `By.cssSelector("[data-testid='...']")` | Implement the ladder as helper functions over the accessibility tree, or accept test ids and cover accessibility separately. |

The ladder itself is general. What is framework-specific is whether the framework gives you the first rung for free, and a framework that does not is a reason to add accessibility assertions elsewhere rather than a reason to skip the contract.

## Canvas, iframes and shadow DOM

**Canvas and WebGL.** There is no DOM to locate. Drive the application through the surface it exposes — a debug API, keyboard input, coordinates computed from the application's own state — and assert on state rather than on pixels unless visual regression is the point. Treat coordinate-based interaction as the last rung of the ladder, because it breaks on every layout change.

**Iframes.** Locate the frame first, then locate inside it. A third-party iframe — a payment field, an embedded widget — is a third party by definition, and the guidance in the network step applies: stub it unless testing it is the point, because its internals will change without notice.

**Shadow DOM.** Playwright's locators pierce open shadow roots, so the ladder works unchanged. Closed shadow roots are opaque to any tool, and an application that uses them needs a deliberate testing interface from the component itself.
