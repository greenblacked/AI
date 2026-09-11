---
name: release-notes
description: "Turn a range of merged changes into release notes the affected reader can act on, and run the release gates: derive the range from the last shipped tag, not a date, sort entries by who is affected instead of by component, write each breaking change with its migration, cut the noise, resolve the ambiguous semantic-version call, and clear the pre-publish checklist — version bumped, tag matching the artefact, rollback stated, the tested build the one shipped. Use this skill whenever notes, a changelog or an upgrade guide are due for a version, or someone says \"write the release notes for 2.4\", \"what changed since last release\", \"is this a minor or a major\", or \"draft the changelog\". Not for how to roll a change out (release-strategy), a one-way switchover (cutover), schema steps (db-migration), a weekly status (status-update), or recording a decision (decision-record)."
allowed-tools: "Bash(git:*), Bash(gh:*), Bash(jq:*), Read, Write, Edit, Grep, Glob"
---

# Release Notes

Release notes are finished when every reader who has to do something because of this release can find, in one pass, what they must do and by when — and when the artefact carrying that version is provably the one that was tested.

The job goes wrong in five recognisable ways. The range is derived from a date or a branch instead of from the last tag that actually shipped, so the notes claim changes that went out a fortnight ago and silently omit a cherry-pick that did not. The entries are sorted by component, which is the author's mental model and nobody else's, so a breaking change to the client library sits in a list of storage-layer refactors where the person who has to migrate will never see it. The breaking change is announced without the migration, leaving a reader who knows they are affected and not what to do. Everything merged gets an entry, including sixty dependency bumps and a typo fix, until the four lines that matter are unfindable and readers stop opening the notes at all — which is the real cost, because it also destroys the channel for the next genuinely dangerous release. And the version is chosen by the size of the diff rather than by the compatibility promise, so a behavioural change that breaks a caller ships as a patch and lands in production through an automatic upgrade. This procedure fixes the range first, sorts by audience, forces the migration to sit inside the breaking change, and ends on a checklist that ties the version to the tested artefact.

## Scope

Use for: assembling notes or a changelog for a version or a deploy; deciding what belongs in them and what is noise; writing the breaking-change and migration section; choosing the version number when semantic versioning is ambiguous; writing an upgrade guide for a major; running the pre-publish checklist and stating the rollback; producing the different cuts a release needs for different audiences.

Do not use for: choosing how the change reaches users — flags, rings, canaries and bake times, which is `release-strategy`; a one-way switchover with a point of no return, which is `cutover`; the expand-and-contract steps of a schema change, which is `db-migration`; a multi-phase platform migration, which is `plan-platform-migration`; a recurring progress report to stakeholders, which is `status-update`; recording why a choice was made, which is `decision-record`; or writing product or API documentation, which is `technical-docs`.

The upgrade guide sits on the line with `technical-docs` and splits by what the document is tied to. A guide scoped to one version transition — what breaks going from 1.x to 2.0, the migration for each break, the deadline on the old path — is part of shipping that release and belongs here, whoever it is written for. A durable page in the documentation set that is owned, dated and re-verified after the release has shipped belongs to `technical-docs`. Write it here first; hand it over when it outlives the release.

## Hard gates

Each one is argued in the anti-patterns at the end; here they are the list you check against.

1. The range comes from the last shipped tag.
2. A breaking change without its migration is not published.
3. The artefact shipped is the artefact tested.
4. The tag points at the commit that was built.
5. Every release states its rollback, including "none — this release is not reversible".
6. Noise is cut before the notes are written, not after.

## Workflow

### 1. Derive the range from what actually shipped

The previous release is the last tag whose artefact reached production, which is not always the highest version number and not always on this branch.

```bash
git describe --tags --abbrev=0                 # the most recent tag reachable from here
git tag --sort=-creatordate --merged HEAD | head
git log --oneline --no-merges v2.3.0..HEAD
gh release view v2.3.0 --json tagName,publishedAt,isDraft
```

