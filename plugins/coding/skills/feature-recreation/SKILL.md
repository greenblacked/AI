---
name: feature-recreation
description: "Build your own version of a feature you saw in another app, without copying its code, text, icons or exact visual design: write what the feature does for the user as your own spec before opening any reference material, keep reading the reference and writing your implementation as separate sessions so no line gets translated rather than reimplemented, and check the licence of anything you do carry across — even a snippet, a sample value or an icon. Use when someone says \"I want a feature like the one in an app, not a copy, something similar\", \"recreate this UI flow in our product\", or \"build our own version of a competitor's feature\". Not for reusing an open-source dependency under a compatible licence (licence-compliance), a spec with no external reference (feature-spec), or reviewing someone else's diff (code-review)."
allowed-tools: "Read, Grep, Glob"
---

# Feature recreation

The job is done when someone who has used both products can say your version does the same
thing for the user, and a side-by-side diff of your source against the reference's — text,
assets, code — turns up nothing beyond what the behaviour itself forces (an HTTP verb, a
common word, a function any correct implementation would also need). "Inspired by" and
"copied from" are not a feeling; they are what that diff shows.

The usual failure is skipping straight from "I like how their export screen works" to
reading their JavaScript bundle or their open network requests with the editor open in the
next tab, so a comment, an error string or a request's exact shape gets typed into your own
codebase without a decision ever being made to put it there. A second failure is treating an
app's behaviour as free simply because the app is popular, free to use, or itself built on
open source — none of those facts says anything about the licence on its own code, its
assets, or whether a pattern is covered by a patent. A third is testing your version by
diffing its output against the reference's exact sample data or fixtures, which quietly
carries the reference's own content into your test suite. The fix for all three is the same:
decide what the feature does before you look at how theirs does it, and keep the two apart
long enough that nothing crosses over by accident.

## Scope

Use for: building an original implementation of a feature, UI flow or behaviour you observed
in someone else's product, documentation or source, when the goal is doing the same job for
the user rather than carrying over their code, text or assets.

Do not use for: pulling in an open-source dependency whose licence already permits it, which
is a licensing decision for `licence-compliance`, not a clean-room exercise; writing a spec
for a feature with no external reference, which is `feature-spec`; understanding a shipped
binary or packaged app down to the artifact level, which is `reverse-engineering` — read that
skill's lawful-use scope first if the only way to understand the feature is static or dynamic
analysis of a binary, and treat its result as input to step 1 below, not as a substitute for
it; or reviewing a diff someone else wrote, which is `code-review`.

## Hard gates

1. **Behaviour first, in your own words, before the reference is open.** Step 1 below
   produces a spec from what the feature does for a user. Nothing from the reference's own
   text, code or comments goes directly into that spec.
2. **Reading and writing are separate, and on a team they are separate people.** Once the
   reference has been read closely enough to extract behaviour, close it before implementing.
   A second person who never opens the reference, implementing only from the spec, is what
   actually shows independent creation; working alone and closing the tab is a weaker
   discipline that cuts down accidental copying but does not show the same thing, and does
   not substitute for the two-person split when gate 4 or gate 5 is live (the reference's
   source was read, or the feature is a core differentiator or a direct competitor's).
3. **No verbatim text, assets, icons, exact visual layout or code.** Error messages, help
   text, variable and function names that leak the reference's internal structure, regexes,
   algorithms copied rather than independently derived, logos and icons — none of it, however
   small the piece.
4. **Licence checked before anything is reused, not after.** Even a single constant, sample
   value or icon carries whatever licence its source carries; `licence-compliance` covers
   compatibility once you know what you are looking at.
5. **Patent and trademark risk is named, not decided here.** A feature can be free of
   copyright concerns and still covered by a patent, or its name and look protected as trade
   dress. This skill does not clear either; flag the risk for legal review when the feature
   is a core differentiator or the reference is a direct competitor.
6. **Verification uses your own test data.** Acceptance tests come from the spec in step 1,
   with your own inputs and fixtures, never the reference's sample data, screenshots or
   recorded responses used as a byte-for-byte oracle.

## Workflow

### 1. Write the behaviour spec before touching the reference

Describe, in your own words: what the user does, what they get, what happens on the edge
cases you can observe (empty input, an error, a limit). This is a short `feature-spec`-style
document, written from using the feature as a user or reading about it secondhand — not from
its code. Using the feature this way is always fine; it is only once you reach for its
internals (its code, its network traffic, a reverse-engineering result) that step 2's
boundaries start to matter. If you cannot write the spec yet, you have not finished
observing; keep observing as a user, not as a reader of its internals.

### 2. Decide what you are allowed to look at, and how

Using a product as an ordinary user, reading its public documentation, or reading your own
network requests in a browser's dev tools are all observing behaviour, and are the normal
way to fill in step 1. Reading the reference's source is a stronger step: only do it when you
have the right to (it is genuinely open source under a licence you have checked, it is your
own prior work, or you have explicit permission), and only to extract behaviour for the spec
— never to copy from while implementing. If understanding the feature requires static or
dynamic analysis of a shipped binary or package, that is `reverse-engineering`'s job; bring
back only what that analysis establishes about behaviour, stated in your own words, and apply
gate 2 to it exactly as you would to source you read directly. [Observation and licence
boundaries](references/observation-and-licence-boundaries.md) has the decision table for
which case you are in and what each one allows.

Before going further, name whether gate 5 applies: is this feature a core differentiator of
your product, or is the reference a direct competitor's? Either one gets flagged for legal
review now, before the time implementing it is spent, not after the feature ships — and
before deciding, next, whether a solo clean-room discipline is enough or this needs the
two-person split.

### 3. Close the reference, then implement from the spec alone

[The clean-room protocol](references/clean-room-protocol.md) covers the two-person version,
which is what independent creation actually rests on, and the weaker solo discipline for
when no second person is available.

Build your own design: your own data structures, your own algorithm where more than one
reasonable one exists, your own naming, your own UI treatment. A different implementation
that satisfies the same spec is the point, not an accident to be minimised. If a step in the
spec turns out to be ambiguous only once you are implementing it, resolve it from the spec's
intent or by observing the reference again as a user — not by reopening its code.

### 4. Verify against your own spec and licence-check what you kept

Write acceptance tests from the spec, with your own fixtures (gate 6). Before merging, list
anything that came from the reference at all — a constant, an icon, a sample value — and
route each through `licence-compliance`, using
[observation and licence boundaries](references/observation-and-licence-boundaries.md) to
decide what counts as "came from the reference" in the first place; anything that is not
clearly cleared does not ship until it is.

## Anti-patterns

**Opening the reference's bundle or repository before writing the spec.** The spec exists to
be the only thing the implementation reads from; write it, or you cannot tell later whether a
detail came from the spec or from memory of the code.

**Reading and coding in the same sitting, reference open in another tab.** This is exactly
the setup that turns "I understood how they did it" into "I typed what they wrote." Separate
the two in time, not just in attention.

**Treating a competitor's exact test fixtures or sample dataset as free to reuse.** They are
content like any other; generate your own from the spec.

**"It's just a UI pattern, nobody owns a UI pattern."** Sometimes true, sometimes the reason a
trade-dress or patent claim exists. Gate 5 is there because this skill does not get to decide
which case you are in.
