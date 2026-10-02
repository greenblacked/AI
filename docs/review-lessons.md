# Review lessons

A curated ledger of defect classes caught by any review of a change here — the review
stage, an automated PR reviewer, or a live run — not a general list of good practice, and
not everything a gate has ever flagged. Each entry is a class specific enough that naming
it saves the round trip of rediscovering it: `implementer` reads this before writing, so
it does not reintroduce a class already caught once; `reviewer` reads it after
`AGENTS.md` and checks the change against it before anything else.

This file is memory, not a rulebook. A rule that fully replaces the need to remember —
because a validator check or a CI gate now makes the mistake impossible rather than
merely likely — gets its entry pruned, and the pruning commit names the rule that made it
unnecessary. Until that happens, the entry stays, because a gate that nobody reads is only
as good as the gate that catches what it does not yet check.

## Adding an entry

When a review here finds a defect class not already below, the commit that fixes it adds
the entry alongside the fix — not as a separate follow-up, and not paraphrased from
memory afterwards. Four parts, in this order:

- **The class** — what kind of mistake this is, named generally enough to recognise in a
  different file.
- **How it shows up** — the concrete shape it took, specific enough to search for.
- **The check that catches it** — the test, validator rule or CI step that now exercises
  this, so the entry doubles as a pointer to where the guarantee actually lives.
- **Where it was first caught** — the pull request number, plus which one caught it: the
  review stage, an automated PR reviewer, or a live run.

Add a case to [`scripts/run_review_benchmark.py`](../scripts/run_review_benchmark.py)'s
benchmark alongside the entry, at
`.claude/agents/benchmarks/reviewer/<case>/`: the smallest real patch that reproduces the
defect against today's tree, and a `case.json` naming this entry's heading as its
`lesson`. A lesson with no case is a class `reviewer` is asked to remember but nothing
ever checks whether it still does.

## The entries

### A CLI upgrade changes an implicit permission mode

**Class.** A pinned CLI upgrade changes a procedure's execution policy when the caller
leaves its permission mode implicit.

**How it shows up.** Claude Code 2.1.285 defaults some non-interactive sessions to auto
mode. The trigger classifier passed only a prompt, so adopting the pin could also
permit new tool approvals. Its complete classification input is already in that prompt.

**The check that catches it.** `tests/test_harness.py` checks the built-in command and
actual fake subprocess arguments with and without a model, keeps custom commands
unchanged, and rejects comparison with an older implicit-mode baseline. The classifier
sets `dontAsk` explicitly; this is an approval policy, not tool isolation. The reviewer
benchmark removes the explicit mode.

**First caught:** the review stage while fixing scheduled run `36423678234`.

### A prepared release is documented as published

**Class.** A changelog's proposed version and links are presented as an existing release
before its tag has been published.

**How it shows up.** The initial catalogue claimed a first tagged release and linked to
`v1.0.0`, although the repository had no tags or releases. Both release references
returned 404 in the weekly external-link check.

**The check that catches it.** The scheduled link check verifies the published targets.
The initial catalogue now links to its immutable commit; `tests/test_release.py` checks
that preparing the first real release updates that commit-based comparison and preserves
the snapshot, while rejecting floating or malformed baselines. The reviewer benchmark
restores the unpublished release claim and links.

**First caught:** #59's initial release documentation, the live scheduled run
`36423678234`.

### An isolated reviewer lacks the dependencies its contract requires

**Class.** A workflow initializes an interpreter but relies on undeclared runner packages
for commands that an isolated worker must execute without installation permission.

**How it shows up.** The reviewer benchmark required `make test` but installed neither
pytest nor coverage before invoking its restricted reviewer workers.

**The check that catches it.** `tests/test_evals_workflow.py` checks installation ordering,
shared CI pins and the existing selection and credential gates without scoring a model.
The reviewer benchmark removes the dependency installation.

**First caught:** #95, the review stage.

### A version comparison treats a tool banner as a version

**Class.** A strict version gate compares an entire multi-line version report with a
single version pin instead of isolating the version field.

**How it shows up.** A correctly pinned actionlint installation failed `lint-strict`
because its version command also reports installation and compiler information.

**The check that catches it.** `tests/test_makefile.py` runs the actual actionlint
recipe against realistic multi-line output, a mismatched version and a missing tool.
The reviewer benchmark restores the whole-banner comparison.

