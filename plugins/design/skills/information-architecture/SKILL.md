---
name: information-architecture
description: "Structure a site or app so people can find things: the sitemap, the navigation, the taxonomy and the labels, and when to browse versus search. Covers grouping content by the user's mental model rather than the org chart, naming sections in the user's words, flattening deep hierarchies, and testing the structure with a card sort or tree test before it ships. Use this skill whenever someone is organising content or navigation. Triggers include building or fixing a sitemap, designing a nav or menu, agreeing a taxonomy or category names, or a findability problem — including phrasings like \"nobody can find X\", \"the menu is a mess\", or \"how should we organise these pages\". Do not use it for a single screen's usability (ui-ux-review), the wording of a label once the structure is set (content-design), the mechanics of running a study (usability-test-plan), or building the site (website-builder)."
allowed-tools: Read, Write, Edit, Grep, Glob
---

# Information Architecture

A structure is finished when a person who has never seen it can predict where a thing lives, find it in a few steps, and name the section they used in the same words the navigation uses.

The job fails in a predictable direction: the structure is drawn from the organisation that made the content rather than the person looking for it. The nav has a "Solutions" item because a product team owns one, "Resources" because marketing owns another, and the thing a customer came for is three levels under "Company". Depth compounds the problem — every extra level is another chance to choose wrong — and labels make it worse, because a label the team understands ("Endpoints") tells a newcomer nothing. The other failure is skipping the test: the team argues about the sitemap in a meeting, ships it, and learns from support tickets that everyone looks under a different heading. This skill works from the content and the users' words, keeps the structure shallow and predictable, and tests it before build.

## Scope

Use for: the structure of a site or app — sitemap, hierarchy, global and local navigation, menus, breadcrumbs, taxonomy, categories, tags, faceted browse, and the browse-versus-search decision; naming sections; auditing why people cannot find something; planning a card sort or tree test to decide a structure; documenting an IA for handoff; planning URLs and redirects when the structure changes.

Do not use for: the usability of one screen or flow, which is `ui-ux-review`; the wording of a single label once the structure is set, which is `content-design`; the mechanics of running the study itself, which is `usability-test-plan`; a WCAG audit, which is `accessibility-audit`; or building the site, which is `website-builder`.

## Workflow

### 1. Inventory the content and name the tasks

List what actually exists — pages, products, articles, settings — and, separately, the tasks people come to finish. The inventory is the raw material; the tasks are what the structure has to serve. If you have no inventory, take one from the CMS, the sitemap or a crawl before drawing anything.

### 2. Group by the user's mental model, not the org chart

Cluster the content by how users think about it, which is usually by task or by thing, not by which team owns it. A section named for a department ("Platform") is a finding: it exists for the maker, not the finder. Where a real user model is unknown, say so and get one — do not invent it from the org chart and call it done.

### 3. Label in the user's words

A label must predict its contents to someone who has not seen the site. Prefer the word users say in search and support over the internal term. Test the label by asking what someone expects to find under it; if the answers scatter, the label is wrong or the group is. Keep one term per concept, matching the product's termbase.

### 4. Keep the hierarchy shallow and predictable

- Prefer breadth to depth: seven top-level items are easier to scan than three levels of three.
- Aim for a task to be reachable in about three choices from the home or nav.
- A category with one child, or with a child that belongs to two parents, is a smell — flatten or re-home it.
- The same kind of thing should sit at the same depth every time, so the structure is learnable.
- Reserve the top level for the few things most people come for; everything else lives under them.

### 5. Choose the navigation patterns

Pick from `references/navigation-patterns.md` and say why: global nav for the top level, local nav within a section, utility nav for account and help, contextual links within content, breadcrumbs for depth, facets for a large set. Navigation states — current, ancestor, visited — must be visible, not implied by colour alone.

### 6. Decide browse versus search

Browse works when the set is small enough to scan and the categories are obvious; search works when the set is large, the words are known, or the item is specific. Most large sites need both, with facets for filtering. Do not use search to paper over a structure nobody can browse; a search box on a tangled site returns tangled results.

### 7. Plan the URLs and findability signals

Make URLs read like the hierarchy so they can be guessed and shared. Plan redirects and a migration map whenever the structure changes, and never ship a new IA that breaks every existing link.

### 8. Test the structure before build

- **Card sort** — give users the content and ask them to group and name it; use it when the grouping is unknown.
- **Tree test** — give users the proposed structure and a task, and see where they go; use it when the structure is drafted and you need to know if it works.
- **First-click or search-log analysis** — use existing behaviour when you have it.

Five to fifteen participants per round is enough for structure. Record where people went, not just whether they were right.

### 9. Document and hand over

Deliver a sitemap, the taxonomy with definitions, the navigation spec (what appears where, in what order, for whom), the URL scheme, and the redirect map. Name the open questions the test did not settle.

## Output format

```markdown
## Sitemap
[Indented tree, top level first, each node with its label and one-line purpose.]

## Taxonomy
[Category, definition, what belongs, what does not.]

## Navigation
[Global, local, utility, contextual, breadcrumbs — what appears and when.]

## Browse vs search
[The decision, and the facets for the large sets.]

## Test plan
[Card sort or tree test, the tasks, the success measure.]

## Migration
[URL scheme, redirects, what changes for existing links.]

## Open questions
[What the structure assumes and the test has not yet confirmed.]
```

## Anti-patterns

**The org-chart nav.** Sections named for teams and functions rather than for what users look for. The maker finds it obvious; the finder does not.

**Depth for its own sake.** Four levels where two would do, each one a chance to choose wrong. Prefer breadth.

**The label only the team knows.** "Endpoints", "Assets", "Platform" — internal words that predict nothing. Use the users' word.

**One child.** A category with a single item, or a child filed under two parents, means the grouping is not real. Flatten it.

**Search as a patch.** A search box over a structure nobody can browse hides the problem rather than fixing it.

**The untested sitemap.** A structure agreed in a meeting and shipped without a card sort or tree test. Support tickets then reveal it.

**The migration nobody planned.** A new structure that 404s every old URL, throwing away the findability the site already had.

## References

- `references/navigation-patterns.md`: read at step 5 for the patterns — global, local, utility, contextual, breadcrumbs, facets, mega-menus, footers, mobile — with when each fits and how its states read.
- `references/taxonomy-and-labelling.md`: read at steps 3 and 4 for grouping, labelling and hierarchy — controlled vocabularies, facets versus categories, card sorts and tree tests, and the IA document.
