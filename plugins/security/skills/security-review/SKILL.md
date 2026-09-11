---
name: security-review
description: "Review a change for the vulnerability classes actually exploited, in a fixed order: establish what the diff reaches and who can reach it, object-level authorisation rather than route-level, injection across SQL, command, template and LDAP, deserialisation, server-side request forgery, secrets reaching a log or the repo, unsafe defaults, and the dependency or build-step change that is the supply-chain risk under OWASP A03 2025; report each finding as reachable path, impact, fix. Use this skill whenever a diff, branch or pull request needs a security look before merge, or someone asks \"is this endpoint safe\", \"can you security review this PR\", \"does this need an authz check\", or \"did we just commit a key\". Not for general correctness review (code-review), live IAM audits (access-review), an already-leaked credential (secret-rotation), Terraform (iac-review), or images (image-hardening)."
allowed-tools: "Bash(git:*), Bash(gh:*), Bash(rg:*), Read, Grep, Glob"
---

# Security Review

A security review is finished when every changed entry point has a named principal, a stated authorisation decision and an injection verdict, and every finding raised carries a path an attacker can reach, the impact when they do, and the fix — with no exploit written down.

The job fails in a small number of recognisable ways. The review reads the diff line by line and never asks what the changed code is reachable from, so a helper that looks harmless is missed because its one caller is an unauthenticated webhook. Authorisation is checked at the route — the middleware requires a logged-in user — and nobody checks whether the record fetched by the id in the path belongs to that user, which is the single most common exploited defect in the field. Injection is judged by the presence of escaping rather than by whether user data crosses a parser boundary as syntax, so a parameterised query sitting beside a dynamically built `ORDER BY` passes. The dependency bump and the new build step are skimmed as housekeeping, which is exactly why OWASP moved software supply chain failures up to A03 in the 2025 Top 10. And the findings that are correct get argued away, because they are written as a class name rather than as a reachable path with an impact, so the author answers "that input is always internal" and the thread dies. The order below forces reachability first, authorisation before syntax, and a report shaped so the conversation is about the fix.

## Scope

Use for: reviewing a diff, branch or pull request for exploitable weakness before it merges; deciding whether a changed endpoint, handler, query, template, deserialiser or outbound fetch is safe; checking that a change touching authentication or session handling did not weaken it; catching a secret or a risky dependency or build-step change while it is still in review; writing the finding up so it gets fixed.

Do not use for: general correctness, design and readability review of a diff, which is `code-review`; auditing who holds which permission in a live cloud or identity estate, which is `access-review`; rotating or containing a credential that has already leaked, which is `secret-rotation`; a Terraform or other infrastructure-as-code diff, which is `iac-review`; hardening a container image or base layer, which is `image-hardening`; or upgrading a dependency for its own sake, which is `dependency-upgrade`.

This skill is defensive. Naming a class, a payload shape and the fix is the work; producing usable exploit code, credentials or steps whose obvious use is unauthorised access is not, and this procedure does not do it.

## Hard gates

1. **Reachability before severity.** A class with no path from an untrusted input is an observation, not a finding. Establish the path first, and say so when you cannot.
2. **Object-level authorisation is checked separately from route-level.** They are different defects with different fixes, and passing the first tells you nothing about the second.
3. **Trust boundary, not input name.** "Internal" is a deployment fact that changes without the code changing. Judge by whether the value crossed a boundary the process controls.
4. **No exploit artefacts.** Describe the payload shape in words — a single quote terminating the literal, a path segment escaping the root — never a working string, credential or request.
5. **Deleted and moved code is reviewed.** A removed check is invisible in a diff read for additions only, and it is the cheapest severe finding available.
6. **A finding with no fix is half a finding.** The author is the person who will apply it, so the concrete change goes in the report.

## Workflow

### 1. Establish what changed and what it reaches

Read the change as a shape before reading it as lines.

```bash
git diff --stat origin/main...HEAD
git diff origin/main...HEAD -- '*.sql' '*.tf' 'package-lock.json' 'go.sum' 'requirements*.txt'
git log origin/main...HEAD --format='%an %s'
gh pr diff <number>
```

Answer three questions in writing before reviewing any line: which entry points the change adds or alters (route, queue consumer, cron, webhook, CLI, scheduled job); which of those an unauthenticated party can reach; and which changed function is called from one of those, however indirectly. A helper is exactly as exposed as its most exposed caller.

### 2. Walk the classes in this order

The order is by how often the class is exploited and by how much later checks depend on earlier ones. Do not reorder it for convenience; injection found in a handler nobody may call is worth less than a missing ownership check in one everybody can.

