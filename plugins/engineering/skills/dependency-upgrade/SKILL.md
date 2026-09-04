---
name: dependency-upgrade
description: "Move a codebase onto a new major version of a dependency, runtime or framework without a six-month branch that never lands: state why you are upgrading before how, read the changelog and grep for every breaking change that applies to code you actually have, escalate deprecation warnings and land those fixes first, choose an incremental or direct jump, bump one dependency per change so a revert is precise, and name the surface your tests do not cover. Use this skill whenever someone is bumping a major version, planning a framework, runtime or language upgrade, reacting to a security advisory with no patch for their version, an end-of-support date, a transitive break or a lockfile conflict — including \"upgrade us to React 19\", \"we are three majors behind\", \"can we move to Python 3.13\", or \"the upgrade branch has been open since March\". Not for a red pipeline, a schema change, the rollout mechanics, or choosing between competing libraries."
allowed-tools: "Read, Grep, Glob, Edit, Write, Bash(npm:*), Bash(pnpm:*), Bash(yarn:*), Bash(pip:*), Bash(uv:*), Bash(go:*), Bash(mvn:*), Bash(cargo:*), Bash(git:*), Bash(gh:*), Bash(rg:*), Bash(jq:*)"
---

# Dependency Upgrade

An upgrade lands well when it arrives as a series of small changes, each independently revertible, each with a stated reason — and the version bump itself is the least interesting one in the series.

The job is hard because the change is misdescribed by its own diff. A major bump is one line in a manifest and a few hundred in a lockfile, so it is reviewed as a version change when it is a behaviour change wearing one. From there teams fail in two directions. One takes the bump, watches a green suite, and meets the behaviour difference three weeks later in production, at which point nobody connects it to the upgrade. The other opens an upgrade branch, discovers it needs a hundred call sites changed, and starts diverging from main faster than it converges — the branch is a fork of your own repository, and it dies quietly around month four. Underneath both sits the reason the work keeps getting deferred: the cost of not upgrading is invisible right up until it is a security advisory with no patch for your major, and then the deadline belongs to someone else.

## Scope

Use for: taking a dependency, framework, runtime or language to a new major; planning the order of a multi-major jump; reacting to an advisory or an end-of-support date; auditing what a lockfile diff actually moved; deciding whether a transitive break is yours to fix or your dependency's; getting a stalled upgrade branch to land.

Do not use for: a pipeline that went red on a dependency, which is `ci-triage` — come here once it is classified as a real break you have to absorb; a schema change, which is `db-migration`; the mechanics of rolling the upgraded build out, which is `release-strategy`; choosing between competing libraries in the first place, which is `decision-record`.

## Hard gates

Breaking one of these does not slow the upgrade down, it removes your ability to know what the upgrade did.

1. The reason and the deadline are written down before the plan. An upgrade with neither loses every prioritisation conversation it is ever in.
2. The changelog and migration guide are read before the lockfile moves. Reading them afterwards means debugging what you could have looked up.
3. One dependency per change. A revert has to be able to name a single thing.
4. Each breaking change is grepped for in your own code. The test suite is corroboration, not the search.
5. Deprecation fixes land on main as their own changes, before the bump, not inside it.
6. Every resolution override carries an owner, a reason and a removal date at the moment it is added.
7. The uncovered surface is named before the change ships. An unnamed risk is one nobody has accepted.

## Workflow

### 1. Establish why, before how

The reason sets the deadline and the acceptable risk, and those two decide the shape of everything below.

| Reason | Deadline comes from | Acceptable risk |
| --- | --- | --- |
| Security advisory with a patched version | The exposure window, and whether the vulnerable path is reachable from your code | High. Take the smallest bump that clears it, ship it fast, do the rest of the upgrade separately |
| Advisory with no patch for your major | The same, but the fix is now a major upgrade — the deadline is externally set and not negotiable | High, and the work is larger than it looks. Escalate early; this is the one that becomes a quarter of work discovered in a week |
| End of support or end of life announced | The published date, minus the time your slowest consumer needs | Moderate. Plan backwards from the date; the last month is always eaten by something else |
| A feature or a fix you need | Whatever the feature is for | Low. This upgrade competes with other work on merit, and should be sized honestly |
| Hygiene — staying within a supported window | Self-imposed, so make it a standing schedule rather than a project | Low, and this is the cheapest form. Small, frequent, boring |

Write the reason in the pull request title. "Bump lodash" gets reviewed as noise; "Bump lodash to clear GHSA-… reachable from the export path" gets reviewed.

