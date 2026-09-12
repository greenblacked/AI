---
name: dependency-triage
description: "Work a queue of dependency vulnerability alerts — Dependabot, npm audit, pip-audit, govulncheck — into a decision each: reachability before severity, CVSS base versus environmental, EPSS and CISA KEV as the two signals that mean today rather than this quarter, direct versus transitive and the three ways to fix a transitive one, patch bumps batched behind the suite while behaviour changes go alone, suppressions with an expiry date and a named reason, and the malicious or typosquatted package that is an incident, not a queue item. Use this skill whenever someone asks \"twelve dependabot PRs, which matter\", \"is this CVE actually exploitable for us\", \"npm audit says 40 vulnerabilities\", \"can we ignore this one\", or has a backlog nobody reads. Not for a planned major-version move (dependency-upgrade), a container image scan gate (image-hardening), or a leaked credential (secret-rotation)."
allowed-tools: "Bash(gh:*), Bash(npm:*), Bash(pnpm:*), Bash(yarn:*), Bash(pip:*), Bash(pip-audit:*), Bash(uv:*), Bash(poetry:*), Bash(go:*), Bash(govulncheck:*), Bash(osv-scanner:*), Bash(jq:*), Bash(curl:*), Bash(rg:*), Read, Grep, Glob"
---

# Dependency Triage

Triage went well when the queue is empty at the end of the session — not because everything was upgraded, but because every alert left it as a merged fix, a batched patch, a dated exception, or an incident someone is already working.

The job is hard because the queue is designed to be uniform and your exposure is not. A scanner reports a critical in a package your code never calls with exactly the same urgency as a medium in the function that parses the request body, because the only thing it knows is the CVSS base score, which is a property of the vulnerability and says nothing about you. Faced with twelve alerts that all look equally severe and all cost real time, teams do one of two things: upgrade everything to make the number go to zero, which spends the week's risk budget on the safest items in the list and eventually lands a breaking change nobody planned; or stop reading, at which point the alert queue becomes wallpaper and the one alert that mattered arrives in the same undifferentiated stream as the ninety that did not. The whole skill is about restoring the difference between them before deciding anything.

## Scope

Use for: a backlog of Dependabot, Renovate, Snyk, `npm audit`, `pip-audit`, `govulncheck` or `osv-scanner` findings; deciding whether a specific CVE or GHSA matters here; fixing a vulnerable transitive dependency; setting up a weekly cadence; judging whether a dev-only finding needs work; responding to a package that turns out to be malicious.

Do not use for: moving onto a new major version of a framework or runtime, whether or not an advisory prompted it — that is `dependency-upgrade`, and this skill hands over the moment the answer is "we need to be on the next major". Choosing a base image, setting a scanner severity gate, or triaging OS-package CVEs inside a built container is `image-hardening`. Reviewing a diff for vulnerability classes is `security-review`. A credential that has leaked is `secret-rotation`.

## Workflow

### 1. Collect the queue once, keyed by advisory rather than by PR

Twelve Dependabot PRs are usually fewer than twelve decisions: one advisory can raise a PR per manifest in a monorepo, and one transitive package can appear under four parents. Deduplicate before you start reading, or you will make the same judgement four times and inconsistently.

```bash
gh api --paginate "repos/OWNER/REPO/dependabot/alerts?state=open&per_page=100" \
  --jq '.[] | {n: .number, ghsa: .security_advisory.ghsa_id,
               cve: .security_advisory.cve_id,
               sev: .security_advisory.severity,
               pkg: .dependency.package.name,
               eco: .dependency.package.ecosystem,
               scope: .dependency.scope,
               manifest: .dependency.manifest_path,
               fix: .security_vulnerability.first_patched_version.identifier}'
```

`.dependency.scope` is `runtime` or `development` and is the single most useful field in that payload; the API also filters on it directly with `&scope=runtime`. Group the output by `ghsa`, and count distinct advisories. That number, not the PR count, is the size of the week's work.