Three things break a naive range and all three are common. A hotfix released from a maintenance branch is in production and not in your range, so its fix appears to be new in this release and its author is confused. A commit merged before the previous tag but cherry-picked afterwards appears twice unless you compare by change rather than by commit. And a release that was tagged and then pulled leaves a tag that never shipped, which is the one case where the highest tag is the wrong boundary.

Reconcile against the deploy record, not only against git. Name the previous version explicitly in the notes so the next person can verify the boundary rather than re-deriving it.

### 2. Sort by who is affected, not by what changed

Component ordering is the default because it falls out of the repository layout. It is the wrong axis, because a reader arrives with a role and needs to know whether this release creates work for them.

| Audience section | What belongs in it | Why it is first or last |
| --- | --- | --- |
| Action required | Breaking changes, removals, anything with a deadline, and any change requiring a configuration or data step at upgrade | First, always. A reader who reads nothing else must still find the work they cannot avoid |
| Operators | Configuration defaults that moved, new required environment or secrets, resource or capacity changes, changed observability and alert semantics | Second: these break the deploy rather than the build, and the operator is rarely the person reading the changelog for features |
| Integrators and API consumers | Endpoint, schema, event-payload, client-library and webhook changes, including additive ones that change validation strictness | Third: additive here still breaks a strict client, which is why it is not filed under features |
| Everyone else | New capability, behaviour improvements, notable fixes users reported | Fourth: real content, but it is the part a reader can skip |
| Internal only | Refactors, test changes, dependency bumps with no behavioural effect, tooling | Last, or a separate file. Present for auditability, absent from the reader's path |

Within a section, order by how much work the entry creates, not by merge order. Merge order is chronology, and chronology is information the reader already has in the commit log.

### 3. Write the entry for the person it affects

Each entry answers three questions in one or two sentences: what changed, what a reader observes because of it, and what they do. A change nobody observes and nobody acts on does not need an entry.

- Write from the outside. "Timeouts now default to 30 seconds" is an observation; "reduced the default in the connection pool config struct" is a diff summary.
- Name the surface exactly — the endpoint, the flag, the configuration key, the class — so the reader can search their own codebase for it.
- Link the change to its issue or pull request, and put the link at the end. A reader scanning ten entries should not read ten identifiers first.
- Attribute external contributions. It is the one piece of ceremony in the document that reliably earns its space.
- Do not describe the implementation. A reader who needs it follows the link; everyone else pays for it.

### 4. Write each breaking change as the migration

A breaking change entry has four parts, and omitting any one of them puts the work back on the reader.

- **What breaks**, in terms of what they will see: an error, a silently different result, a failed start-up, a rejected payload.
- **Who is affected**, stated narrowly enough that most readers can rule themselves out in one line. "Only callers passing the legacy sort parameter" saves a thousand people an investigation.
- **The migration** — the concrete replacement, before and after, including the case where the answer is "there is no replacement, and here is why".
- **The deadline and the interim behaviour**: whether the old path still works in this version, when it stops, and what it does in the meantime — error, warning, or silent fallback.

Where a compatibility shim exists, say what it costs and when it is removed; a shim with no removal date is the next major's breaking change written in advance. Where the migration takes more than a paragraph, it becomes an upgrade guide and the notes link to it, because a migration buried in a changelog entry is a migration nobody completes.

`references/breaking-changes.md` has the catalogue of changes that break callers without looking like breaks, with the wording for each. Read it when deciding whether a change is breaking at all, or when a change is breaking in a way the diff does not show.

### 5. Cut the noise before you write

Filter the range, then write. The test is whether any reader, in any of the audiences above, changes what they do because of the entry.