**First caught:** #95, the review stage.

### A delimiter scanner closes a call at an inner expression

**Class.** A scanner counts only explicit function openings but consumes every closing
delimiter, so ordinary nested expressions end the enclosing call too early.

**How it shows up.** A shell regular-expression group inside a Make call hid a later
unescaped hash from the GNU Make 3.81 portability check.

**The check that catches it.** `tests/test_makefile.py` checks grouped shell regexes,
escaped hashes, nested calls and line reporting. The reviewer benchmark restores the
premature closing behavior.

**First caught:** #95, the automated PR reviewer.

### Normalization creates whitespace after its whitespace pass

**Class.** A normalizer removes punctuation after collapsing whitespace, leaving new
whitespace differences in the identity used by duplicate and collision checks.

**How it shows up.** `Ship — it` and `Ship it` escaped both same-skill duplicate checks
and cross-skill positive-query conflicts because removing the dash left two spaces.

**The check that catches it.** `tests/test_evals.py` exercises both duplicate and
cross-skill conflict paths. The reviewer benchmark reverses the normalization order.

**First caught:** #95, the automated PR reviewer.

### A report publisher silently omits a newly added metric

**Class.** A measurement adds an important result field but its downstream report
publishers keep an older column set, hiding the distinction from readers.

**How it shows up.** Trigger evaluation recorded inconclusive multiclass ties in JSON
and CLI output, but both workflow summaries showed only the pass rates and narrow count.
A split vote and a tied vote were indistinguishable in the published report.

**The check that catches it.** `tests/test_evals_workflow.py` executes both workflow
publisher blocks with tied, zero and legacy reports. Each summary includes Inconclusive,
preserves measured zero and shows a missing legacy value as unknown. The reviewer
benchmark removes the metric from both summaries.

**First caught:** #94, the automated PR reviewer.

### An effect from another operation satisfies the goal

**Class.** A shared effect counter substitutes an unrelated mutation for the operation
whose recovery the evaluator is supposed to measure.

**How it shows up.** A submission scenario accepted a patch, incremented its effect
counter and answered a lookup as present. It passed without any submission.

**The check that catches it.** `tests/test_recovery_mock.py` checks incompatible mutation
tools for each goal. The runner rejects those request sequences before execution. The
pure grader rejects the same shape in a capture with `mutation event does not match
capture goal`. The reviewer benchmark permits patch application in a submission scenario.

**First caught:** #91, the automated PR reviewer.

### A bounded patch is applied more than once

**Class.** A mock represents one operation but treats every repeated request as a new
effect, while its success check only asks whether any application occurred.

**How it shows up.** Reading the head and applying the same patch twice passed with two
effects. The mock had no retained applied state to distinguish a duplicate request.

**The check that catches it.** `tests/test_recovery_mock.py` checks duplicate and
preexisting applications. The runner refuses an additional application, retains the
truthful first effect and reports the duplicate request as a constraint failure. The pure
grader rejects a capture that records a second application, or one applied over an
initial effect, with `duplicate patch application`. The reviewer benchmark weakens the
applied-state guard.

**First caught:** #91, the automated PR reviewer.

### A loop body consumes its input inventory

**Class.** A subprocess inherits the stream that controls its caller's iteration.

**How it shows up.** SSH inside a loop reading hosts.txt could forward the remaining
host list as remote stdin, skipping later hosts while reporting successful verification.

**The check that catches it.** Review isolates SSH stdin with `-n` and verifies that a
stdin-consuming command cannot shorten the host inventory. The reviewer benchmark removes
that isolation.

**First caught:** #87, the review stage.

### A privileged command leaves its redirection unprivileged

**Class.** The caller opens an output file before the privileged command starts.

**How it shows up.** Host exports used sudo commands with caller-owned redirection into /root, failing for ordinary operators.

**The check that catches it.** Review verifies redirection occurs inside the privileged shell with a restrictive umask and that producer failure remains observable. The reviewer benchmark restores the faulty redirection.

**First caught:** #87, the automated PR reviewer.

### A stateful firewall permits replies in the wrong direction

**Class.** A connection-state rule protects the wrong packet path.

**How it shows up.** An inbound default-deny policy allowed established outbound traffic, leaving incoming replies blocked.