Locally, one command per ecosystem:

```bash
npm audit --json                       # add --omit=dev to see the runtime subset alone
pip-audit -r requirements.txt -f json  # or: pip-audit (audits the active environment)
govulncheck ./...                      # Go: identification and reachability in one pass
osv-scanner scan source -r .           # cross-ecosystem, reads the lockfiles it finds
```

`npm audit` reports against the whole installed tree, so a fresh `npm ci` matters: auditing a stale `node_modules` reports vulnerabilities in packages the lockfile no longer resolves to.

### 2. Split the queue before scoring it

Four buckets, in this order, because each one changes what the later questions even mean.

| Split | The question | Why it changes the answer |
| --- | --- | --- |
| Runtime or build-only | Does this code execute in production? | A build-only finding is not automatically safe — see below — but it is a different threat model |
| Direct or transitive | Is the vulnerable package in your manifest? | Direct is a one-line fix; transitive has three routes and each costs something |
| Reachable or not | Does any path from your code reach the vulnerable function? | This is the largest single reduction in the queue, and it is the one nobody does |
| Fix available or not | Is there a patched version? | Nothing else matters if there is nowhere to go; that alert becomes a compensating-control decision |

**The dev-dependency question is not "does it ship".** It is "does it execute anywhere holding credentials". A test runner or build plugin executes on your CI runner, usually with a registry token, a cache key, sometimes a deploy key, and on a self-hosted runner with network reach into your estate. An arbitrary-code-execution bug in a build tool that runs on every pull request from a fork is worse than an unreachable deserialisation CVE in a production library. Ask where it runs and what it can see, and only then downgrade it. The genuinely low-risk dev finding is one that runs on a developer laptop against code that is already trusted — a linter, a type checker — and even those have `postinstall` scripts.

### 3. Two signals move something out of the weekly queue and into this morning

Everything else in this skill is about ordering the week. These two are about whether you should still be doing weekly triage at all for a given alert.

**CISA KEV.** The Known Exploited Vulnerabilities catalogue lists vulnerabilities with reliable evidence of active exploitation in the wild. It is small — low thousands of entries against hundreds of thousands of published CVEs — which is exactly what makes it useful: it has very high precision and it is the one signal worth an interrupt. Entries carry a `dueDate`, which binds US federal civilian agencies under BOD 22-01 and which everyone else can reasonably borrow as a default deadline.

```bash
curl -s https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json \
  | jq -r '.vulnerabilities[] | [.cveID, .dueDate, .knownRansomwareCampaignUse] | @tsv' > kev.tsv
```

Join your queue against that file. A KEV hit on a package you actually deploy is not a triage item, it is an action for today, and the reachability question changes from "should we fix this" to "how fast can we fix it and what do we do until then".

**EPSS.** The Exploit Prediction Scoring System publishes, daily, a probability that a given CVE will be exploited in the wild in the next thirty days, plus that score's percentile against every other CVE. It is a forecast of attacker activity, not of severity and not of impact on you.

```bash
curl -s 'https://api.first.org/data/v1/epss?cve=CVE-2021-44228' \
  | jq -r '.data[] | [.cve, .epss, .percentile] | @tsv'
```

Use the percentile for ranking within your queue and the raw probability for a threshold. The distribution is heavily skewed — the large majority of CVEs sit below a one percent probability — so a score in the high nineties of percentile is a genuine outlier and worth jumping the queue for. Do not invert it: a low EPSS is weak evidence of safety, because nothing has been observed *yet*, and a vulnerability in software only you run will never have observation data at all.

Read `references/scoring-signals.md` before arguing about a score with anyone — it covers CVSS base versus threat versus environmental metrics, what NVD does and does not publish, why GHSA, OSV and CVE identifiers disagree about severity, and the ordering table that combines all of this into a queue.

### 4. Reachability before severity

