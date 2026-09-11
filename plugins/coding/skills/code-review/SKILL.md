---
name: code-review
description: "Review a change — a diff, a pull request, a branch — in a fixed severity order: correctness first (does it do what its description claims, what happens on the error path, what happens under concurrency, what happens with hostile input), then tests, then maintainability, with a severity label on every finding and nits named as nits. Covers reviewing a diff you cannot run, sampling a large diff honestly instead of pretending to have read it, and writing a comment that gets acted on rather than argued with. Use this skill whenever someone asks you to look over a change — \"review my PR\", \"can you check this diff before I merge\", \"is this safe to ship\", \"what did I miss in #412\", \"give this branch a once-over\". Not for a red pipeline, which is ci-triage; not for designing a test suite, which is test-design; not for restructuring without behaviour change, which is refactoring; not for a dedicated threat model, which is security-review."
allowed-tools: "Read, Grep, Glob, Bash(git:*), Bash(gh:*), Bash(rg:*), Bash(jq:*)"
---

# Code Review

A review is finished when every claim the change makes has been checked against the code that implements it, and every finding carries a severity that survives being read by the author six hours later.

The job goes wrong in five reliable ways. The reviewer opens with the cheapest observations — naming, import order, a docstring — because those are findable without understanding anything, and by the time attention runs out the error path has never been read. The reviewer reads the diff and not the code around it, so a function that is correct in isolation and wrong at its two call sites passes. The reviewer treats the description as evidence rather than as a claim to be tested, which is the specific failure that matters most now that much of the code under review was generated: Stack Overflow's 2025 survey found 66% of developers spend more time than expected debugging AI-generated code and 45% describe it as "almost right, but not quite", and Sonar's 2026 developer survey reports 96% do not fully trust the functional accuracy of generated code, with the burden having moved from writing to verification — near-miss code reads well and fails on the branch nobody exercised. The reviewer emits twenty findings with no severity, so the author picks the three that are easiest to fix. And the reviewer, faced with 2,000 lines, skims all of it and approves, which is worse than reading 200 lines and saying so. This skill fixes the order, forces a severity on every finding, and makes partial coverage something you declare rather than hide.

## Scope

Use for: reviewing a diff, a pull request, a branch or a patch before merge; a second opinion on a change someone else already approved; reviewing code you or another model generated; deciding whether a change is safe to ship.

Do not use for: a failing pipeline, which is `ci-triage`; driving an observed bug down to its cause, which is `debugging`; designing what a suite should test, which is `test-design`; restructuring code that is not changing behaviour, which is `refactoring`; a dedicated threat-model or authorisation pass, which is `security-review`; reviewing an interface contract before it is built, which is `api-design`; writing the change in the first place, which is `code-scaffold`.

## Hard gates

Breaking one of these does not make the review slower, it makes it dishonest.

1. Read the change's stated purpose first, then verify the code does that. The description is the claim, not the evidence.
2. Correctness findings are complete before a single style comment is written. A style comment at the top of a review is a signal to the author that nothing worse was found.
3. Every finding carries one of four severities: blocking, should-fix, consider, nit. A finding with no severity is a finding the author gets to rank.
4. A nit is not a finding. Cap nits, prefix them, and be willing to have none.
5. State your coverage. "I read the migration and the handler, not the front-end changes" is a complete and useful review; implying you read all of it is not.
6. Quote the line you are talking about and say what happens, not what you would have written.

## Workflow

### 1. Establish what the change claims

Read the title, description, linked issue and commit messages before the diff. Write down, in one sentence, what this change is supposed to do and what it is supposed not to do. Everything below tests that sentence.

```bash
gh pr view 412 --json title,body,files,additions,deletions,commits
gh pr diff 412
git log --oneline main..HEAD && git diff main...HEAD --stat
```

Two things to catch here, before any code. A change whose diff touches areas the description never mentions is either mislabelled or is two changes — say which. And a description that describes intent in terms of behaviour ("orders now retry on timeout") gives you a testable claim, while one that describes mechanism ("added a retry wrapper") gives you nothing to check; ask for the first.

### 2. Read the code, not only the diff

The diff shows what moved. Correctness lives in what surrounds it.

For each changed function, open the file and read the whole function, then find its callers:

```bash
rg -n 'chargeCustomer\(' --glob '!test*'
git log -n 5 --oneline -- path/to/changed_file.py
git log -S 'retryOnTimeout' --oneline          # when this behaviour arrived, and why
```

The reviews that catch real defects are the ones that ask what the change means at the call sites, not what it means on its own lines. A new parameter with a default is safe in the function and wrong at every existing caller that should have passed something else. A widened return type is safe until you read the three places that switch on it.

`git log -S` on a line the change deletes is the cheapest way to find out whether it was load-bearing. Code removed because it "looks unused" is a recurring cause of the regression that arrives a month later; the commit that added it usually says why.

### 3. Correctness, in this order

Work these four in sequence and finish each before moving on. This is the ordering the whole skill exists to impose.