| Include | Exclude |
| --- | --- |
| A behavioural change a caller can observe, however small the diff | A refactor, rename or test change with identical observable behaviour |
| A dependency bump that fixes a vulnerability, changes behaviour, or moves a minimum runtime version | Routine dependency bumps, which belong in a single collapsed line or in the internal section |
| A fix for a problem someone reported or could plausibly have hit in a released version | A fix for a defect introduced and resolved inside this same release range; it never reached anyone |
| A performance change large enough to alter capacity, cost or a timeout someone set | A micro-optimisation with no externally visible effect |
| A new default, limit, quota or validation rule | An internal constant that happens to be configurable |
| A security fix, with the severity and the affected versions | Details of the vulnerability beyond what a reader needs to assess urgency and upgrade |

Sixty collapsed dependency bumps read as one line. Sixty individual entries read as a wall, and the wall is what teaches readers to skip the document that will one day carry the line that mattered.

### 6. Resolve the version when semantic versioning is ambiguous

Semantic versioning is a promise about compatibility, not a measure of effort. The number follows from what a caller must do, so decide the compatibility question first and the number falls out.

| Situation | Call it | Reason |
| --- | --- | --- |
| A bug fix that some caller has plausibly built on | Major where an untouched caller observes a different result; patch where the old behaviour was documented as a defect and nothing could reasonably depend on it | Semantic Versioning 2.0.0 defines PATCH as a backward-compatible bug fix, which reads as covering every fix. It does not: a fix a caller has built on is not backward compatible, so the spec's own compatibility test makes it MAJOR. Say in the notes which of the two you applied, because a reader comparing against a literal reading of the spec will expect a patch |
| A new optional field in a response | Minor, unless clients validate strictly | Additive is only additive if the consumer tolerates unknown fields; strict validation makes it breaking in practice |
| A new required field in a request, or stricter validation on an existing one | Major | Previously accepted input is now rejected, which is a break however small the change |
| A default value changed | Major when a caller relying on the old default gets a different outcome; minor when it only affects new installations | The question is whether an untouched caller behaves differently after upgrading |
| A minimum runtime, platform or dependency version raised | Major | The upgrade fails for somebody who changed nothing |
| A deprecated feature removed after its announced period | Major, and reference the version that announced it | The announcement does not make the removal compatible; it makes it expected |
| Error message or code changes | Major when the code or shape is documented or obviously parsed; minor otherwise, with a note | Callers parse error strings whether or not they were told to |
| A security fix requiring a breaking change | Ship the break, and backport a non-breaking mitigation to supported lines | Forcing a major upgrade to get a security fix means most users take neither |
| Pre-1.0 | Follow the same reasoning and say the rule you are using | The specification gives pre-1.0 no compatibility guarantee, which readers reliably assume anyway |

Where the call remains genuinely ambiguous after this table, choose the more disruptive number and say why in the notes. An unexpected major costs a reader one planned upgrade; an unexpected break costs them an incident.

### 7. Run the pre-publish checklist

Every item is verified against the artefact and the repository, not from memory. Any unchecked item stops the publish.

- **Version bumped** in every place it appears — the manifest, the lockfile, any vendored or generated copy, the container label. A version string that disagrees with itself makes support unanswerable.
- **The tag points at the built commit**, and the tag has not been moved or recreated. Confirm with `git rev-parse` against the build's recorded revision.
- **The artefact is the tested one.** Promote the build that passed the tests, identified by digest or checksum. A rebuild at publish time is a different artefact with no test result.
- **Every breaking change has its migration**, and every migration has been read by somebody who did not write it.
- **The rollback is stated**: the previous version, whether downgrading is supported, and what makes it irreversible — a schema contraction, a data format change, a one-way external side effect. Where it is irreversible, say so in the notes, prominently.
- **Dependencies and minimum versions** stated where they changed, including the runtime floor.
- **The security fixes carry severity and affected versions**, so an operator can decide urgency without reading the diff.
- **The range is reconciled** against the deploy record, with the previous version named in the document.
- **Links resolve**, and no entry references an unmerged or reverted change.