Check reachability before treating an advisory as urgent. A vulnerable function in a package you depend on, in a code path you never call, is a real finding with a low priority, and conflating that with an exploitable path is how a team burns its upgrade budget on the wrong package. Most ecosystems will tell you: `npm audit --json` reports the dependency path, and reachability tooling (`osv-scanner`, `govulncheck`) goes further and reports whether the symbol is called.

### 2. Read the changelog, then grep for what applies

Before the lockfile moves, produce a list of breaking changes that apply to code you actually have. Not the upstream list — your subset of it.

```bash
npm view react versions --json | jq -r '.[-15:][]'   # what majors sit between you and the target
git -C ../react log --oneline v18.3.1..v19.0.0 -- CHANGELOG.md
```

Then, for each breaking change in the migration guide, search your own code:

```bash
rg -n --stats 'ReactDOM\.render\(|componentWillReceiveProps|defaultProps' src/
rg -n 'from ["'"'"']pkg/legacy' --glob '!node_modules'
```

The grep is the load-bearing step, and it is the one that gets skipped because the suite is right there and it is green. A removed API fails to compile and any check finds it. The expensive class is the behaviour change with no signature change — a default that flipped, a sort that became unstable, a timezone that is now resolved differently, an error that is now thrown instead of returned, a timeout that went from infinite to thirty seconds. Those pass compilation, pass type checking, pass every test that did not happen to assert on the changed behaviour, and surface in production. For each one the migration guide names, find the call sites yourself and decide per site.

Keep the list. It becomes the review checklist and the output block at the end.

`references/breaking-change-audit.md` has the search patterns per breaking-change class, how to read an upstream changelog for the things it under-reports, codemod usage and its limits, and the compatibility-shim shapes. Read it while building the list.

### 3. Choose the shape: incremental or direct

| Shape | Use when | Cost |
| --- | --- | --- |
| **Incremental** — one major at a time, each landed and released | Each intermediate major has its own migration guide and its own breaking changes; the jump is more than two majors; the package is core to the codebase | More releases, more elapsed time, and intermediate states you have to keep running |
| **Direct** — straight to the target | The intermediate versions changed nothing you use; the package is small or leaf-shaped; upstream publishes a single guide covering the whole jump | One larger change to review, and no fallback position between here and there |

The test is not how many majors you are crossing, it is how many migration guides apply. Three majors that each removed something you use is three migrations, and doing them in one commit means debugging all three simultaneously with no way to attribute a failure to any of them. That is the specific failure mode: not that the work is large, but that it becomes unattributable. Land each intermediate on main, run it in production for at least one full traffic cycle, then start the next.

Direct is legitimate and often correct — check the intermediate changelogs rather than assuming either answer.

### 4. Escalate deprecation warnings on the version you already run

This is the highest-leverage move available, and it is available before the upgrade starts. Every well-run project spends a major cycle warning you about what the next one removes. Turn those warnings into failures on your current version, fix what they name, and land the fixes on main as ordinary changes. The bump that follows is then small enough to review properly.

```bash
node --throw-deprecation --pending-deprecation ./node_modules/.bin/jest
python -W error::DeprecationWarning -m pytest
```

```bash
go vet ./... && staticcheck ./...          # go: deprecations surface as SA1019
mvn -Dmaven.compiler.showDeprecation=true test
```

Do this as a separate pull request per warning class, on main, ahead of the bump. Two properties make it worth the extra changes: each is small enough to be reviewed on its merits by someone who is not thinking about the upgrade, and each is revertible without touching the upgrade. A codebase that has cleared its deprecation warnings has usually done 60-80% of the next major's migration without ever opening a branch.

Then keep it: fail the build on new deprecation warnings from that point on, or they accumulate again at exactly the rate they did before. `references/ecosystem-playbooks.md` has the escalation flags, the lockfile and audit commands, and the override syntax for npm, pnpm, yarn, pip, uv, Poetry, Go, Maven, Gradle and Cargo. Read it when you need the exact flag for your ecosystem.

### 5. Bump one thing, and read the lockfile diff

One dependency per change, and the manifest diff is not the change — the lockfile is.

```bash
npm install react@19 --save-exact
git diff --stat package-lock.json
node -e "…" # or: npm ls --all --json | jq '…' to diff the resolved tree
```

A lockfile update that moves forty transitive packages alongside the one you meant is not revertible in any useful sense: reverting returns all forty, and one of them was the fix somebody else needed. Reviewing it is not possible either, because the reviewer cannot tell intent from incidental. Constrain the update to the package you named, review the transitive movement that remains, and account for it.

