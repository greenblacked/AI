# The four modes, in full

Read this when a draft resists being one mode, or when splitting a page that has grown
into two or three. The workflow's table is the summary; this is the decision procedure.

## Contents

- [Placing a document in one question](#placing-a-document-in-one-question)
- [Tutorial](#tutorial)
- [How-to](#how-to)
- [Reference](#reference)
- [Explanation](#explanation)
- [Worked splits](#worked-splits)
- [Linking the four together](#linking-the-four-together)

## Placing a document in one question

Two axes decide it. Is the reader **acting** or **understanding**? Are they **studying**
(no immediate goal) or **working** (a goal right now)?

| | Studying | Working |
| --- | --- | --- |
| **Acting** | Tutorial | How-to |
| **Understanding** | Explanation | Reference |

Ask the question about the reader in the document's own opening sentence. If the answer is
"both", you have two documents. The most reliable symptom of a mixed document is a
paragraph beginning "of course, you could also…" inside a numbered step, or a section
heading that reads like a topic rather than a goal.

## Tutorial

**The reader is learning and has no basis for any choice you offer them.**

- One path only. No alternatives, no "depending on your setup", no optional steps.
- It must work end to end, on a clean machine, today. A tutorial that fails at step 6 is
  worse than none, because it teaches the reader the system is broken rather than that
  they are new.
- Every step produces something the reader can see, so they know they are still on track.
- Concrete and specific: a fixed project name, fixed values, fixed output. Generality is
  the reader's job later, not the tutorial's job now.
- It ends with a visible win and a single link to the how-to that generalises it.

The obligation is pedagogical rather than informational. Simplifications the expert would
object to are acceptable if they are honest and if the tutorial says the real picture
comes later.

## How-to

**The reader is competent, has a goal right now, and is under some time pressure.**

- Titled by the goal in the reader's words: "Rotate the signing key", not "Key management".
- Numbered steps, one action per step, in execution order.
- Conditions come before the action they govern. "If the cluster is multi-region, run X
  first" after the step is read too late to be acted on.
- Assumes competence: it does not explain what a certificate is, and it does not reassure.
- Names the finished state so the reader knows to stop.
- It may branch, unlike a tutorial, but each branch must be decidable from information the
  reader already has.

If a how-to needs three paragraphs of rationale to be followable, the rationale goes in an
explanation document linked from the top, and what remains is one sentence naming the
constraint.

## Reference

**The reader knows what they want and needs a fact, quickly and exactly.**

- Structured by the thing being described — the modules, the endpoints, the flags — not by
  a narrative the author found natural.
- Mechanically ordered: alphabetical, or mirroring the code's own structure. A reader
  scanning for one entry must be able to predict where it is.
- Complete. Partial reference is worse than none, because a missing entry reads as an
  absent feature.
- Uniform in shape: every entry carries the same fields in the same order, so scanning
  works.
- Neutral and dull. Description, not instruction; no worked narrative.
- Generated from the source wherever the source holds the truth — a CLI's own help, an
  OpenAPI document, a config schema. Hand-written reference drifts the moment the code
  changes, and nothing fails when it does.

## Explanation

**The reader is away from the keyboard and wants to understand why.**

- Organised by topic and argument rather than by task.
- Names the alternatives that were considered and why the current design won, including
  the constraints that no longer apply — that is the part nobody can reconstruct later.
- Admits history: the shape of most systems is partly a record of what was easy at the
  time, and saying so prevents a reader inferring a design intent that never existed.
- Carries no commands. A reader in this mode is not in a position to run them.
- Bounded in scope: one question per document, answered.

Where the document is really recording a decision with alternatives, a decision date and
consequences, it is an architecture decision record and belongs to `decision-record`
instead. Explanation describes how the system is and why; the decision record captures the
moment a choice was made and what was rejected.

## Worked splits

**A README that grew into everything.** Keep: what it is, how to run it, how to test it,
who owns it, where to go next. Move the configuration table to reference, the architecture
prose to an explanation page, the step-by-step first deployment to a how-to, and the
"getting started for new team members" narrative to a tutorial.

**A how-to with a design essay in the middle.** The essay is almost always one constraint
the steps depend on. Reduce it to a single sentence stating the constraint, link the
explanation, and let the steps run unbroken.

**A tutorial with options.** Every "or you can use X" is what stalls a beginner. Pick the
one you would pick, remove the rest, and add one link at the end to the how-to covering
the alternatives.

**Reference with narrative.** The examples woven between entries make completeness
impossible to audit — nobody can see which entries are missing. Move examples into a how-to
and leave the table.

## Linking the four together

The four modes fail differently when isolated: reference nobody can enter, tutorials that
lead nowhere, how-tos that assume context the reader lacks.

- Tutorial ends with one link to the how-to that generalises what was just done.
- How-to links out to reference for the exhaustive option list, and to explanation for the
  one constraint it asserts.
- Reference links to the how-tos that use each area, and nowhere else.
- Explanation links to the how-to that puts the idea into practice.

One link per direction. A page of links at the bottom of every document is a navigation
structure, and a navigation structure that nobody maintains is the next thing to rot.