| Order | Class | What to look for in the diff | Verdict is |
| --- | --- | --- | --- |
| 1 | Broken access control | An identifier arriving from the request and used to fetch, update or delete without a check that the caller owns the object | The named check, on the named object, in the named handler |
| 2 | Injection | User-controlled data reaching a SQL, shell, template, LDAP, XPath or ORM-fragment parser as syntax rather than as a bound value | Every sink in the diff classified as parameterised, allow-listed, or exploitable |
| 3 | Insecure deserialisation | A native deserialiser, object mapper with polymorphic typing, or pickle-equivalent given bytes the process did not produce | The format changed to data-only, or the type allow-list named |
| 4 | Server-side request forgery | An outbound request whose host, path or scheme is influenced by input, including redirects and webhook targets | The allow-list, and whether redirects are re-validated |
| 5 | Secrets and sensitive data | A literal credential, a token in a log line, an error body echoing internals, a new file that bypasses ignore rules | Removed from the diff, or confirmed a placeholder |
| 6 | Unsafe defaults | A permissive default that only the caller's diligence closes — verification off, wildcard origin, debug on, a temporary file with wide permissions | The default inverted, so omission is safe |
| 7 | Supply chain | A new or bumped dependency, a changed lockfile, a new build or CI step, an unpinned action or image tag | The provenance, the pin, and what the step can reach |

### 3. Review authorisation properly

Route-level authorisation answers "is this caller authenticated, and does their role permit this kind of operation". Object-level authorisation answers "does this specific caller have a relationship with this specific record". Middleware gives you the first and cannot give you the second, because it runs before the record is loaded and does not know which record is coming.

For every request-supplied identifier in the diff, state the answer to all four:

- **Who is the principal**, and is it derived from the session or the request body? An owner id taken from the payload is an authorisation bypass with extra steps.
- **Which object is being reached**, and is the ownership or tenancy predicate part of the query that loads it rather than a check performed afterwards? A check after the load still leaks existence through timing and error differences, and it is one refactor away from being dropped.
- **Is the check present on every verb**? Read is usually guarded and update, delete and the bulk or export path frequently are not. List endpoints are the worst case: one missing tenant predicate returns the whole table.
- **Does the identifier permit enumeration**? A sequential id is not itself the vulnerability, but it converts a missing check from a targeted attack into a complete extraction, so it changes severity.

Where the change adds a role, scope or claim, check the default for an unknown value. A comparison that grants when the role is unrecognised fails open, and unrecognised is precisely the state of a token minted by an older or newer service.

`references/class-checks.md` has the per-class checks with the sink inventories, the language-specific shapes each one takes, and the fix for each. Read it when working step 2 for a class you are not fluent in, or when you need the full sink list for a language in the diff.

### 4. Treat a change to authentication as a different, higher bar

When the diff touches login, session issue or validation, token verification, password or key handling, or multi-factor logic, ordinary review is insufficient — these defects are unrecoverable once shipped, and the blast radius is every account.

- Verify the token signature check validates algorithm and issuer as well as the signature, and rejects rather than accepts an algorithm it does not recognise.
- Verify expiry is checked on every use and not only at issue, and that the clock skew allowance is bounded.
- Confirm session identifiers are regenerated at privilege change — login, elevation, impersonation — because a session fixed before login stays valid after it otherwise.
- Confirm logout and password change invalidate existing sessions and refresh tokens server side, not only the cookie.
- Check that failure paths are uniform: a login that distinguishes unknown user from wrong password is an account enumeration oracle, and the fix is one error and one timing profile.
- Check rate limiting and lockout exist on the credential path and are keyed on something the attacker does not choose freely.
- Where the change adds its own cryptography or its own comparison, that is the finding. Constant-time comparison for secrets, vetted library primitives, and no hand-rolled token format.

If the change is large enough that these cannot all be answered from the diff, say so and ask for the design rather than approving the parts you could read.

### 5. Judge the supply-chain part of the diff as code

OWASP's 2025 Top 10 raises software supply chain failures to A03, above injection, on the basis that the dependency and build surface is now where compromise actually enters. A lockfile change is a code change with no review.

- A new direct dependency: who maintains it, how recently, how many transitive packages it drags in, and whether a well-maintained alternative or the standard library covers the use.
- A bumped dependency: whether the bump is the advertised version — a lockfile whose resolved URL or integrity hash points somewhere unexpected is the finding.
- A new install or postinstall script, build plugin, code generator or CI step: it executes with the build's credentials and network. Ask what it fetches and what it can write.
- Pinning: an action or image referenced by a mutable tag is whatever the publisher moved it to this morning. A full commit SHA or a digest is what makes it immutable.
- Credential exposure in the pipeline: a step that runs untrusted contributor code with a write-scoped token or secret access is a repository takeover path, and it is a normal review finding rather than an exotic one.

### 6. Write each finding as reachable path, impact, fix