`references/checklist.md` has the checklist as a runnable list with the verification command for each item, plus the release-day sequence and what to do when an item fails after publication. Read it at step 7, and when a release has to be yanked or amended.

## Output format

```markdown
# [Version] — [date]

[One or two sentences: the headline of this release, and whether upgrading requires work.]
Previous release: [version, and the range this document covers.]

## Action required
[Breaking changes and anything with a deadline. Each one: what breaks, who is affected,
the migration, when the old path stops working.]

## For operators
[Configuration, secrets, capacity, observability and deploy-affecting changes.]

## For integrators
[API, schema, event and client-library changes, additive ones included.]

## Changes
[New capability, behaviour changes, notable fixes. Ordered by work created, each with its
link at the end of the entry.]

## Security
[Each fix with severity and affected versions. Enough to judge urgency, no more.]

## Upgrade
[Steps in order, including any data or configuration step, and the rollback: previous
version, whether downgrade is supported, and what makes it irreversible.]

## Internal
[Refactors, dependency bumps, tooling. Collapsed. Present for the record.]
```

## Anti-patterns

**Deriving the range from a date.** Dates do not line up with what shipped: a hotfix went out from a maintenance branch, a release was tagged and pulled, a cherry-pick moved. The notes then claim changes users already have and omit ones they do not, and the error is invisible until someone debugs against the wrong version. Derive from the last tag that reached production and reconcile with the deploy record.

**Sorting by component.** It matches the repository and nothing about the reader. The person who must migrate a client library scans a list organised around storage, scheduler and API internals, misses their line, and finds out at upgrade time. Sort by audience, with the work that cannot be avoided first.

**A breaking change with no migration.** The reader now knows they are affected and not what to do, so they either delay the upgrade indefinitely or attempt it and fail. The replacement, the before-and-after and the deadline belong inside the entry, not in a linked issue.

**One entry per merged commit.** Sixty dependency bumps and a typo fix bury the four lines that matter, and readers learn the document is not worth opening. That lesson persists into the release where the top entry is a security fix. Cut the range before writing.

**Versioning by diff size.** A large refactor with no observable change is a patch; a one-character default change that alters an untouched caller's behaviour is a major. Deciding from effort ships breaks through automatic upgrades, which is how an unattended dependency update becomes somebody else's incident.

**Publishing a rebuild.** The tests passed on an artefact that no longer exists, and the one users receive has never been tested. Promote by digest, and treat any rebuild between test and publish as a new release requiring a new test run.

**A moved or recreated tag.** Every future range derivation from that point is wrong, every checkout of that version returns something different depending on when it was fetched, and support cannot reproduce anything. A bad release gets a new version number, never a moved tag.

**Writing notes from commit messages alone.** Commit subjects are written for reviewers of a diff, so the notes inherit internal vocabulary, describe implementation, and miss the change made entirely in configuration or a template where no commit message mentions the user-visible effect. Start from the observable change and use the log to find it.

**No rollback statement.** Silence reads as "yes, you can downgrade", which is the assumption someone acts on at the worst moment. Where a migration, a data format or an external side effect makes the release one-way, that sentence is the most valuable one in the document.

**Different notes for different audiences, written separately.** They drift within one release: the customer-facing summary omits the deadline, the internal one omits the migration, and each audience is confidently told something incomplete. Write one document with audience sections and cut from it.

## Reference files

- `references/breaking-changes.md` — read when deciding whether a change is breaking at all, or when it breaks callers in a way the diff does not show: the catalogue of silent breaks across APIs, schemas, events, configuration defaults and client libraries, with the deprecation sequence and the wording for each.
- `references/checklist.md` — read at step 7, and again when a release has to be yanked or amended: the pre-publish checklist with a verification command per item, the release-day sequence, and the procedure for a bad release that is already published.