This is the step that makes the queue finite. A critical CVSS score in a transitive dependency whose vulnerable function your code never calls is lower risk than a medium in a path that handles untrusted input, and treating them alike is precisely why alert queues stop being read.

What "reachable" means here, in descending order of what it proves:

1. **A symbol-level call path exists** from your code to the vulnerable function. Strongest available evidence, and only some ecosystems can produce it.
2. **The vulnerable package is loaded at runtime** but the specific function is not obviously called. Weaker; treat as reachable unless you check the call path by hand.
3. **The package is present in the lockfile but not imported anywhere.** Often a dependency of an optional feature or a peer that was never used. Still worth removing, rarely worth an interrupt.
4. **The vulnerable code path requires a configuration you do not enable** — a parser mode, a plugin, a debug endpoint. Real mitigation, but it is a statement about your configuration and it expires the moment someone changes the config, so it is an exception with a date, not a dismissal.

Per ecosystem, briefly; `references/reachability.md` has the full procedure, the flags, and what each tool's analysis actually covers.

**Go** has the strongest answer in any mainstream ecosystem. `govulncheck ./...` builds a call graph and reports symbol-level results, splitting output into vulnerabilities your code calls and vulnerabilities present but uncalled. That split is the triage, handed to you:

```bash
govulncheck ./...            # source mode, symbol-level, module deps and stdlib
govulncheck -test ./...      # include test files, for the build-only question
govulncheck -mode=binary ./bin/app   # what actually shipped, when you have no source tree
```

**npm** has no free symbol-level equivalent. What you do have is the dependency path and the import graph:

```bash
npm explain lodash           # every path in the tree that pulls this package in
npm ls lodash                # the resolved versions and where they sit
rg --hidden -n "require\(['\"]lodash|from ['\"]lodash" src/
```

That establishes whether the package is used at all and by whom, which already clears a large share of a typical `npm audit` output. Going further — does your code reach the specific vulnerable export — is manual: read the advisory for the affected function, then trace from your import. Commercial tooling (Semgrep Supply Chain, Snyk, Endor Labs) automates this with advisory-specific reachability rules; be clear when recommending one that you are recommending a paid product.

**Python** is the weakest, and say so rather than implying otherwise. Dynamic imports, `getattr` dispatch and plugin registries defeat static call graphs, so the practical ceiling is import-level plus a manual read of the advisory:

```bash
pipdeptree --reverse --packages urllib3   # who depends on it
rg -n "^\s*(import|from)\s+urllib3" .     # do we import it directly at all
```

**Reachability analysis has false negatives, and this is not a footnote.** Reflection, dynamic dispatch, `eval` and plugin loading all hide edges from a call graph. `govulncheck` in binary mode loses precision relative to source mode. Any tool only knows the vulnerabilities in the database it reads, and the Go vulnerability database, GHSA and OSV are each curated on their own schedule, so a freshly published CVE can be invisible to a tool that is working correctly. Treat "not reachable" as "reachable path not found by this tool today" — it justifies deferring to the batch, never a permanent dismissal, and it is the reason every suppression in step 8 gets a date.

### 5. Decide the action, one per advisory

| Reachable | Signal | Scope | Action |
| --- | --- | --- | --- |
| yes | in KEV | runtime | Today. Patch or take the service off the vulnerable path; if no patch exists, apply a compensating control and track it |
| yes | high EPSS or critical with a fix | runtime | This week, as its own change with its own test run |
| yes | anything else with a fix | runtime | Next batch, unless the bump carries a behaviour change |
| no | in KEV | runtime | This week. The precision of KEV outweighs your confidence in the call graph |
| no | anything else | runtime | Batch it with the patch sweep. No interrupt, no exception needed |
| either | any | build-only, runs in CI with credentials | Treat as runtime until you have checked what the runner holds |
| either | any | build-only, laptop only | Batch |
| any | no fix available | any | Not a version bump. Decide on a compensating control, a replacement, or an exception with a date and a named owner |