Three things to check in the diff:

- **Transitive majors.** A direct dependency's minor bump can pull a transitive major. That transitive package's breaking changes are yours now, and nothing in your manifest mentions them.
- **Overrides.** A `resolutions` or `overrides` entry forcing a transitive version is a legitimate temporary measure and a bad permanent one — it silently deoptimises upstream's own constraint solving and it hides the fact that the real fix is upstream. Every one carries an owner, the upstream issue it waits on, and a removal date, and something has to check the dates or they are decoration.
- **Supply chain.** A new maintainer on a package, a package that grew a `postinstall` script it did not have, or a diff far larger than the release notes justify are all worth ten minutes. Small packages with sudden large diffs and fresh publisher accounts are the shape of a compromise, not of a normal release. Prefer packages that publish provenance, and pin by digest where the ecosystem supports it.

### 6. Be honest about what the tests cover

The suite proves the paths it covers, and an upgrade is exactly the change whose risk sits in the paths it does not. Before shipping, name them explicitly: the batch job that runs monthly, the admin surface, the error paths, the third integration that only one customer uses, the code that only executes under load.

For each uncovered area, choose deliberately and record the choice:

| Option | Fits when | What it buys |
| --- | --- | --- |
| Write the test first | The behaviour is cheap to pin down and worth pinning permanently | The regression is caught now and stays caught |
| Shadow traffic — run both versions, compare outputs | The surface is read-shaped and side-effect-free, and correctness is the question | Real inputs, real cardinality, no user impact. The side-effect suppression is the hard part |
| Canary or ring rollout | The failure is statistical: latency, error rate, resource use | Bounded blast radius and a fast rollback |
| Accept the risk, with a written rollback plan | Coverage is genuinely not worth building, and the area is low-consequence | An honest position, provided the rollback is real and someone has tested it |

The rollout mechanics — ring sizes, bake times crossing a full traffic cycle, guardrails per cohort, the automated rollback signal — are `release-strategy`. Hand off to it rather than reinventing a canary here, and keep the upgrade's own artefact to what makes it an upgrade: the breaking-change list, the uncovered surface, and what a revert consists of.

### 7. Runtime and language upgrades change more than the version string

A dependency upgrade touches your code. A runtime or language upgrade touches everything at once, and the surprises are rarely in the language:

- **The standard library moves.** Functions get removed, defaults change, and a module that was in the standard library becomes an external package you now have to add.
- **Performance characteristics change**, in both directions. A garbage-collector change, a new default allocator, or a JIT tier that behaves differently under your workload can move p99 latency and memory footprint enough to invalidate your capacity assumptions. Measure rather than assume, and re-check headroom.
- **The base image changes with it**, which means a different distribution version, different system libraries, a different OpenSSL, possibly a different libc — and a fresh set of CVEs to triage. Rebuild and rescan; cross-reference `image-hardening` for the base image ladder, digest pinning and the scan gate.
- **The toolchain around it moves too**: linters, formatters, coverage tools and build plugins each have their own supported range, and the upgrade stalls on whichever of them is slowest to support the new version. Check them before committing to a date.
- **TLS, certificates and crypto defaults** are the classic silent break — a new runtime rejecting a protocol version or a weak cipher that a payment gateway still uses fails only against that one integration, only in production.

### 8. If you must open a branch, rebase it daily

The long-lived upgrade branch is the most common way this work dies. Divergence compounds: every day the branch is open, more code lands on main written against the old API, and the branch's job grows while its author's attention shrinks.

Prefer, in order:

1. **Land it on main directly**, behind a compatibility shim if both versions must coexist — an adapter module that presents the old interface over the new dependency, with a deletion ticket. Both call styles work, main never forks, and the shim's removal is a separate small change.
2. **Land the preparation on main and keep the bump alone on a branch.** The deprecation fixes, the codemods, the new-API-compatible rewrites are all valid against the current version. Landing them shrinks the branch to the manifest change plus whatever genuinely cannot be expressed in both versions.
3. **A branch, rebased daily, with a stated end date.** If nobody is going to rebase it daily, do not open it — an unrebased upgrade branch is a research spike, and calling it a spike out loud is more honest and cheaper than discovering it in month four.

A branch that has been open longer than it took to write is telling you the upgrade needs to be broken up, not that it needs more time.

## Signal to action

