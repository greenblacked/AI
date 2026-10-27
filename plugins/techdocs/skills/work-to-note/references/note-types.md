# Note types

Read this in step 1 to choose the type, and in step 5 for the section shape. These shapes are the defaults of a vault that files notes by kind; the vault's own standard wins where it differs.

## The seven types

| Type | Usual folder | Use it for | Section shape | Typical length |
| --- | --- | --- | --- | --- |
| `adr` | `adr/` | One decision, the context that forced it and the consequences accepted | Context, Decision, Consequences, Alternatives considered, Validation, References | 800 to 900 words |
| `pattern` | `patterns/`, and some in `ai/` and `compliance/` | A reusable way of doing something, with the reason it works and how it fails | Topic sections, Failure modes, Related | about 1,500 words |
| `tool` | `tools/` | A comparison or evaluation of tools for one job | At a glance, Where each is stronger, When to choose which, Operating costs, Our choice | about 800 words |
| `standard` | `standards/` | A rule the team follows, with its checklist | Principles, rule sections, Checklist, Sources, Related | 2,000 to 2,400 words |
| `runbook` | `runbooks/` | A procedure for the moment someone has to do the thing | When to use, Preconditions, Steps (numbered `###`), Validation, Rollback, Troubleshooting | about 1,000 words |
| `guide` | `ai/`, `management/`, `learn/`, `compliance/` | Teaching a topic or a way of working, including lessons | Principles or concepts, worked examples, Pitfalls, Sources | 800 to 1,300 words; lessons about 5,300 |
| `reference` | `architecture/` | A target design and its trade-offs | Goals, design sections, Failure modes, Pitfalls, Verify, Sources | about 3,200 words |

The vault may also accept a generic `note` type. Do not use it for work notes: every note here has a more specific home, and a note nobody can classify is usually two topics.

Folders group by subject as well as by kind, so a type can appear in several folders: look at where the neighbouring notes on the topic live before choosing, and follow the vault's standard where it differs. File names are lowercase kebab-case with no numeric prefix, except ADRs, which are `NNNN-short-kebab-title.md` with a four-digit number that is never reused. A comparison uses `-vs-` in the name.

## Choosing between two that fit

- Work that ended in a choice between options is an `adr` if one decision is the point, and a `tool` if the comparison is the point and the choice is local.
- Work that found a way of doing something that generalises is a `pattern`. If the same work is a sequence someone will execute under pressure, it is a `runbook`; write the steps, not the argument.
- A rule everyone must now follow is a `standard`. A preference one team follows is a `pattern`.
- A fix that taught a method (how to read a graph, how to triage) is a `guide`; the same fix that is a repeatable procedure is a `runbook`.
- If two fit equally, pick the one a reader would search for, and link the other one.

## When the output is not a note

- **A lesson-ledger entry.** The work revealed a defect class that review or a gate should catch next time: a kind of mistake, with a shape specific enough to search for. Write the entry as `references/lesson-entry.md` describes, in the same change as the fix. A pattern note can sit beside it when the remedy is also a reusable technique.
- **A postmortem.** Customers or users were affected and the value is the timeline, the contributing causes and the action items. Hand off to `postmortem`; this skill covers the reusable technique that came out of it, not the incident record.
- **Nothing.** The fix was one line, the cause was a typo, nothing would help a stranger, or the claim the note would rest on was never checked. A short commit message is the right record. Say so and stop; a note nobody needs costs every future reader a search result.

## Length and focus

Length follows the type; do not pad to reach it, and do not compress a standard into a paragraph. A note that runs past about three screens without a table of contents shape is probably two topics. The title is sentence case and names the lesson, not the day.