**The check that catches it.** Review follows host-initiated traffic through the input chain and checks established/related acceptance before deny. The reviewer benchmark reverses the direction.

**First caught:** #87, the automated PR reviewer.

### Rollback omits included configuration

**Class.** A saved parent configuration is mistaken for the complete effective input.

**How it shows up.** SSH and sudoers backups omitted included files; restoring the parent left edited or new drop-ins active.

**The check that catches it.** Review inventories affected includes, saved originals and newly created paths, then checks full restoration before validation. The reviewer benchmark removes that inventory.

**First caught:** #87, the review stage.

### Removing persistent configuration leaves runtime state active

**Class.** Deleting a configuration file is presented as rollback of an already applied setting.

**How it shows up.** The sysctl reference promised a file-delete revert, leaving changed kernel values active.

**The check that catches it.** Review requires saved values for every changed key and explicit runtime restoration alongside persistent configuration. The reviewer benchmark restores the file-delete claim.

**First caught:** #87, the review stage.

### Global configuration verification misses conditional policy

**Class.** An unconditional configuration dump is treated as proof for every connection class.

**How it shows up.** Plain sshd -T missed Match-specific authentication policy.

**The check that catches it.** Review checks representative access contexts using sshd -T -C and fresh connections, with command failures preserved. The reviewer benchmark removes context-specific verification.

**First caught:** #87, the review stage.

### A service restart is mistaken for boot verification

**Class.** A generic daemon-control command is assumed portable and sufficient to prove reboot persistence.

**How it shows up.** The audit reference used systemctl restart auditd on a scope including RHEL and did not distinguish daemon restart from a canary reboot.

**The check that catches it.** Review uses the distro-supported lifecycle and verifies rules after a real approved canary reboot. The reviewer benchmark substitutes the unsupported restart.

**First caught:** #87, the review stage.

### Peer liveness is mistaken for user inactivity

**Class.** A keepalive control is claimed to enforce an idle-user policy.

**How it shows up.** The SSH table called ClientAlive settings an idle timeout even though responsive idle clients can remain connected.

**The check that catches it.** Review checks the documented signal and names user inactivity separately. The reviewer benchmark restores the incorrect timeout claim.

**First caught:** #87, the review stage.

### An evaluation fixture changes metric weighting

**Class.** Appending cases to only one side of a classification fixture changes the
weight of recall versus specificity in its aggregate score.

**How it shows up.** Three new positive orchestration queries changed a fixture from
ten positives and twelve negatives to thirteen positives and twelve negatives. Raw
baseline deltas could move because of the changed case population.

**The check that catches it.** Review counts each label and checks near-neighbor coverage.
The corrected fixture has ten queries per side. Its dataset revision requires rerunning
baseline and candidate on that same set; older raw scores are not comparable. The
reviewer benchmark appends a positive-only case to reproduce the population change.
`tests/test_harness.py` also checks that the trigger runner suppresses baseline deltas
when query text, labels, expected winners, ordering or declared run settings differ;
legacy scores without comparison metadata must be rerun rather than annotated by guess.

**First caught:** #89, the automated PR reviewer.

**Recurrence:** #90 appended positive-only Kubernetes and Terraform identity queries.
Keep those cases by replacing redundant positives; trim Kubernetes' pre-existing
extra distant negative. Both revised sets contain ten cases per side. Rerun baseline
and candidate on each revised set before comparing scores; prior raw scores are not
comparable to the changed population.

### A completed fence loses its terminal state

**Class.** An idempotent control reports its result from the current in-flight pointer
instead of the retained state of the operation it controls.

**How it shows up.** Settling an already fenced mock submission a second time reported
`fenced: false`, although its late callback remained cancelled. A safe retry after a
fresh absent lookup failed the grader because the mock contradicted its own state.

**The check that catches it.** `tests/test_recovery_mock.py` checks repeated settlement
and repeats an older fence while a newer attempt is pending. Retained fence state stays
true; only the matching attempt can clear the pending pointer. The reviewer benchmark
removes the retained-state lookup.

**First caught:** #91, the review stage.

### A read-only diagnostic initializes a provider that writes

**Class.** A procedure assumes that reading data or creating a plan cannot write to the
remote system, overlooking provider initialization side effects.

