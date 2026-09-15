# The twenty-section feature specification

Read this at step 5 and keep it open while drafting. Every section is here in the order it is written, with what it has to contain, the discipline it unblocks, and what goes wrong when it is thin. The order is the document's order: intent, then boundary, then behaviour, then the discipline-facing detail, then proof.

Keep every section. A section that does not apply says so and says why — "Not applicable: single-player only, confirmed decision" — because a reader cannot tell a section that was considered and dropped from one that was forgotten.

## Contents

- [How to use the skeleton](#how-to-use-the-skeleton)
- [1. Purpose](#1-purpose)
- [2. Player experience goal](#2-player-experience-goal)
- [3. Scope](#3-scope)
- [4. Out of scope](#4-out-of-scope)
- [5. User flow](#5-user-flow)
- [6. Gameplay rules](#6-gameplay-rules)
- [7. States and transitions](#7-states-and-transitions)
- [8. Parameters and configuration](#8-parameters-and-configuration)
- [9. UI requirements](#9-ui-requirements)
- [10. Visual requirements](#10-visual-requirements)
- [11. Audio requirements](#11-audio-requirements)
- [12. Technical dependencies](#12-technical-dependencies)
- [13. Analytics events](#13-analytics-events)
- [14. Save and load behaviour](#14-save-and-load-behaviour)
- [15. Multiplayer behaviour](#15-multiplayer-behaviour)
- [16. Edge cases](#16-edge-cases)
- [17. Error handling](#17-error-handling)
- [18. Acceptance criteria](#18-acceptance-criteria)
- [19. QA scenarios](#19-qa-scenarios)
- [20. Open questions](#20-open-questions)
- [The skeleton](#the-skeleton)

## How to use the skeleton

Draft section 4 before section 3, then write the rest in order. Mark every statement with its kind as you write it rather than in a pass afterwards, because the pass afterwards is where assumptions get promoted to decisions by fatigue.

One specification covers one feature. A document that covers the whole game is read once, at the start, by nobody who is currently implementing anything.

## 1. Purpose

**Contains.** One paragraph on why the feature exists: the player problem or the business goal it serves, and what changes if it ships. Name the measurable outcome if there is one, and mark it as a decision or an assumption.

**Unblocks.** Everyone. It is the section that lets a reader judge whether a later detail is essential or incidental.

**Thin when.** It restates the feature name — "the purpose of the daily reward is to give a daily reward". That sentence tells a programmer nothing about which behaviours are load-bearing when a trade-off appears at implementation time.

## 2. Player experience goal

**Contains.** What the player should feel, notice or do differently, in the player's terms. This is the one section where adjectives belong, because their job here is to constrain the interpretation of the rules below.

**Unblocks.** Designers, artists, animators and audio — they resolve the hundred small choices the spec does not enumerate, and this is what they resolve them against.

**Thin when.** It is a list of mechanics again. If the section could be pasted into the gameplay rules without anyone noticing, it is not doing its job.

Keep these adjectives here and nowhere else. A criterion in section 18 written as "feels responsive" is untestable; the same word in section 2, paired with the number in section 18, is direction.

## 3. Scope

**Contains.** What this specification covers, as a list of the behaviours, screens, systems and content the feature includes. Name the platforms, the modes and the build it lands in.

**Unblocks.** Producers estimating, and every reader deciding whether a question they have is answered somewhere in this document or somewhere else.

**Thin when.** It is written as a summary of the feature rather than a boundary. Scope is a list of what is inside a line; a summary is section 1.

## 4. Out of scope

**Contains.** Every adjacent thing a reasonable reader could assume is included, each marked as deferred (with the milestone), permanently excluded (with the reason), or owned by a named other feature or specification.

**Unblocks.** Reviewers, producers and every programmer who was about to build a generalisation nobody asked for.

**Thin when.** It is missing, which is the usual case, or when it lists only the obviously absurd. The useful entries are the near misses: the second currency, the offline mode, the controller support, the thing a similar game has.

Write it before section 3.

## 5. User flow

**Contains.** The player's path through the feature, step by step, including entry points, every branch, every exit, and what returns the player to where they came from. Cover the first-time path and the repeat path separately when they differ; they usually do.

**Unblocks.** UI and UX designers, and QA, who turn the branches directly into test paths.

**Thin when.** It describes only the happy path. The branch nobody wrote down is the one that gets invented in code, and it is invented differently in each of the three places it is reached from.

## 6. Gameplay rules

**Contains.** The rules of the feature as numbered statements in the modal verbs — what must happen, what may happen, what cannot happen, and under exactly which conditions. Include costs, limits, cooldowns, eligibility, stacking and interaction with existing systems.

**Unblocks.** Programmers, and designers of every neighbouring feature that will interact with this one.

**Thin when.** It is prose. A rule that is not a numbered statement cannot be referenced in a bug report, an acceptance criterion or a change request, so it is discussed from memory.

## 7. States and transitions

**Contains.** Every state the feature can be in, every legal transition between them with its trigger, and the states from which each transition is illegal. Name what is interruptible, what is not, and what happens to an in-flight transition when the player quits, pauses or is disconnected.

**Unblocks.** Programmers, animators and artists, all three of whom are producing something per state.

**Thin when.** It lists the states and omits the transitions, which is where the defects are. A state diagram with no illegal transitions marked is a diagram that permits everything.

## 8. Parameters and configuration

**Contains.** A table: every tunable value, its default, its valid range, its unit, whether it is live-configurable or build-baked, and who owns it. Anything a designer will want to change without a programmer belongs here.

**Unblocks.** Programmers, who build the configuration surface once instead of three times, and designers, who tune without a build.

**Thin when.** Values are buried in the prose of section 6. They get hard-coded, and the balance pass turns into an archaeology exercise. Choosing the values themselves is `game-balance`; this section is the surface those values are set through.

## 9. UI requirements

**Contains.** Every screen, panel, widget and piece of feedback: what it shows, where it appears, what it does when the underlying value is empty, zero, maximum or unavailable, and what it does at the localisation and platform extremes — longest string, smallest supported resolution, controller and touch input.

**Unblocks.** UI designers and UI programmers.

**Thin when.** It names screens without naming their states. The empty state, the loading state and the error state are where UI work actually goes, and they are the states a wireframe rarely shows.

## 10. Visual requirements

**Contains.** The assets the feature needs, at what fidelity, in which states, with any variation by rarity, faction, level or platform. Note whether existing assets are reused, and whether animation is required for each.

**Unblocks.** Artists and animators, who need a countable list before they can schedule anything.

**Thin when.** It describes the mood rather than the deliverables. Mood belongs in section 2; this section is a list somebody can estimate against.

## 11. Audio requirements

**Contains.** Every sound and music cue, its trigger, whether it loops, what it does when the same trigger fires repeatedly within a short window, how it ducks against other audio, and what happens when the player has audio disabled.

**Unblocks.** Audio designers and implementers.

**Thin when.** It omits the repeat and overlap behaviour, which is the most common source of shipped audio bugs and the cheapest thing to have written down.

## 12. Technical dependencies

**Contains.** What this feature needs that does not exist yet, and what it relies on that does: engine features, backend endpoints, other in-flight features, third-party SDKs, platform capabilities, content pipelines. Mark each as existing, in progress with an owner, or unstarted.

**Unblocks.** Producers ordering the work, and programmers discovering a blocker before the sprint starts rather than in it.

**Thin when.** It lists only technology. A dependency on another team's unfinished feature is the one that moves the date.

## 13. Analytics events

**Contains.** For each event: the name, the exact trigger, the properties with their types and ranges, and the question the event exists to answer. Also say what is deliberately not instrumented, so nobody adds it speculatively.

**Unblocks.** Analysts, and the decision that follows launch.

**Thin when.** It is left for later. Instrumenting after launch loses the baseline permanently — the pre-feature weeks cannot be re-measured, so the first evaluation of the feature is anecdote. An event with no question behind it is the opposite failure: cost with no payoff, and a payload nobody queries.

## 14. Save and load behaviour

**Contains.** Exactly what the feature persists, what it restores on load, what happens when the field is absent because the save predates the feature, what happens when the game is closed or crashes mid-flow, and whether the state is per profile, per slot, per device or on a server.

**Unblocks.** Programmers, and everyone who would otherwise find out at the first patch that the feature changed the save format.

**Thin when.** It says "state is saved". Schema versioning, the migration step, the write policy and cloud conflicts are `game-save-system`; this section names the requirement precisely enough that that work can be scoped.

## 15. Multiplayer behaviour

**Contains.** Whether the feature exists in multiplayer at all; what other players see of a player using it; what the server must validate rather than trust; what happens on disconnect, rejoin, host migration or a mid-session party change; and whether the feature is shared, per player or spectatable.

**Unblocks.** Network programmers, and the architecture decision that cannot be revisited cheaply.

**Thin when.** It says "single-player for now" with no statement of whether multiplayer is ever intended. A feature built client-authoritative because nobody asked the question cannot be made authoritative later without a rewrite. The authority model, prediction and reconciliation are `game-netcode`.

## 16. Edge cases

**Contains.** The specific situations the main flow does not cover, each with the correct behaviour rather than a note that the case exists: zero of a resource, maximum of it, the feature used at the exact moment it expires, two inputs on the same frame, the player at the level cap, an empty inventory, a first-time user with no history, a returning user whose data is from an older build.

**Unblocks.** QA and programmers equally.

**Thin when.** It lists cases without deciding them. "What if the inventory is full?" in this section is an open question wearing a disguise — move it to section 20 with an owner, or answer it here.

## 17. Error handling

**Contains.** Every failure the player can reach and what the game does about it: a network call that fails or times out, a purchase that does not complete, a save that cannot be written, content that is missing or corrupt, a permission that is denied. Say what the player sees, whether the action is retryable, whether progress is lost, and what is logged.

**Unblocks.** Programmers, QA and support.

**Thin when.** It assumes the backend answers. Every remote call has a failure path and the player is in it more often than the design imagines; an unhandled one becomes a silent hang that reads as a frozen game.

## 18. Acceptance criteria

**Contains.** A numbered list of statements that someone who did not write the specification can mark as passed or failed from the build alone. Each names the observable behaviour, the condition, and any number with its unit and the device or configuration it applies to.

**Unblocks.** QA, and the conversation about whether the feature is done.

**Thin when.** The criteria contain adjectives. "Responsive" cannot be failed by anyone but the author; "input-to-first-animation-frame latency under 100 ms at 60 fps on the minimum-spec device" can be failed by a stranger with a capture card.

Cover the rules in section 6, the edge cases in section 16 and the error paths in section 17. A rule with no criterion is a rule nobody will check.

## 19. QA scenarios

**Contains.** The paths to walk, in order, including the ones that are tedious: first-time entry, repeat entry, entry with the feature already complete, interrupted mid-flow, resumed from a save written before the feature existed, on the minimum-spec device, with the network disabled, and with the longest localised strings.

**Unblocks.** QA planning, and the test estimate a producer needs.

**Thin when.** It repeats the acceptance criteria. Criteria say what is true of a finished build; scenarios say what a person does to find out.

## 20. Open questions

**Contains.** Every unresolved question, each with the person who can answer it, the date the answer is needed, and whether it blocks a start or only a finish. When one is answered, move the answer into the section it belongs to as a confirmed decision and leave a line here saying what it became.

**Unblocks.** Producers, who chase them, and everyone else, who now knows which parts of the document are still moving.

**Thin when.** It is empty on a first draft. That almost never means there are no questions; it means the author answered them privately, which is the same as answering them at random.

## The skeleton

Copy this, keep the order, and fill it in.

```markdown
# Feature: <name>

Status: draft | in review | approved
Owner: <name>    Last updated: <date>
Legend: [decision] confirmed | [assumption] unverified | [recommendation] proposed | [open] unanswered

## 1. Purpose
## 2. Player experience goal
## 3. Scope
## 4. Out of scope
## 5. User flow
## 6. Gameplay rules
## 7. States and transitions
## 8. Parameters and configuration
## 9. UI requirements
## 10. Visual requirements
## 11. Audio requirements
## 12. Technical dependencies
## 13. Analytics events
## 14. Save and load behaviour
## 15. Multiplayer behaviour
## 16. Edge cases
## 17. Error handling
## 18. Acceptance criteria
## 19. QA scenarios
## 20. Open questions
```