| Pass | The question | What it catches |
| --- | --- | --- |
| Claim | Does the code do what the description says, exactly, including the boundary the description implies? | The near-miss: right shape, wrong condition. Off-by-one, an inverted comparison, a guard that returns early on the wrong branch. |
| Error path | For every call that can fail, what happens when it does — and is the resulting state still valid? | Swallowed exceptions, a partially applied update with no rollback, a retry over a non-idempotent call, an error logged and then execution continuing as if it had not. |
| Concurrency and ordering | What happens if two of these run at once, or the second arrives before the first completes? | Read-modify-write without a lock or a conditional update, a check-then-act on shared state, an unbounded queue, a cache written before the source of truth. |
| Hostile or absent input | What does an empty, huge, negative, null, duplicated or attacker-chosen value do here? | Unvalidated input reaching a query or a shell, a limit that a caller controls, a regex over user input with backtracking, an authorisation check that runs after the fetch it was meant to guard. |

Two rules make this pass work rather than become a checklist recited at the end of a review. Ask each question against the specific lines in front of you and write the answer down, even when the answer is "this call cannot fail" — an unwritten answer was usually not asked. And when you cannot answer one from the diff, that is itself a finding: "I cannot tell from this diff whether `applyCredit` is called inside the transaction — if not, a failure after line 88 leaves the credit applied and the order unpaid."

`references/correctness-checklist.md` has the per-pass question lists with the concrete code shapes each one looks for, including the resource, state-machine and data-migration cases that do not fit the four passes cleanly. Read it while working step 3 on a change with real consequences — money, auth, persistence or concurrency.

### 4. Then tests

Only once correctness is done. Assess the tests against the defects you just looked for, not against a coverage number.

- Does a test exist that fails if this change is reverted? If not, the change is unverified regardless of what the suite reports.
- Are the error and concurrency paths from step 3 exercised, or only the happy path?
- Does any test assert on a mock's behaviour rather than the system's? A test that verifies the mock was called with certain arguments passes when the real call signature changes underneath it.
- Is the test deterministic — no wall-clock, no network, no ordering dependency on another test, no sleep standing in for a wait condition?

A missing test for a changed behaviour is a should-fix. A missing test for a behaviour the change's own description calls out is blocking.

### 5. Then maintainability, briefly

Now, and only now, the things that make the code liveable: naming that misleads (not naming you would have chosen differently), duplicated logic that will drift, a function whose control flow you had to read three times, a comment that contradicts the code, a magic number without a source. Each of these is a `consider` unless you can state the failure it will cause.

Everything that survives no stronger justification than personal preference is a nit or is dropped. Prefer dropped. A reviewer who reliably raises formatting has trained their authors to skim reviews.

### 6. Grade, and say what you did not read

Assign a severity to every finding before writing any of them up, in one pass, so the grades are relative to each other rather than to your mood when you wrote each one.

| Severity | Means | Test for it |
| --- | --- | --- |
| blocking | This will cause incorrect behaviour, data loss, a security hole or an outage. | You can describe the input or the sequence that makes it fail. |
| should-fix | Real defect, bounded consequence, or a missing test for changed behaviour. | It will cost someone real time later, but it will not corrupt anything. |
| consider | A better approach exists and you can state what it buys. | The author declining it is a reasonable outcome. |
| nit | Preference. | You would not mention it if the review were verbal. |

Then state coverage explicitly: which files you read fully, which you sampled, which you did not open, and what would change your verdict. A review that says "I read the payment path closely and did not review the 900 lines of generated client code" is more useful than one that implies uniform attention, because the next reviewer knows where to look.

## Reviewing a diff you cannot run

Most reviews are this. You have text and no environment, so be explicit about what that removes and route around it.

- Trace the two or three most consequential paths by hand, naming each line as you go, rather than forming an impression of the whole. The output of the trace is what you quote in the finding.
- Read the tests as a specification of intended behaviour, then check whether the implementation matches the specification the tests imply. A mismatch between the two is usually a real defect and is findable without running anything.
- Use history where you cannot use execution: `git log -S`, `git blame` on the lines being changed, and the previous incident or revert that touched the same file.
- Convert anything you genuinely cannot determine into a question with a stated consequence, not a hedge. "What is the behaviour when `items` is empty? If it returns 0 the invoice total is wrong for refunds" is actionable; "have you considered empty lists?" is not.
- Say which findings are unverified. A blocking finding you could not confirm is still worth raising, labelled as such.

## Reviewing a large diff

Above roughly 400 changed lines, review quality falls off and the honest options are to split it or to review part of it deliberately. Never skim the whole thing and approve.

1. Ask for it to be split first. That is the correct answer and it is available more often than people accept.
2. If it cannot be split, sort the files by risk rather than reading in diff order: schema and migrations, authentication and authorisation, money and billing, concurrency and queues, public interfaces, then everything else. Generated files, lockfiles, vendored code and mechanical renames go last and are checked as a class, not line by line.
3. Set an explicit budget and spend it top-down. Review the highest-risk third properly and declare the rest unreviewed, rather than spreading the same attention over everything.
4. For mechanical changes, verify the mechanism rather than the instances: check the codemod or the find-and-replace pattern, then spot-check three call sites, and say that is what you did.
5. `git diff main...HEAD -- path/` per risk area keeps each pass small enough to hold in your head. Reviewing per-commit is better still when the commits are clean.