The last row is the one people get stuck on. An alert with no patched version cannot be closed by upgrading, and leaving it open forever is what teaches everyone that the queue is noise. Write down what you are doing instead — input validation in front of the vulnerable path, a WAF rule, disabling the feature, or a plan to replace the library — and put a review date on it.

### 6. A vulnerable transitive dependency has three fixes, and they cost different things

First find out whether you have a problem at all: if the parent already permits a patched version, the fix is to refresh the lockfile, not to override anything.

```bash
npm explain minimist          # npm: every parent that pulls it in, and the range each allows
go mod why -m golang.org/x/net  # Go: the import chain that requires this module
pipdeptree --reverse --packages jinja2   # Python
```

**Route 1 — update the lockfile and let resolution pick the patched version.** `npm update <pkg>`, `poetry update <pkg>`, `go get <module>@<version> && go mod tidy`. Costs nothing and is correct whenever the parent's declared range already covers the fix. Try this first; a surprising share of "we need an override" turns out to be a stale lockfile.

**Route 2 — force the resolution.** Correct when the parent's range excludes the fix and you have read enough of the diff to believe the API did not change.

| Ecosystem | Mechanism |
| --- | --- |
| npm 8.3+ | `"overrides"` in `package.json` |
| pnpm | `"pnpm": {"overrides": {...}}` in `package.json` |
| Yarn (Classic and Berry) | `"resolutions"` in `package.json` |
| pip | a constraints file, applied with `pip install -r requirements.txt -c constraints.txt` |
| Poetry | add the transitive package as an explicit direct dependency with the patched range |
| uv | `[tool.uv] constraint-dependencies` to narrow, `override-dependencies` to ignore the declared requirement outright |
| Go | none needed in the usual case: `go get` the newer module and minimal version selection takes the maximum. `replace` exists for the case where you need a fork |

The cost is that you are now running a combination the parent's maintainers never tested, and the override is invisible in the parent's own CI. It also goes stale silently: when the parent eventually widens its range, the pin keeps you on an older version than resolution would have chosen. Put a comment on every override saying which advisory it closes, and delete it when the parent catches up.

**Route 3 — replace or remove the parent.** The right answer when the parent is unmaintained, when the override breaks it, or when the same parent has produced this conversation three times. It is a real project rather than a triage action, so it leaves this skill: open an issue, size it, and do not attempt it inside the weekly session.

Waiting for the parent is a legitimate fourth option when the advisory is unreachable and low-signal. Waiting is a decision only if it is written down with a date to check again; otherwise it is the queue growing.

### 7. Batch the safe, isolate the risky

Two shapes of change, and mixing them is what makes a triage sweep unrevertible.

**The batch.** Every patch-level and lockfile-only bump with no behaviour change goes into one branch, one lockfile diff, one test run. The full suite is the gate. If it goes red, bisect within the batch — that is cheap because the changes are independent. Dependabot groups these natively:

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    groups:
      patch-sweep:
        applies-to: version-updates
        update-types: ["patch"]
