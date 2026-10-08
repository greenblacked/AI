# Taxonomy and labelling

## Contents

- Categories versus facets
- Building a taxonomy
- Controlled vocabulary
- Labelling rules
- Hierarchy and depth
- Card sort
- Tree test
- Search logs and analytics
- The IA document

## Categories versus facets

A category is one place a thing lives; a facet is one attribute a thing has. A camera lives in "Cameras" (category) and has facets for brand, sensor size and price. Use categories when things belong in one obvious place and the set is small; use facets when the set is large or has several valid groupings. Mixing them — categories that are really attributes, or facets that are really a hierarchy — produces a structure nobody can predict.

## Building a taxonomy

1. **Inventory** every item with its attributes.
2. **Cluster** by the users' mental model, from a card sort if the grouping is unknown.
3. **Name** each cluster in the users' words (see Labelling rules).
4. **Define** what belongs and, more usefully, what does not.
5. **Test** the structure with a tree test.
6. **Maintain** it: a taxonomy with no owner rots into a junk drawer.

A category earns its place when it has several items, a clear definition and a name a user would choose. A category with one item, or with no definition, is a smell.

## Controlled vocabulary

A controlled vocabulary is the agreed set of terms, with the words you do not use pointing at the word you do.

| Preferred term | Also called (do not use in the UI) |
| --- | --- |
| project | workspace, board, space |
| plan | tier, package, subscription level |
| invoice | bill, statement |

- Keep the synonym list so search and redirects can map the old word to the new.
- Add a term only when the same thing has been named two ways in the product.
- Where a public API or help centre already uses a term, prefer it unless it is wrong for users.

## Labelling rules

- The label predicts the contents to someone who has not seen the site.
- Use the word users say in search and support, not the internal name.
- Noun phrases for categories ("Billing"), verbs for actions ("Add a payment method").
- Sentence case, no jargon, no cleverness that costs clarity.
- Test by asking what someone expects under the label; scattered answers mean the label or the group is wrong.
- One term per concept, across navigation, search and help.

## Hierarchy and depth

- Prefer breadth to depth: about five to seven items per level, and tasks reachable in about three choices.
- The same kind of thing sits at the same depth every time, so the structure is learnable.
- Flatten a level that has one child; re-home a child that belongs to two parents.
- The top level is the few things most people come for; everything else lives under them.
- If a level exists only because the org has that many teams, remove it.

## Card sort

Use to discover the grouping when you do not know it.

- **Open sort:** participants group items and name the groups. Reveals the users' categories and labels.
- **Closed sort:** participants place items into groups you define. Tests a proposed taxonomy.
- Fifteen to thirty items is a workable set; more than that tires participants and blurs the pattern.
- Five to fifteen participants per round. Record the groups, the names they give and the items that never agree.
- Read the result as a signal, not a vote: an item placed in the same wrong group by everyone is telling you the group's name is wrong.

## Tree test

Use to test a drafted structure before build.

- Give participants the tree (labels only, no design) and a task ("Where would you find last month's invoice?").
- Measure first-click success, path taken and time; first-click is the strongest signal.
- Write tasks from real user goals, not from the structure's own labels.
- Ten to fifteen participants per round is enough; run more rounds rather than a bigger one.
- A task everyone fails by going to the same wrong place is a labelling or grouping defect, not a participant error.

## Search logs and analytics

Existing behaviour beats a new test when you have it.

- Top searches with no clicks are unmet content or a wording mismatch.
- Searches that repeat and then succeed suggest a label problem.
- Where a page is reached and then abandoned, the page or its place in the structure is wrong.
- First-click tests on an existing nav show where the current structure loses people.

## The IA document

Deliver the structure so someone can build and maintain it.

```text
Sitemap        the tree, each node labelled and given a one-line purpose
Taxonomy       each category, its definition, what belongs and what does not
Vocabulary     preferred terms and their synonyms
Navigation     what appears in global, local, utility and contextual, and in what order
URLs           the scheme, and how it maps to the hierarchy
Redirects      old URL -> new URL, for every existing link
Test results   what the card sort or tree test found
Open questions what the structure assumes and the test has not confirmed
```