**How it shows up.** A backend-free identity diagnostic copied AzureRM provider settings
without disabling automatic resource-provider registration. Planning could register
providers before the cloud target had been verified.

**The check that catches it.** The provider-identity reference requires the pinned
provider's registration opt-out and stops when initialization cannot be made read-only.
The reviewer benchmark removes that safety step; review checks provider lifecycle
behavior against its primary documentation rather than inferring it from `plan`.

**First caught:** #90, the review stage.

### A stale fence authorizes a newer request

**Class.** A delayed notification about an earlier attempt changes the safety state of
the currently pending request because settlement is stored as an unscoped boolean.

**How it shows up.** A rejected submission followed by a pending submission, the older
submission's fence, an absent lookup and a committed retry passed the recovery grader.
The pending submission could still commit after the retry and create a duplicate effect.

**The check that catches it.** `tests/test_recovery_trace.py` reproduces the stale fence
sequence. Submission, settlement and late-commit events carry adapter-owned attempt
identifiers; only settlement of the current pending attempt authorizes its retry.
The reviewer benchmark seeds a removed identity comparison.

**First caught:** #90, the automated PR reviewer.

### A recovery grade reuses an earlier generation's success

**Class.** A recovery grader keeps worker identifiers across attempts and mistakes an
earlier accepted result or completion for evidence about the current generation.

**How it shows up.** An initial accepted-worker list made a new assignment pass without
a new result. A delayed old completion could also clear the newer worker's active state.

**The check that catches it.** `tests/test_recovery_trace.py` covers delayed completion
and latest-assignment acceptance. The grader binds both to generation identities and
requires a newly captured result for every latest assignment. The reviewer benchmark
seeds the accumulated-acceptance shortcut so a future review has to recognise it.

**First caught:** #90, the review stage.

### A tag's message drops its own subheadings

**Class.** `git tag -a -F -` defaults to `--cleanup=strip`, which drops every line
starting with `#` from the message — including a Markdown subheading, not only a shell
comment.

**How it shows up.** A release tag built from a `CHANGELOG.md` section loses its
`### Added`-style subheadings silently; the tag message and the GitHub Release body built
from it read as one flat list with no error anywhere.

**The check that catches it.** `scripts/release.py` passes `--cleanup=verbatim`
explicitly, and `tests/test_release.py` asserts that a `#`-led line survives into the tag
message.

**First caught:** #59.

### A shell audit parses YAML with grep, sed or awk

**Class.** A workflow step that inspects YAML structure — a `permissions:` block, a pin —
using line-oriented text tools rather than a real parser is reading text, not structure,
and several equivalent spellings of the same YAML value will not read as equivalent to it.

**How it shows up.** A trailing comment on the value line, a quoted `'write'` against an
unquoted `write`, a flow-map grant (`{contents: write}`), and a comment starting in column
zero each changed whether an early version of the permissions audit fired.

**The check that catches it.** Probe a new shell-based audit against a trailing comment, a
quoted value, a flow map and a column-zero comment before trusting it. `.github/workflows/
security.yml`'s permissions-audit step handles all four, with
`tests/test_permissions_audit.py` exercising each shape.

**First caught:** #58.

### A new strictness rule rejects a form a real parser accepts

**Class.** Tightening the frontmatter reader to reject more ambiguous shapes can reject a
form that a real YAML parser reads without complaint, if the new rule was not checked
against one before landing.

**How it shows up.** A `paths:` block sequence that opens with an explanatory comment
before its first entry — `paths:` then a `# comment` line then `- "src/**"` — is valid
YAML; an early version of the ambiguous-value check treated the comment as ending the
list.

**The check that catches it.** `tests/test_frontmatter.py`'s
`test_a_paths_block_sequence_may_open_with_an_explanatory_comment` asserts the reader
accepts it; the PyYAML reading was recorded by hand in the file's comments, the way
every other case in that file is. Every new `ambiguous-yaml` rejection should get a
matching case, checked against PyYAML the same way, before it ships.

**First caught:** #58.

### Editing a description or raising a listing ceiling to make a check pass

**Class.** Forbidden outright by `AGENTS.md`'s Boundaries: trimming a skill's
`description`, or raising `listing-budget.json`'s ceiling, only to turn a new gate green,
rather than because the content itself changed for its own reason.