```

Renovate's `minimumReleaseAge` is worth setting alongside this — a cooldown of a few days on new releases costs you almost nothing in exposure and takes you out of the blast radius of the compromised-release window described in step 9.

**The isolated change.** Anything with a minor or major bump, a changelog entry mentioning behaviour, a dependency that appears in your public API's types, or a package whose patch you had to force. One change, one PR, its own review. If the isolated change turns out to need a major version, stop: that is `dependency-upgrade`, with its own sequencing and its own breaking-change grep.

Review the lockfile diff itself, not only the version numbers. New transitive packages arriving in a "patch" bump, a package gaining a `postinstall` script, or a registry URL changing are all visible there and nowhere else.

### 8. Suppress with an expiry date and a named reason, or do not suppress

A suppression is a claim with a shelf life: "this is not reachable in our build today", "the fix requires a major we are scheduling for Q3", "this parses only files we generate". Every one of those can stop being true without anyone touching the suppression, which is why it needs a date.

`osv-scanner` has the mechanism that gets this right, and it is worth adopting for the config file even if another scanner produces your alerts:

```toml
# osv-scanner.toml
[[IgnoredVulns]]
id = "GHSA-xxxx-xxxx-xxxx"
ignoreUntil = 2026-03-01
reason = "Reached only through the CSV import path, which is behind an admin flag we do not enable. Revisit when the flag ships."
```

Other ecosystems are weaker and need the date carried by hand. `pip-audit --ignore-vuln <ID>` takes no expiry, so keep the list in a file with a dated comment per entry and a calendar item to re-read it. `govulncheck` has no suppression mechanism at all, which is a deliberate design choice. Dismissing a Dependabot alert records a reason but never expires:

```bash
gh api --method PATCH "repos/OWNER/REPO/dependabot/alerts/42" \
  -f state=dismissed \
  -f dismissed_reason=not_used \
  -f dismissed_comment="Not imported anywhere; review 2026-03-01"
