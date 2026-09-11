---
name: codebase-orientation
description: "Get oriented in a codebase you did not write, in a fixed order: what it does and for whom before how it is built, the entry points, one real request traced end to end, a named behaviour located in the code, the tests read as the specification, the history read as evidence of what churns and what has never moved, and the local dev loop run once — then separate live code from dead, generated and vendored code, and finish with a written map plus one small change. Use this skill whenever someone lands in unfamiliar code and asks \"where do I even start with this repo\", \"how does this service actually work\", \"I just inherited this project\", \"where does X actually happen in here\", or \"what should my first change be\". Do not use it to chase a specific failure (debugging), judge a diff (code-review), restructure code already understood (refactoring), or write the documentation afterwards (technical-docs)."
allowed-tools: Read, Grep, Glob, Bash(git:*), Bash(rg:*), Bash(find:*), Bash(make:*), Bash(npm:*)
---

# Codebase Orientation

Orientation is finished when you can name the system's purpose in one sentence, trace one real request from entry point to persistence without opening a file you have not already seen, and land a small change that passes the project's own checks.

Reading an unfamiliar codebase goes wrong in five recognisable ways. People start at the top of the directory listing and read alphabetically, which spends the first hour on `adapters/` and never reaches the thing that makes the system worth running. They read structure instead of behaviour, so they can recite the layer names and still cannot say what happens when a user clicks buy. They treat every file as equally real, so a dead module kept for three years reads as load-bearing and a vendored copy of someone else's library reads as house code to be understood. They trust the README, which describes the system as it was at the commit where someone last cared. And they finish with a summary nobody can act on, having never run the thing, so the first real change is still a first day. The order below is built so that each step produces a falsifiable claim, and so that the exit condition is a change that compiled rather than a document that reads well.

## Scope

Use for: landing in a repository you did not write; inheriting a service whose author has left; picking up an open-source project to contribute to; finding where a named behaviour lives before changing it; deciding what the first safe change is; writing the orientation note the next person reads.

Do not use for: chasing a specific reported failure to its cause (`debugging`), judging a specific diff or pull request (`code-review`), restructuring code whose behaviour you already understand (`refactoring`), choosing what tests a module needs (`test-design`), writing the durable documentation afterwards (`technical-docs`), or planning a move off the platform the code runs on (`plan-platform-migration`).

## Workflow

Work in order. Each step is cheap and each one narrows the next; taken out of order they all cost more.

### 1. Establish what the system does and for whom

Before any code. Spend ten minutes and answer three questions in writing: who uses this, what do they get, and what breaks for them if it stops. Sources, in order of trustworthiness: the deployed product or its API responses, the issue tracker's last twenty closed items, the on-call alerts and dashboards, the README last.

The README is a claim, not evidence. Check its date against `git log -1 --format=%ci -- README.md`; a README untouched for two years describes a system two years gone. Record every claim you could not corroborate — those are the questions to ask a human later, and they are worth more than the answers you found yourself.

### 2. Find the entry points

An entry point is anywhere control enters from outside the process: an HTTP route table, a CLI argument parser, a message-queue consumer, a cron or scheduled job, a serverless handler, a `main` function. Everything else in the repository exists to serve one of these.

```bash
rg -n "func main|if __name__|app\.(get|post|put|delete)|@app\.route|addEventListener" --type-add 'src:*.{go,py,ts,js,rb,java,rs}' -tsrc
rg -n "schedule|cron|consumer|subscribe|handler" -g '!**/vendor/**' -g '!**/node_modules/**'
```

Read the deployment manifests too — a Dockerfile `CMD`, a Procfile, a Kubernetes `command:`, a systemd unit. They name the process that actually runs, which is regularly not the one the directory layout suggests. Write the list down and stop; do not follow any of them yet.

### 3. Trace exactly one real request end to end

This is the step that produces understanding, and it is the one people skip. Pick the single most important path — the checkout, the ingest, the nightly reconcile — and follow it from the entry point through every hop to the point where state changes or a response is returned. One path, all the way, beats five paths half way.

At each hop record four things: the file and function, what the data looks like coming in, what transformation happens, and where it goes next. Where the trace jumps through dynamic dispatch, dependency injection or a message bus, the static read will lose it: run the thing with a debugger breakpoint or a log line rather than guessing which of the four implementations of the interface is wired in. `references/tracing.md` covers the techniques for the hops static reading cannot cross, including how to use a stack trace as a free map.

The trace is done when you can draw it without the editor open.

### 4. Locate a named behaviour

Given a behaviour described in a user's words — "the retry email", "the 15% discount", "the export is capped at 1000 rows" — find the code. Search in this order, because it is cheapest first:

| Search | What it finds | When it wins |
| --- | --- | --- |
| The literal user-visible string, in every locale file and template | The presentation layer, then its callers backwards | The behaviour has any text attached, which is most user-facing behaviour. |
| The magic number or constant (`1000`, `0.15`, `15 * 60`) | The rule itself, often in config rather than code | The behaviour is a threshold, limit or rate. |
| The domain noun (`refund`, `entitlement`) across filenames, not contents | The module that owns the concept | The codebase names things after the domain rather than after patterns. |
| `git log -S'<string>'` for the string's introduction | The commit and the pull request that added it, with the reasoning | Every earlier search returned too many hits or none. |
| The database column or event name | The write path, from the schema backwards | The behaviour persists something and the code layer is heavily indirected. |

If four searches fail, the behaviour is probably not in this repository — it is in a sibling service, a feature flag, a configuration store or an operator's dashboard. Say that rather than continuing to search; a wrong belief about which repository owns a behaviour costs days.

### 5. Read the tests as the specification

Tests are the only documentation that fails the build when it becomes untrue, which makes them the most reliable prose in the repository. Read them in this order: the end-to-end or integration tests for the path you traced in step 3, then the unit tests for the module you found in step 4, then the fixtures.

What each kind tells you:

| Artefact | What to extract |
| --- | --- |
| Integration test names | The behaviours the team considers contractual, stated in their vocabulary rather than yours. |
| Test fixtures and factories | The shape of real data, including the fields that are always present and the ones nobody sets. |
| Assertions on error paths | The failures the system is designed to survive, which is the fastest route to its actual risk model. |
| A module with no tests at all | Either dead, or the scariest code in the repository. Step 6 tells you which. |
| A test marked skipped or quarantined | A behaviour that broke and was never fixed. Read the commit that skipped it. |

### 6. Read the history as evidence

Structure tells you how the code is arranged; history tells you which parts are alive, which are feared, and which have already been tried.

```bash
git log --format=%ad --date=short | tail -1                       # how old the codebase really is
git log --since='12 months ago' --name-only --format= | sort | uniq -c | sort -rn | head -30
git log --since='12 months ago' --format='%an' | sort | uniq -c | sort -rn | head
git log --oneline --grep='revert' -i --since='24 months ago'
```

Read the four results as four different findings. A file in the top ten by churn is where the requirements are still moving, so it is where your change is most likely to be welcome and least likely to be final. A file untouched for three years is either stable infrastructure or abandoned, and the test suite decides which. A file with exactly one author who no longer appears in recent commits is an ownership hole, and it is the one to ask about before touching. A reverted change is the strongest signal in the repository: someone tried your idea already and it failed in a way the tests did not catch, so read the revert commit before proposing it again. `references/history.md` has the fuller set of queries, including per-file blame ageing and how to read a repository that was squashed or imported from another VCS and therefore has no real history at all.

### 7. Run the local dev loop once

Install, build, test, run, and make the smallest visible change you can — alter a log line, a string, a constant — and see it take effect. Time each stage and write the times down.

This is not a formality. It surfaces the undocumented prerequisite, the service that must be running, the environment variable with no default, and the test that has been failing on everyone's machine for months. It also gives you the cycle time you will be paying for every subsequent change: a 40-second loop and a 25-minute loop demand completely different working styles, and choosing the wrong one is how a first week disappears.

If the loop does not work, that is the finding. Fix it and write down what was missing — the next person hits the same wall, and this is the highest-value contribution a newcomer can make.

### 8. Separate the real code from the rest

Not everything in the tree is the team's code, and not everything the team wrote is still executed.

| Signal | Reading | What to do |
| --- | --- | --- |
| A path in `.gitattributes` marked `linguist-generated`, or a header saying "do not edit" | Generated output committed for convenience | Find and read the generator instead; edits here are overwritten on the next build. |
| `vendor/`, `third_party/`, `node_modules/`, a licence file inside the directory | Someone else's code | Read it only to understand behaviour, never to change it. A local patch here is invisible to dependency tooling. |
| No inbound references from any entry point traced in step 2 | Probably dead | Confirm with a production log or metric before deleting; reflection and dynamic imports hide real callers from search. |
| Referenced only by its own tests | Dead with a support system | The tests pass forever and prove nothing. Candidate for deletion, not for study. |
| A feature flag that has been fully on or fully off for over a year | One side of the branch is dead | Read which side; the other is the system's real behaviour. |
| Two modules with similar names, one with recent commits | A migration nobody finished | Work in the new one, confirm which by checking which the entry point reaches. |