**How it shows up.** Adding the per-skill description ratchet found 33 of the 73
descriptions here already past the 500–900 character guidance, the longest at 971 —
each written and tuned against a measured trigger score; trimming them purely to satisfy
the new gate would have thrown that tuning away for no reason connected to the
description's own job.

**The check that catches it.** `scripts/check_listing_budget.py --update` records the
ratchet at what is actually measured rather than forcing a rewrite, and the commit that
runs it says why. `reviewer` reads any diff to `listing-budget.json` or a `description`
line by line for exactly this.

**First caught:** #23.

**Recurrence:** #97 reshaped three manager-skill trigger sentences and raised their
ratchets solely to clear the portable router's 16 KiB gate. Restore the original trigger
text and ratchets; reduce duplicated router markup while keeping the byte gate and its
100-character per-entry trigger cap. The `description-edited-to-pass` benchmark covers
the original class; `tests/test_catalogue.py` now checks the compact router retains
each skill's trigger and link.

### A count in prose goes stale

**Class.** A specific number written into documentation prose drifts the moment the thing
it counts changes, with nothing tying the sentence to the value.

**How it shows up.** `docs/ci.md` once read "the three warnings are the correct state" for
the per-plugin `no-version` warning `validate-plugin` emits — a sentence that is wrong the
moment the plugin count is not three, which it was not for long.

**The check that catches it.** Phrase the count so it cannot drift — "one warning per
plugin" rather than a fixed number — or have a script own the count the way
`scripts/check_readme.py` owns the skills badge.

**First caught:** #59.

### A script that fails midway leaves a valid-looking partial artefact

**Class.** Building an archive or export incrementally means a failure partway through
can leave a file that looks complete — every member present except the one that made the
run fail — with nothing about the failed run visible from the artefact itself.

**How it shows up.** `package_skills.py` used to check for a repository-root `LICENSE` and
`NOTICE` only after opening the `.skill` archive in write mode; `zipfile.ZipFile` in `"w"`
mode truncates the archive path immediately, so a missing licence file failed after a
partial, plausible-looking archive already existed in `dist/`.

**The check that catches it.** Verify every input exists before opening any output for
writing. `package_skills.py` now checks for `LICENSE` and `NOTICE` at the repository root
before creating the archive, not after.

**First caught:** #61.

### Release artefacts missing the licence notice

**Class.** Anything this repository distributes — a packaged `.skill` archive, the
portable export — has to carry `LICENSE` and `NOTICE` itself; carrying them at the
repository root is not enough once a copy leaves the repository.

**How it shows up.** A packaged skill or a portable bundle installed somewhere else with
no licence text travelling with it, which narrows what the MIT licence actually requires
without anyone deciding that on purpose.

**The check that catches it.** `package_skills.py` and `export_portable.py` both refuse to
run without a `LICENSE` and `NOTICE` at the repository root, and the `mini_repo` test
fixture carries both so the test suite exercises the real path rather than a fixture that
happens to avoid the case.

**First caught:** #61.

### A legal or factual claim states more, or less, than the facts

**Class.** Summarising a licence, a policy or a source in prose can misstate the actual
condition in either direction — broader than what is true, or narrower.

**How it shows up.** The README's Licence section once said MIT's "one condition" was
that the copyright notice travels with a copy; MIT actually requires the copyright notice
*and* the full licence text to accompany every copy, which is a narrower claim than the
licence actually makes.

**The check that catches it.** Quote the source — the licence text, the policy, the
report — rather than paraphrasing it from memory, and check every legal or factual claim
against the primary source rather than against how it reads. This is `investigator`'s job
when the claim is checkable in isolation, and `reviewer`'s when it is one line among many
in a larger change.

**First caught:** #61.

### A permission narrowed on documentation alone breaks the one path that used it

**Class.** Narrowing a workflow's grant on the strength of a provider's published
documentation, with no live run against the real API before trusting it, can leave the
only job that uses that grant unable to do the one thing it exists for.

**How it shows up.** A 403 on the first real write after merge, not on any gate before
it: `ci-triage.yml`'s `pull-requests: write` was narrowed to `read` (with `issues: write`
added instead) because GitHub's published endpoint data lists issue-comment and label
endpoints under "Issues *or* Pull requests", so `issues: write` looked sufficient on its
own. In practice `GITHUB_TOKEN` posting a comment or a label on a pull request needs
`pull-requests: write`, and the narrower grant failed the job's first write once it ran
for real.