| Signal | Classification | Action |
| --- | --- | --- |
| Advisory with a patch on your current major | Routine, urgent | Take the patch release now as its own change. Check reachability to set the priority, not to skip it |
| Advisory with no patch for your major | Forced major upgrade | The deadline is external. Size the upgrade this week, not this quarter; consider a temporary mitigation (disable the feature, block the input, virtual patch at the edge) to buy the time honestly |
| End of support announced | Scheduled major upgrade | Put the date in the plan and work backwards. Start at the point where the incremental path still fits in the time |
| Transitive-only break, direct dependency unchanged | Upstream constraint problem | Fix upstream if you can — an issue plus a pull request. Locally, a pinned override with a removal date tied to the upstream issue, not an indefinite one |
| Behaviour change with no signature change | The expensive class | Grep every call site by hand, write a test that pins the new behaviour, and decide per site. This is the one that reaches production |
| Package changed maintainer, or a small package with a large unexplained diff | Supply-chain review | Read the diff before merging. Check the publisher, the provenance attestation and any new install scripts. Delay the bump if the answer takes longer than the bump saves |
| The upgrade needs a change in a library that has not shipped support yet | Blocked, not slow | Say so and record what unblocks it. A blocked upgrade tracked as in-progress is invisible to whoever could escalate it |

## Output format

```markdown
## Dependency
[Name, from version, to version. Direct or transitive.]

## Reason and deadline
[Advisory / support deadline / feature / hygiene — and the date, with where the date comes from.]

## Shape
[Incremental through which intermediates, or direct — and why the intermediates do or do not apply.]

## Breaking changes that apply to us
| Upstream change | Call sites found | Signature change? | Fix |
[One row per change that touches code we have. Behaviour-only changes marked.]

## Preparation landed separately
[Deprecation fixes and codemods already on main, with their change ids.]

## Lockfile movement
[Transitive packages moved, majors among them, any override added with owner and removal date.]

## Uncovered surface
[The paths the suite does not exercise, and the deliberate choice for each: test, shadow, canary, accept.]

## Rollout
[Handed to release-strategy: mechanism, rings, bake. Or: shipped directly, and why that is acceptable.]

## Rollback
[What reverting consists of, and the point after which it stops being a revert — persisted data in a new format, a migrated config, an external system that saw the new version.]
```

## Anti-patterns

**Bumping and trusting the tests.** A green suite proves the covered paths still behave; the upgrade's risk lives in the behaviour changes that carry no signature change, which is exactly the class no compiler and no type checker sees. Cost is a production incident three weeks later, by which time nobody links it to the version bump and the diagnosis starts from zero.

**Batching forty packages.** "Bump all dependencies" produces a diff nobody can review and a revert nobody can aim. When it breaks, the only available action is reverting all forty, which returns every fix the other thirty-nine carried, so the team reverts nothing and debugs under pressure instead.

**Skipping the intermediate major.** Three migrations arrive simultaneously and no failure can be attributed to any one of them. The debugging cost is not additive, it is combinatorial, and the usual outcome is abandoning the jump and doing it incrementally anyway, having spent the incremental budget twice.

**Ignoring deprecation warnings for two years.** The warnings were the free preview of exactly this migration, spread over a release cycle in small pieces. Ignored, they arrive together as one large change under a deadline, and the log line that would have told you which call site is now noise nobody reads.

**A branch nobody rebases.** Divergence grows faster than the work shrinks. The branch becomes a fork of your own repository maintained by one person, and it is abandoned after months of intermittent effort — the most expensive way to not upgrade.

**A permanent resolution override.** Added as a temporary pin to unblock a release, it outlives the person who added it, silently constrains every future resolution, and hides the upstream fix that landed a year ago. Undated overrides are how a lockfile becomes unupgradeable.

**Upgrading with no stated reason and no deadline.** It loses to every other priority, every sprint, in a way nobody argues with — until the reason arrives from outside as an advisory with a fixed date, and the work that was optional for two years is now urgent and larger.

## Reference files

- `references/breaking-change-audit.md` — read while building the list of breaking changes that apply to your code: search patterns per class of change, the behaviour changes changelogs under-report, codemods and where they stop being trustworthy, compatibility-shim shapes, and how to pin new behaviour with a test before you rely on it.
- `references/ecosystem-playbooks.md` — read when you need the exact command for your ecosystem: deprecation-warning escalation, lockfile diffing, advisory and reachability scanning, override and resolution syntax with expiry, and the runtime-upgrade checklist for npm, pnpm, yarn, pip, uv, Poetry, Go, Maven, Gradle and Cargo.
