# Reporting a security finding

Read this when a finding is being disputed, when deciding whether one blocks the merge, or
when reviewing the dependency and build-step part of a diff.

## Contents

- [The severity rubric](#the-severity-rubric)
- [Wording that survives a disagreement](#wording-that-survives-a-disagreement)
- [The real finding that is out of scope](#the-real-finding-that-is-out-of-scope)
- [Supply-chain review checklist](#supply-chain-review-checklist)

## The severity rubric

Severity is exploitability multiplied by impact on this system. Both axes are judged from
the reachable path established in step 1, never from the class name.

**Exploitability** — pick the highest row that applies.

| Level | Condition |
| --- | --- |
| Reachable by anyone | An unauthenticated entry point reaches the sink with no precondition the attacker does not control |
| Reachable by any user | Any registered or authenticated principal reaches it, including a free-tier or self-service account |
| Reachable by a scoped principal | Requires a role, tenancy or relationship the attacker must first obtain |
| Reachable with a precondition | Requires a state the attacker cannot set directly, a race, or another defect first |
| Not established | You could not find a path. Say so; the finding stays, the severity does not inflate |

**Impact** — what the attacker obtains or changes, in the system's own nouns.

| Level | Condition |
| --- | --- |
| Critical | Code execution in the service, credential or key disclosure, authentication bypass, or read or write across every tenant |
| High | Read or write of another tenant's or user's data, privilege escalation within the application, or disclosure of a secret with limited scope |
| Medium | Disclosure of internal structure, a single-tenant integrity or availability effect, or a control weakened such that another defect becomes exploitable |
| Low | Defence in depth: a missing hardening measure with no path established through it today |

Blocking is a separate decision from severity, and it is the one that keeps the review
credible. Block on anything critical or high with an established path. Everything else is
reported and tracked. A review where nine findings block is a review the author triages by
price rather than by risk.

## Wording that survives a disagreement

A finding is disputed when it reads as an accusation of a category rather than a
description of a path. Three properties keep the conversation on the fix.

- **Lead with the path, not the class.** "The export handler loads the invoice by the id
  in the path and returns it without a tenant predicate" is a fact about the code. The
  class name alone is a label the author can decline.
- **State impact in the system's own data.** "Any authenticated user can read any other
  tenant's invoices" cannot be answered with "that endpoint is internal", because the
  sentence already names who reaches it.
- **Propose the fix at the layer it belongs.** A fix in the handler is accepted and
  repeated; a fix demanding a new architecture is deferred. If the correct fix is
  structural, say what closes it today and what closes it properly, and separate them.

Two failure modes to avoid in the writing itself. Overstating an unconfirmed path spends
the credibility the rest of the report needs — write "unconfirmed" and name what would
confirm it. And including a working exploit converts the review into an attack tool stored
in the repository history and the ticket system permanently; the payload shape in words is
sufficient to identify the defect, which is the only thing the author needs.

When the author disagrees on reachability, the resolution is a fact, not a further
opinion: name the caller you believe reaches it, and ask which control stops it. Either
the control exists and the finding closes honestly, or it does not and the finding stands.

## The real finding that is out of scope

A review of one change routinely surfaces a defect the change did not introduce. Holding
the change hostage to it is how security review gets a reputation that makes the next one
harder.

- If the change makes the pre-existing defect reachable or materially worse, it is in
  scope for this review and blocks on the rubric above.
- If the defect is severe and merely adjacent, file it separately with the same three-part
  shape, name it in the review as out of scope, and do not block.
- If the change is an improvement that does not go far enough, approve it and file the
  remainder. A partial fix that merges beats a complete fix that is still in review.

Record the class, not only the instance. A class found once is usually present in several
places; a search for the same sink shape across the repository is cheap at the moment you
already know what to look for and expensive six months later.

## Supply-chain review checklist

OWASP's 2025 Top 10 raises software supply chain failures to A03. Work a dependency or
build-step diff through this list rather than skimming it.

- **New direct dependency**: maintenance recency, maintainer count, transitive package
  count added, and whether the standard library or an existing dependency already covers
  the use. A package added for one function is a permanent attack surface for one
  function.
- **Name**: confirm it is the package intended. Substitution relies on a plausible name, a
  hyphen or a different registry, and on a reviewer reading the diff quickly.
- **Version bump**: does the lockfile's resolved version, registry URL and integrity hash
  match what the manifest claims? A resolved URL pointing somewhere unexpected is the
  finding.
- **Install-time and build-time execution**: any postinstall script, build plugin, code
  generator or native build step runs with the build's credentials and network access.
  Ask what it fetches and what it writes.
- **Pinning**: actions, base images and downloaded tools referenced by a mutable tag are
  whatever the publisher moved the tag to. A full commit SHA or an image digest is what
  makes the reference immutable; the version comment beside it is what lets a bot upgrade
  it deliberately.
- **Fetch-and-run**: a step that downloads a script and pipes it into a shell has no
  review and no integrity check. Pin a version and verify against a recorded digest.
- **Credential reach in CI**: a workflow step that executes contributor-controlled code
  while a write-scoped token or a secret is available is a repository takeover path.
  Confirm the token permissions are scoped per job and that untrusted code runs in a job
  that holds neither.
- **Provenance and integrity**: where the ecosystem offers signed builds, attestations or
  a lockfile integrity mode, confirm the change does not disable them. A flag that skips
  integrity checking to make the build pass is the finding, not the fix.