```

Valid reasons are `fix_started`, `inaccurate`, `no_bandwidth`, `not_used` and `tolerable_risk`. `no_bandwidth` and `tolerable_risk` are the two that are really "later", and the dismissal will outlive the person who wrote it, so pair each with a dated issue.

**An unexpiring suppression is the same failure as a disabled test.** Both were added for a reason that was true that day; both stop being read; both leave behind a signal that reports green while covering nothing; and in both cases the loss is silent, so no future event will surface it. The difference is that a skipped test is at least visible in the suite output, while a scanner suppression is visible only in a config file nobody opens. Give it a date and the failure mode becomes a finding reappearing on a Tuesday, which is exactly what you want.

### 9. The vulnerability that is not in your dependency at all

A malicious package, a typosquat, or a compromised maintainer account is a different kind of event and the response is different and faster. The distinction that matters: an ordinary CVE is a latent flaw that an attacker must reach, so you have time proportional to reachability. A malicious package is code that already ran — at install time, on every developer machine and every CI runner that resolved it — so the exposure is in the past tense and triage ordering does not apply.

What it looks like:

- A package published hours or days ago, in a version you did not ask for, arriving through a range like `^1.2.0`.
- `preinstall` or `postinstall` scripts in a package that had none, or a Python `setup.py` doing work at install time in a project that publishes wheels.
- Published artifacts that do not match the source repository: minified or obfuscated code in the tarball with no corresponding commit, or a version on the registry with no matching git tag.
- A name one edit away from something popular, or an internal package name suddenly resolvable from the public registry, which is dependency confusion.
- A new maintainer added recently, or a long-dormant project becoming very active just before a release — the pattern behind the `xz`/`liblzma` backdoor, where a maintainer was cultivated over roughly two years before the payload landed.
- An advisory with a `MAL-` identifier rather than a `GHSA-`/`CVE-`; OSV carries these for known-malicious packages.

The response, in order:

1. **Stop the spread.** Pin away from the bad version and block it — an `overrides` entry or a registry deny rule — before anything else, because CI is still resolving it while you investigate.
2. **Treat it as credential exposure, not as a version bump.** Install-time code on a CI runner sees whatever that runner holds: registry publish tokens, cloud credentials, cache contents, the checkout's `.git` config. Upgrading to a clean version does not undo execution. Hand the credential work to `secret-rotation` and start it in parallel rather than after.
3. **Establish the blast radius from the lockfile history**, not from memory. `git log -p -- package-lock.json` tells you when the bad version entered and which builds ran after it.
4. **Remove rather than upgrade** where the package is dispensable. A registry account that has been compromised once is not a stronger dependency after the fix than it was before.
5. **Report it** to the registry's security contact and to the OSV malicious-packages process, so the next team's scanner catches it.

Prevention that costs little: `ignore-scripts=true` in `.npmrc` with an explicit allowlist for the few packages that genuinely need a build step (pnpm 10 made non-execution the default, with `onlyBuiltDependencies` as the allowlist), a release cooldown via Renovate's `minimumReleaseAge`, `npm audit signatures` to check registry signatures on the installed tree, and never letting an internal package name be resolvable from a public registry.

### 10. A weekly cadence that ends

The point of a cadence is that it terminates. An hour, once a week, at a fixed time, ending with an empty queue — where empty means every alert has been categorised, not that every alert has been fixed.

1. Pull the queue (step 1) and deduplicate by advisory. Write down the count.
2. Join against KEV and EPSS (step 3). Anything in KEV leaves the session immediately and becomes today's work with an owner.
3. Split runtime from build-only and direct from transitive (step 2).
4. Run the reachability pass (step 4) on what is left. Most of the queue resolves here.
5. Open one batch PR for the patch sweep; open one PR each for the isolated changes; open one dated exception for each alert with no fix or no fix you can take.
6. Confirm nothing is left unlabelled. Every alert is now merged, in a PR, or suppressed with a date.
7. Record three numbers: alerts in, alerts closed, open exceptions. A rising exception count is the early warning that the cadence has become a queue again — it is the number to watch, not the raw alert count.

Whoever runs it rotates, and it is announced in the same channel each week. A triage session that only one person knows how to run stops happening the week they are on leave, and the backlog it was holding back takes about a month to become unreadable again.

## Anti-patterns

**`npm audit fix --force` as a reflex.** The `--force` flag installs semver-major upgrades to clear findings, so it will happily move you across breaking changes in packages you have not read the changelog for, in a single commit that also contains twenty harmless patch bumps. When something breaks, the revert takes the fixes with it. Run `npm audit fix` without `--force` for the in-range fixes, and treat every remaining finding as its own decision.

**Upgrading everything to make the count go to zero.** The count is not the risk. A sweep that bumps ninety unreachable packages spends the week's change budget and the team's review attention on the safest items in the queue, while the reachable medium that needed a careful look sits in the same green "resolved" list as the rest.

**Treating a dev-dependency finding as automatically safe.** The question is whether it executes anywhere holding credentials, and a build tool on a CI runner with a publish token usually does. "It does not ship to production" answers a different question than the one that matters.

**Severity as the sort key.** CVSS base scores describe the vulnerability under assumed-worst conditions and are the same number for every organisation on earth. Sorting by them produces a queue ordered by someone else's worst case, which is how a critical in an unused optional dependency outranks a medium on your request path.

**A permanent ignore, an allowlist with no dates, or a `.trivyignore`-style file nobody has opened in a year.** It suppresses the finding you assessed and, silently, every future one that matches. The same failure as a disabled test, with worse visibility.

**Letting the queue become something nobody reads.** This is the terminal state and it arrives gradually: alerts accumulate faster than they are worked, the notification becomes noise, and the mechanism that was supposed to surface the exploited-in-the-wild vulnerability delivers it in a batch of ninety. The fix is not more alerts or louder ones, it is a cadence that ends and an exception count that is allowed to be visible.

**Deduplicating by pull request instead of by advisory.** The same decision gets made four times in a monorepo, differently each time, and the inconsistency is invisible afterwards.

**Dismissing an alert because the fix is a major version.** That is a real constraint, but it is a scheduling decision, not an assessment. Record it as an exception with a date and hand the upgrade itself to `dependency-upgrade`.

## Reference files

- `references/reachability.md` — read when deciding whether a specific finding can actually be reached: what `govulncheck` proves and what it misses, the npm and Python procedures in full, Java and Rust, binary versus source analysis, and the manual call-path trace for when no tool covers your case.
- `references/scoring-signals.md` — read before ranking a queue or arguing about a score: CVSS base, threat and environmental metrics and who publishes which, EPSS interpretation and thresholds, CISA KEV and its due dates, why GHSA, OSV and NVD disagree, and the combined ordering table with worked examples.