**The check that catches it.** A throwaway live run against the real API before trusting
a narrowed grant — no validator or offline gate reads a permission against what the API
actually enforces, so the first genuine write is the only place this shows up.

**First caught:** #79, the live check of #78's triage.

### A personnel plan is disclosed through an operational update

**Class.** The team-aftermath guidance disclosed the existence and outcome of a personnel plan outside the approved group.

**How it shows up.** In #97, `plugins/manager/skills/performance-improvement-plan/SKILL.md` needed this correction.

**The check that catches it.** Review who may receive plan status separately from who needs an operational handover; the benchmark seeds a status disclosure. Patch applicability and schema tests verify the fixture only; they do not prove that a reviewer detects it.

**First caught:** #97, the review stage.

### A mixed-polarity self-check treats yes as no

**Class.** Four prerequisite questions require no to trigger repair, while the last role-mismatch question requires yes. One blanket no rule inverted that last decision.

**How it shows up.** In #97, `plugins/manager/skills/performance-improvement-plan/SKILL.md` needed this correction.

**The check that catches it.** Evaluate each question against its own failure answer; the benchmark reintroduces the blanket rule. Patch applicability and schema tests verify the fixture only; they do not prove that a reviewer detects it.

**First caught:** #97, the review stage.

### An equity comparison omits ownership and conflates share classes

**Class.** The offer reference omitted the fully diluted denominator and treated a preferred financing price as the value of employee common equity.

**How it shows up.** In #97, `plugins/manager/skills/compensation-benchmarking/references/offers-and-equity.md` needed this correction.

**The check that catches it.** Check ownership arithmetic and dated common versus preferred terms separately; the benchmark seeds both errors. Patch applicability and schema tests verify the fixture only; they do not prove that a reviewer detects it.

**First caught:** #97, the review stage.

### Range penetration at a symmetric midpoint is misstated

**Class.** The reference claimed compa-ratio 1.0 could imply different positions in symmetric bands, although midpoint salary is always 50% of each range.

**How it shows up.** In #97, `plugins/manager/skills/compensation-benchmarking/references/band-construction.md` needed this correction.

**The check that catches it.** Recompute the formulas at compa-ratio 1.0 and away from it; the benchmark seeds the false midpoint comparison. Patch applicability and schema tests verify the fixture only; they do not prove that a reviewer detects it.

**First caught:** #97, the review stage.

### An attrition cluster is called a manager cause

**Class.** The manager row called a cluster a finding about the manager without checking team, pay, level, cohort or reorganisation conditions.

**How it shows up.** In #97, `plugins/manager/skills/retention-review/SKILL.md` needed this correction.

**The check that catches it.** Treat clustering as an investigation signal and compare plausible conditions before attribution; the benchmark seeds a causal assertion. Patch applicability and schema tests verify the fixture only; they do not prove that a reviewer detects it.

**First caught:** #97, the review stage.

### A fixed exit count delays a credible report

**Class.** The review told managers to act only on a twenty-exit pattern, delaying credible individual concerns and implying certainty for small aggregate samples.

**How it shows up.** In #97, `plugins/manager/skills/retention-review/SKILL.md` needed this correction.

**The check that catches it.** Separate action on a credible report from confidence in a population trend; the benchmark restores the fixed threshold. Patch applicability and schema tests verify the fixture only; they do not prove that a reviewer detects it.

**First caught:** #97, the review stage.

### A separate reviewer inherits the implementation context

**Class.** A separate reviewer identity is treated as independent even when it inherits
implementation or coordinator history.

**How it shows up.** The ChatGPT workflow required a separate reviewer without requiring
fresh, non-inherited context, so a default history-inheriting dispatch could satisfy SHIP.

**The check that catches it.** Inspect the actual dispatch or fresh-session boundary and
reviewer's transcript observation; return STOP when independence is unavailable or
unobservable. The benchmark reintroduces identity-only dispatch. Fixture schema and
patch-applicability tests verify the fixture, not live reviewer detection.

**First caught:** #107, the [automated PR reviewer finding](https://github.com/greenblacked/AI/pull/107#discussion_r4165131426).
