# Statement kinds and modal verbs

Read this at steps 3 and 4, and again during the review pass. A specification is a set of statements, and most of the damage a specification does comes from two confusions: a reader who cannot tell a decision from a guess, and a reader who cannot tell a requirement from a preference. Both are fixed by notation rather than by care.

## Contents

- [The four statement kinds](#the-four-statement-kinds)
- [Marking them inline](#marking-them-inline)
- [The six modal verbs](#the-six-modal-verbs)
- [Words that look like requirements and are not](#words-that-look-like-requirements-and-are-not)
- [Rewrites](#rewrites)
- [Reviewing a draft for statement discipline](#reviewing-a-draft-for-statement-discipline)

## The four statement kinds

**Confirmed decision.** Someone with the authority to decide has decided. It may still change, but changing it is a change request rather than a conversation. Build against it.

**Assumption.** Taken as true so the document could continue, and not verified. Every assumption carries an owner and a date on which it becomes a decision or an open question. An assumption that survives to implementation unmarked is the most expensive defect this document can contain, because the work built on it looks finished.

**Recommendation.** The author's proposal, offered to be overruled. A recommendation names the alternative it beat and why, so the person overruling it does not re-derive the comparison. If the reasoning is long, that is a `decision-record` and this document links to it rather than restating it.

**Open question.** No answer yet. It carries the person who can answer, the date it is needed, and whether it blocks a start or only a finish.

The distinction that matters most is decision against assumption. A team can work productively on a marked assumption — they build the seam differently, they schedule the verification, they do not couple everything to it. The same team working on an unmarked assumption behaves exactly as if it were settled, and finds out in review.

## Marking them inline

Mark at the statement, not at the paragraph or the section. A reader copies one line into a ticket, and the mark has to travel with it.

```markdown
- Dash must have a 1.2 s cooldown. [decision]
- Cooldown is shared across all movement abilities. [assumption — Priya, confirm by 14 Mar]
- Cooldown should be shown as a radial sweep rather than a number, because the number
  competes with the damage readout. [recommendation — alternative: numeric countdown]
- Does dash cooldown persist across a checkpoint reload? [open — Sam, needed before UI work]
```

Any notation works as long as it is one per statement and defined once at the top of the document. What does not work is grouping by kind — an "assumptions" section at the end is read once and then forgotten, while the unmarked sentences in the body keep being read as decisions.

Two habits keep the marking honest:

- When you write a decision, be able to name who made it. If you cannot, it is a recommendation or an assumption.
- When you cannot decide between two kinds, take the weaker one. Downgrading an assumption to a decision later is a one-line edit; discovering a decision was an assumption is three weeks.

## The six modal verbs

| Verb | Meaning | Test for whether it is the right verb |
| --- | --- | --- |
| must | Required; the build is wrong without it | Would you reject the build over it |
| should | Expected; a deviation needs a written reason | Could a sensible implementer skip it and still be right |
| may | Permitted and optional | Would you accept both outcomes without comment |
| cannot | Prohibited; the system prevents it | Is it enforced, or merely not offered |
| only when | The sole condition under which the thing is permitted | Can you name every other condition it excludes |
| except when | The sole carve-out from a rule already stated | Is the rule it modifies stated immediately above |

Use no others. "Will", "needs to", "has to", "is supposed to", "ideally", "would be nice" and "we want" each read as a different obligation to different people, and none of them is defined.

Two failure directions, both common:

- **A "should" that means "must".** The implementer skips it legitimately, the reviewer approves, and the missing behaviour reaches QA as an ambiguity rather than a bug.
- **A "must" that means "should".** Work happens that nobody wanted, and the first person to question it is told it is in the spec.

`cannot` deserves particular care. It is a claim about enforcement, so it belongs to an implementation: "the player cannot dash while stunned" means the code rejects the input, not that the UI hides the button. If the prohibition is not enforced, write "must not be offered" and say what happens if it is reached anyway.

`only when` and `except when` each introduce exactly one condition. Two conditions in one sentence produce a rule whose truth table nobody has worked out; write two statements.

## Words that look like requirements and are not

- **Support.** "The shop must support gifting" names no behaviour. Support how, to whom, with what limits, and what happens when it fails.
- **Handle.** "The client must handle a disconnect" is section 17 with the content removed. Handle by doing what, and what does the player see.
- **Properly, correctly, appropriately, gracefully.** Each defers the definition to whoever implements it, which is the person with the least context about what correct means.
- **Etc., and so on, and similar.** They make an enumeration unbounded, so the implementer picks a boundary and QA picks a different one.
- **As needed, where appropriate, if necessary.** These convert a requirement into a judgement call without saying whose judgement.
- **Fast, smooth, responsive, intuitive, juicy.** Legitimate in the player experience goal. In a rule or an acceptance criterion they are untestable, so convert them to a number, a duration, a count or an observable ordering.

## Rewrites

**A gameplay rule.**

Badly:

> The player should be able to use the dash ability fairly often, but not so often that it trivialises combat. It shouldn't work while stunned.

Well:

> - Dash must have a cooldown of 1.2 s, starting on the frame the dash begins. [decision]
> - Dash cannot be initiated while the player is stunned, rooted or in the death state; input received in those states must be discarded rather than queued. [decision]
> - Dash may be used while airborne. [decision]
> - Cooldown should not be reduced by any existing item, because the combat pacing target assumes a floor of 1.2 s. [recommendation — alternative: allow reduction to 0.8 s via the movement item line]

The rewrite turns one sentence into four statements, three of which a programmer would otherwise have had to invent, and exposes an item interaction that the original did not mention.

**An acceptance criterion.**

Badly:

> The shop should load quickly and show an error if something goes wrong.

Well:

> - The shop must render its first row of items within 800 ms of the open input on the minimum-spec device, measured from a cold app start. [decision]
> - When the catalogue request fails or exceeds 5 s, the shop must show the retry panel with the failure reason, and must not show an empty catalogue. [decision]
> - The retry action must re-issue the request and must be usable an unlimited number of times. [decision]
> - Whether the shop caches the previous catalogue for offline display is open. [open — Ana, needed before the offline milestone]

The original is one sentence that no tester can fail. The rewrite is testable by someone who has never spoken to the author, names the device and the timeout, and surfaces a question the original hid.

**A save statement.**

Badly:

> Progress is saved.

Well:

> - The player's current tier, accumulated points and claimed-reward ids must be persisted per profile. [decision]
> - On load, a save with no track data must be treated as tier 0 with zero points, and must not block entry to the feature. [decision]
> - Points earned since the last checkpoint may be lost if the game exits without a save; the feature must not rely on them for anything the player has already been shown. [decision]
> - Schema version, migration step and write policy are specified by the save system work, not here. [decision]

## Reviewing a draft for statement discipline

Five passes, each cheap, each finding a different defect:

1. Search for every unmarked sentence in a normative section. Each one is being read as a confirmed decision; decide whether it is.
2. Search for "will", "needs to", "has to", "ideally" and "we want", and replace each with one of the six verbs.
3. Search for every "should" and ask whether you would reject a build over it. If you would, it is a "must".
4. Search for the adjective list above. Each occurrence outside the player experience goal is either a number waiting to be chosen or an open question.
5. Count the confirmed decisions against the assumptions and open questions. A first draft that is all decisions has not been reviewed; it has been asserted.