A finding gets fixed when the author cannot dispute that it is reachable and can see what to change. Three parts, in this order, per finding:

- **Reachable path** — the entry point, the principal who can use it, and the call chain to the sink. Where you could not establish reachability, write "unconfirmed" rather than implying it; an honest unconfirmed finding survives, an overstated one discredits the rest.
- **Impact** — what the attacker obtains or changes, in terms of the system's own data. "Any authenticated user can read any other tenant's invoices" ends the argument that "that is internal".
- **Fix** — the specific change at the right layer, plus whether the same defect exists elsewhere in the codebase. A class found once is usually present three times.

Rank by exploitability times impact, not by class name. State severity with its reason attached, and keep the count of blocking findings small enough that blocking means something.

`references/reporting.md` has the severity rubric, the wording that survives a disagreement, and how to handle a finding that is real but out of scope for the change under review. Read it when a finding is being disputed, or when deciding whether something blocks the merge.

## What this review does not certify

Say this out loud in the report, because silence is read as coverage. A diff review sees the change, not the system: it cannot clear the code the change calls but does not touch, business logic whose rules you were not told, the deployed configuration, or anything reachable only through a component outside the repository. Where a finding depends on one of those, name the assumption.

## Output format

```markdown
## Verdict
[Blocking findings: N. Non-blocking: N. One sentence on whether this can merge.]

## Attack surface touched
[Entry points added or changed, which are unauthenticated, and which changed functions
they reach.]

## Findings
### [N]. [Class] — [severity]
Reachable path: [entry point, principal, call chain to the sink. Or "unconfirmed", with
what would confirm it.]
Impact:        [what an attacker obtains or changes, in this system's own terms.]
Fix:           [the specific change, at the layer it belongs, and whether the same defect
                appears elsewhere.]

## Authentication review
[Only when the diff touches auth. The answers from step 4, including the ones that could
not be answered from the diff alone.]

## Supply chain
[Dependency, lockfile, build-step and pinning changes, each with its verdict.]

## Not covered
[What this review could not see: untouched callers, deployed config, business rules not
supplied. Named, so nobody reads silence as clearance.]
```

## Anti-patterns

**Reviewing the diff without establishing reachability.** Findings are raised by pattern match, the author replies that the input is internal, and the thread ends with nothing changed — including the two findings that were genuinely reachable. Establish the entry point and the call chain first, and the same finding becomes unarguable.

**Accepting route-level authorisation as the authorisation check.** The middleware proves the caller is somebody; the handler then loads a record by an identifier the caller supplied. This is the most exploited defect class in the field and it passes every review that stops at the middleware. Check ownership at the query that loads the object.

**Judging injection by the presence of escaping.** Escaping is a guess about a parser's grammar made by code that does not contain the parser. A query that is parameterised everywhere except its sort column is an exploitable query, and it reads as safe. Ask whether user data can become syntax, sink by sink.

**Skimming the lockfile.** A dependency change is executable code entering the build with no review, which is why OWASP moved supply chain failures to A03 in the 2025 list. Read the resolved versions, integrity hashes and any new install-time script with the same attention as a handler.

**Reading only added lines.** A deleted authorisation check, a removed validation, a guard clause lost in a refactor — all invisible when the review scans for new code. Removals are the cheapest severe findings in any diff and the ones nobody looks for.

**Severity assigned by class name.** "Injection: critical" applied to a shell call whose only argument is a compile-time constant spends the author's trust on nothing, and the next genuine critical is discounted. Severity is exploitability times impact on this system, and the reason travels with the label.

**Writing a working exploit to prove the point.** It converts a review comment into an attack tool that lives in the repository history and the ticket forever, and it is not needed: the reachable path plus the impact already ends the argument. Name the payload shape, never the payload.

**Approving a change to authentication from the diff alone.** Session handling, token validation and credential storage fail in ways that are invisible without the surrounding design — what invalidates a session, which service mints the token, what the default is for an unknown claim. Ask for the design or restrict the approval to what you actually read.

**Raising forty findings.** Everything blocks, so nothing does, and the author triages the list by choosing the cheap ones. Rank ruthlessly, block on the few that are reachable and severe, and file the rest where they will be picked up rather than in the same thread.

## Reference files

- `references/class-checks.md` — read when working step 2 on a class you are not fluent in, or when you need the full sink inventory for a language present in the diff: the per-class checks for access control, injection across SQL, command, template and LDAP, deserialisation, request forgery, secret exposure and unsafe defaults, each with the shapes it takes per language and the fix.
- `references/reporting.md` — read when a finding is being disputed, or when deciding whether one blocks the merge: the severity rubric with its exploitability and impact axes, the wording that keeps a finding about the fix, how to handle a real finding that is out of scope for this change, and the supply-chain review checklist for a dependency or build-step diff.