Deleting dead code is a separate job and belongs to `refactoring`. Here you are only marking it, so that your map does not send the next person into a wing of the building with no floor.

### 9. Write the map, then make one change

Produce the orientation note in the shape below and put it in the repository, not in a chat message. Then make one small, real change — the smallest genuine improvement you found while orienting, which is usually a missing dev-setup step, an untested edge you can cover, or a stale comment contradicted by the code — and take it through the project's own review and checks.

The change is the proof. A map with no change behind it has not been tested against reality, and the first thing it will be wrong about is exactly the thing that matters.

## How deep to go, and when to stop

Match the depth to the change you are about to make, and stop there. A newcomer trying to understand everything before touching anything is the most common way orientation consumes a month and produces nothing.

| The change ahead | Stop after | Skip |
| --- | --- | --- |
| A one-line fix with a reproducing test | Steps 4, 5 and 7 | The full trace; you need the one hop, not the path. |
| A new endpoint or job alongside existing ones | Steps 1 to 7, tracing the nearest sibling | The history forensics; copy the working neighbour. |
| Changing behaviour on a hot path | All nine steps, tracing that exact path | Nothing. |
| Deciding whether to rewrite or keep | Steps 1, 6 and 8 | The deep trace; churn, ownership and dead weight answer this. |

## Anti-patterns

**Reading the repository alphabetically.** The directory listing is an artefact of naming, not of importance, so this spends the freshest hours on the least load-bearing code and arrives at the core with the attention already gone. Start at an entry point and follow control flow.

**Mapping structure instead of behaviour.** A diagram of the layers can be produced in twenty minutes and is worth almost nothing: it survives any rewrite of what the system actually does. One traced request tells you more than a complete module inventory.

**Trusting the README over the code.** The README describes the system at the commit where someone last cared about explaining it, and nothing fails when it drifts. Check its last-modified date against the code it describes, and treat every uncorroborated claim as a question.

**Studying vendored or generated code as though it were house code.** Hours spent understanding a checked-in client generated from a schema, which will be regenerated and silently discard any edit made to it. Identify the boundary in step 8 before reading deeply.

**Declaring code dead from search alone.** Reflection, dynamic imports, string-keyed dispatch and configuration-driven wiring are invisible to grep, and the deletion that follows takes out a quarterly job nobody was watching. Corroborate with a production log line or a metric before acting.

**Skipping the dev loop until the first real change.** The undocumented prerequisite is discovered under deadline instead of during orientation, and the cost lands on the day it is most expensive. Run it on day one, when finding a broken loop is a contribution rather than a delay.

**Orienting without ever asking a person.** Some of what you need is not in the repository at all — why the second implementation exists, which customer the special case is for, which service actually owns the behaviour. Batch the questions the first eight steps produced and ask once; arriving with specific questions costs a colleague ten minutes, arriving with none costs them a week.

**Producing a file-by-file summary.** A restatement of the directory tree is something anyone can generate and nobody can act on. The deliverable is the trace, the map of which code is live, the list of open questions, and one merged change.

**Keeping the map in your head.** The orientation is done in a week and forgotten in a month, and the next joiner pays the whole cost again. Write it into the repository where the next person will trip over it.

## Output format

```markdown
# Orientation: [repository or service name]

**Oriented by:** [name] · **Date:** [YYYY-MM-DD] · **Commit:** [sha]

## What this is
[One sentence: who uses it, what they get, what breaks if it stops.]

## Entry points
[Each one: the trigger, the file, and what it is for.]

## The main path, traced
[The hops from entry to state change, file and function per hop.]

## Where things live
[Behaviour to location, for the handful of behaviours anyone asks about.]

## Live, dead and not ours
[Generated paths, vendored paths, code with no inbound callers, unfinished migrations.]

## The dev loop
[The exact commands, their real timings, and every prerequisite the README omits.]

## History says
[Highest-churn files, files untouched for years, ownership holes, anything reverted.]

## Open questions
[What the code could not answer, and who to ask.]

## First change
[The change made, the link to it, and what it proved or disproved about the map above.]
```

## Reference files

- `references/tracing.md` — read when step 3 loses the thread: crossing dependency injection, event buses, queues and dynamic dispatch, using a debugger or a temporary log line as a static-reading substitute, and reading a stack trace as a ready-made map of the path.
- `references/history.md` — read at step 6, and again before proposing anything that feels obvious: the churn, blame-ageing, ownership and revert queries in full, plus how to orient in a repository whose history was squashed or imported and carries no evidence.
- `references/first-change.md` — read at step 9: how to choose a first change that is genuinely small and genuinely useful, what to do when the dev loop is the thing that is broken, and how to write the orientation note so the next joiner starts where you finished.