The pathology to avoid is uniform attention. Every line getting equal scrutiny means the migration and the README change got the same amount, which means the migration got too little.

## Writing a comment that gets acted on

A finding is only worth the time it took if the author acts on it. Four properties do that work.

| Do this | Not this |
| --- | --- |
| State the consequence: "if `resp` is nil here the deref on line 94 panics and the request 500s." | State the rule: "should check for nil." The author has to reconstruct why it matters before they can agree. |
| Point at the line and quote it, so the author does not have to find what you mean. | Describe it in prose: "in the handler somewhere there's an unchecked error." |
| Ask a real question when you are genuinely unsure, and say what answer would satisfy you. | Ask a rhetorical question. "Are we sure this is thread-safe?" reads as an accusation and carries no information. |
| Say it once, at the first instance, and note that it recurs. | Repeat the same finding on nine lines, which turns one issue into a wall and buries the blocking one. |

Prefix nits with `nit:` so they can be triaged in one pass. Attach the reason a rule exists rather than its name; "this is O(n squared) over a list that is user-controlled" moves an author that "avoid nested loops" does not. And review the change in front of you rather than the change you would have written — a rewrite proposal disguised as a review is the most common way a review stalls a week.

Approving with non-blocking comments outstanding is usually correct and is what keeps a review culture fast. Reserve blocking for findings where you can name the failure.

`references/review-comment-craft.md` has worked before-and-after examples of findings at each severity, the phrasings that get a defensive response and their replacements, and how to handle disagreement, a review you are unsure about, and a change generated by a model. Read it before writing up a review that is going to be contentious or that carries several blocking findings.

## Output format

```markdown
## Verdict
[Approve / approve with comments / request changes — one sentence with the reason.]

## Coverage
[Which files were read fully, which were sampled, which were not opened. What would change the verdict.]

## Blocking
[Each: file:line, the quoted code, the input or sequence that makes it fail, the consequence.]

## Should fix
[Each: file:line, what is wrong, what it costs. Missing tests for changed behaviour go here.]

## Consider
[Each: the alternative and what it buys. The author declining is a fine outcome.]

## Nits
[One line each, prefixed. Omit the section if there are none.]

## Questions
[What you could not determine from the diff, each with the consequence that hangs on the answer.]
```

## Anti-patterns

**Opening with style.** Naming and formatting at the top of a review tells the author that the reviewer's attention peaked on the cheap findings, and it anchors the whole thread on preference. The blocking finding three screens down is then read as one more opinion. Finish correctness before the first style comment exists.

**Reviewing the diff without the file.** The diff hides the invariant the function relied on and every caller that now behaves differently. This is how a change that is locally correct ships a regression, and it is the single most common way a careful review misses a real defect.

**Taking the description as evidence.** The description says what the author intended; near-miss code says something adjacent. With 45% of developers reporting generated code is "almost right, but not quite" (Stack Overflow 2025), reading the description and then skimming for agreement finds exactly nothing, because the code does look right.

**Findings without severity.** Twenty equal-weight comments get triaged by cost to fix, so the rename gets done and the race condition gets a "good catch, follow-up" that never lands. Grading costs two minutes and decides which findings are actually acted on.

**Approving a 2,000-line diff you skimmed.** The approval is a statement that someone checked, and the team now believes it. Better to review the migration and the auth change properly, say so, and leave the rest openly unreviewed, than to launder a skim into a signature.

**Rewriting the change in the comments.** A review that proposes a different design after the work is done costs a week and usually loses. If the design is wrong, say that as one blocking finding with the consequence, and move the conversation off the diff.

**The rhetorical question.** "Did you think about concurrency here?" carries no information, invites a defensive answer and often turns out to be wrong. Ask the specific question with the specific consequence, or trace it yourself and make it a finding.

**The same nit nine times.** Repetition converts one preference into the dominant impression of the review. Say it once at the first occurrence, note that it recurs, and let the author decide whether to sweep.

**Passing on the error path because the happy path is right.** Error handling is where the defects that page someone live: partial writes, swallowed failures, retries over non-idempotent calls. It is also the least-read part of any diff, which is precisely why it is worth a pass of its own.

## Reference files

- `references/correctness-checklist.md` — read while working step 3 on any change touching money, authentication, persistence or concurrency: the question list per pass, the specific code shapes each question is looking for, and the resource, state-machine and data-migration cases the four passes do not cover cleanly.
- `references/review-comment-craft.md` — read before writing up a contentious review or one with several blocking findings: worked before-and-after findings at each severity, phrasings that provoke a defensive reply and their replacements, and how to handle disagreement, low confidence, and a change a model generated.
