# Establishing Reachability

The procedure behind step 4 of `SKILL.md`. Read when you have a specific finding and need to decide whether your code can actually reach the vulnerable function, rather than whether the vulnerable package is installed.

The framing that keeps this honest: a reachability tool answers "did I find a path", and the absence of a path is evidence, not proof. Every technique below has a false-negative mode, and each section names its own.

## Contents

- [What each level of evidence is worth](#what-each-level-of-evidence-is-worth)
- [Go: govulncheck](#go-govulncheck)
- [npm and the JavaScript ecosystem](#npm-and-the-javascript-ecosystem)
- [Python](#python)
- [Java and Maven](#java-and-maven)
- [Rust](#rust)
- [The manual call-path trace](#the-manual-call-path-trace)
- [Where reachability analysis is wrong](#where-reachability-analysis-is-wrong)
- [Recording the result](#recording-the-result)

## What each level of evidence is worth

| Evidence | Strength | What you may conclude |
| --- | --- | --- |
| A tool reports a symbol-level call path from your code to the vulnerable function | Strongest | Reachable. Act on it |
| The advisory's affected symbol is imported somewhere in your tree | Strong | Treat as reachable until a manual trace says otherwise |
| The package resolves in the lockfile but nothing imports it | Moderate | Not reachable today; batch the fix and consider removing the package |
| The vulnerable path needs a config, flag or plugin you do not enable | Moderate, and perishable | An exception with a date, not a dismissal — configuration changes |
| A tool reported "not called" and you did not read the advisory | Weak | You know the tool found no path, which is not the same claim |
| "It is only a dev dependency" | Not evidence of reachability at all | Answers a different question. See the credentials test in `SKILL.md` step 2 |

## Go: govulncheck

The strongest answer available in a mainstream ecosystem, because the toolchain ships type information and a complete build graph.

```bash
go install golang.org/x/vuln/cmd/govulncheck@latest

govulncheck ./...                    # source mode; symbol-level by default
govulncheck -test ./...              # include test files and their dependencies
govulncheck -show=verbose ./...      # show the full call stacks, not just the summary
govulncheck -json ./...              # machine-readable, for joining against your queue
govulncheck -mode=binary ./bin/app   # analyse a built binary with no source tree
```

What it does: resolves your module graph against the Go vulnerability database, then runs a static call-graph analysis to decide, per vulnerability, whether any of the affected symbols is reachable from your package's entry points. The output separates the two cases explicitly — vulnerabilities called by your code, and vulnerabilities present in the module graph but with no affected symbol called. That split is the triage decision handed to you for free, and it is why Go findings should almost never be worked from a Dependabot list instead.

The `-scan` flag controls granularity: `symbol` is the default and the useful one, `package` and `module` are progressively coarser and correspondingly noisier. Do not lower it to make the analysis faster; a module-level result is the same information Dependabot already gave you.

What it misses:

- **Reflection.** A call reached only through `reflect.Value.Call` has no static edge. Code that dispatches handlers by name out of a registry is the common real-world shape.
- **cgo.** Anything crossing into C is outside the analysis.
- **`go:linkname` and assembly.** Edges the compiler honours and the call-graph builder does not model.
- **Binary mode is coarser than source mode.** For binaries built with older toolchains the analysis may fall back to package-level results, so a "no affected symbol" from binary mode is a weaker claim than the same sentence from source mode.
- **Database coverage.** It reads the Go vulnerability database (`GO-YYYY-NNNN` identifiers). That database is curated and maps published CVEs, but with a lag, and a vulnerability with no Go entry yet produces a clean run that is correct and incomplete at the same time. Cross-check the queue against GHSA or OSV rather than treating a green `govulncheck` as the whole answer.
- **Stdlib findings need the toolchain, not a dependency bump.** `govulncheck` reports vulnerabilities in the Go standard library against the version you built with; the fix is a toolchain upgrade, which no dependency-management tool will offer you.

## npm and the JavaScript ecosystem

No free tool produces symbol-level reachability here. Dynamic `require`, bundler transforms, monkey-patching and the general absence of types make a sound call graph expensive, which is why the vendors that do it charge for it.

What you can establish for nothing, in order:

**Is the package in the tree at all, and who pulled it in.**

```bash
npm explain lodash        # prints every dependency path that requires this package
npm ls lodash             # resolved versions, and where each sits in the tree
npm ls --omit=dev lodash  # the same restricted to the runtime tree
```

`npm explain` is the one to reach for: it answers "why is this here" with the full chain and the range each parent declared, which is also exactly what you need for the transitive-fix decision in step 6 of `SKILL.md`. `pnpm why <pkg>` and `yarn why <pkg>` are the equivalents.

**Does your own code import it.**

```bash
rg -n --hidden -g '!node_modules' "require\(['\"]lodash|from ['\"]lodash" .
```

A package nothing imports, in a tree where no dependency imports it either, is a strong not-reachable. Confirm the second half — a transitive package is imported by its parent, not by you, so the absence of a direct import tells you only that *you* do not call it.

**Does the advisory's affected export appear on a path you use.** Read the GHSA entry for the affected function or option; GitHub advisories frequently name it and the OSV record sometimes carries it in an ecosystem-specific field. Then trace from your import, by hand, using the procedure below. This is the step that actually clears findings, and it is the step people skip.

**Is the package used at all in the built output.** For a bundled front end, a package tree-shaken out of the bundle is not shipped. Check the bundle analysis rather than the lockfile — but note this only clears the browser artefact, not the build step, and not any server-side code sharing the lockfile.

Tools worth naming, with what each actually provides:

| Tool | What it gives | Note |
| --- | --- | --- |
| `npm audit` | Advisory matching against the installed tree | No reachability of any kind. `--omit=dev` narrows scope, which is not the same thing |
| `osv-scanner` | Lockfile-driven advisory matching across ecosystems | Call analysis exists for some languages but not JavaScript; check `osv-scanner scan source --help` for the current flag and coverage before claiming it |
| `depcheck`, `knip` | Unused dependencies in your own code | Good first sweep: a package nothing imports is a removal, not an upgrade |
| Semgrep Supply Chain, Snyk, Endor Labs | Advisory-specific reachability rules | Commercial. Say so when you recommend one; the free tiers do not include the reachability feature |
| Socket | Behavioural risk in the package itself — install scripts, network, filesystem | Answers the malicious-package question in step 9, not the CVE question |

## Python

The weakest of the three, and it is better to say that than to imply a call graph exists. Dynamic imports, `getattr` dispatch, entry-point plugin registries and monkey-patching all sever static edges, and there is no widely used open-source symbol-level reachability tool for Python advisories.

```bash
pip install pip-audit
pip-audit                              # audits the active environment
pip-audit -r requirements.txt          # audit a requirements file without installing
pip-audit --desc                       # include advisory descriptions, which name the affected API
pip-audit -f json -o audit.json        # machine-readable
pip-audit --ignore-vuln GHSA-xxxx-xxxx-xxxx   # no expiry field; carry the date yourself
```

Then establish what you can:

```bash
pip install pipdeptree
pipdeptree --reverse --packages urllib3     # which of your packages depend on it
rg -n "^\s*(import|from)\s+jinja2" --glob '!.venv' .
```

The practical ceiling is: who requires it, do we import it directly, and does the advisory's affected API appear in our source. For a transitive package nothing of yours imports, the honest conclusion is "not reachable from our code directly; reachable through `<parent>` if `<parent>` uses the affected API", and then you read the parent's source for that call. That is slower than `govulncheck` and it is still much faster than upgrading blind.

Two Python-specific traps:

- **Extras change the answer.** A vulnerability in a package installed only under an extra you do not request is not in your environment at all. Check the resolved lockfile or `pip freeze`, not `pyproject.toml`.
- **Build-time dependencies are invisible to a runtime audit.** `pip-audit` on the active environment does not see anything from `[build-system] requires` that was used and discarded. Audit the lock or constraints file too if the build environment matters.

## Java and Maven

Between Go and Python in strength. The dependency graph is precise and the class-level analysis is tractable, so tooling does better here than in JavaScript.

```bash
mvn dependency:tree -Dincludes=com.fasterxml.jackson.core:jackson-databind
mvn org.owasp:dependency-check-maven:check
./gradlew dependencyInsight --dependency jackson-databind
```

OWASP Dependency-Check matches by CPE against the National Vulnerability Database and does no reachability analysis; its well-known failure mode is false positives from CPE mismatches, so confirm the coordinates before acting. Where the affected class is named in the advisory, `jdeps` and the dependency tree together will tell you whether anything in your build references it. The Log4Shell-era lesson applies generally: shaded and fat jars hide vulnerable classes from a manifest-based scan, so scan the built artefact as well as the build file.

## Rust

```bash
cargo install cargo-audit
cargo audit                      # advisory matching against Cargo.lock, from RustSec
```

`cargo-audit` is advisory matching only. Reachability for Rust is available through `osv-scanner`'s call analysis, which exists for Rust and Go; confirm the flag name against the version you have installed rather than pasting one from memory, because it moved between major versions.

## The manual call-path trace

When no tool covers the case, this is the procedure, and it takes about ten minutes per finding.

1. **Read the advisory for the affected symbol, not the summary.** "Prototype pollution in the merge function" is the useful sentence; "critical vulnerability in the package" is not. GHSA entries usually name the function, the option, or the input format.
2. **Find where that symbol enters your process.** A direct import, a parent's import, or a plugin registration.
3. **Ask what data reaches it.** The question is not whether the function is called but whether anything an untrusted party controls arrives at it. A parser called only on files your build generates is a very different finding from the same parser behind an upload endpoint.
4. **Check the preconditions in the advisory.** Many require a non-default option, a specific encoding, or a platform. If yours is excluded, that is the strongest exception you can write — and it is still an exception with a date, because defaults change.
5. **Write the conclusion down in one sentence** with the symbol and the path, so the next person does not repeat the trace. That sentence is the `reason` field of the suppression.

## Where reachability analysis is wrong

Named plainly, because a reachability result presented as certainty is worse than no analysis at all.

- **Reflection and dynamic dispatch** hide edges in every language that has them.
- **Configuration-dependent paths** are reachable the day someone flips a flag, and nothing re-runs your analysis when they do.
- **Test and build code** is real code running on real machines with real credentials. A finding "only in tests" is not unreachable, it is reachable from a different place.
- **Vendored and shaded copies** of a vulnerable library carry the vulnerability without appearing in any lockfile. Scanning the built artefact catches these; scanning the manifest does not.
- **Database lag.** Every tool is bounded by the advisory database it reads, and those disagree with each other and with NVD about both existence and severity. See `references/scoring-signals.md`.
- **The transitive parent's own reachability** is a second analysis nobody runs. "We do not call it" is frequently true while the parent does, on your behalf, on every request.

The operational consequence of all of this is the same one: an unreachable finding is deferred to the batch and given a review date. It is never permanently dismissed on the strength of a call graph.

## Recording the result

Whatever you conclude, record it in the form that survives a rotation of the person doing triage:

```text
GHSA-xxxx-xxxx-xxxx / CVE-2025-XXXXX  pkg@1.2.3 (transitive via parent@4.5.6)
Scope:        runtime
Reachable:    no — govulncheck source mode, no affected symbol called (2026-02-14)
Signals:      EPSS 0.004 (p41), not in KEV
Action:       batch with the weekly patch sweep
Review:       n/a, fix available and taken
```

The date on the reachability line is the part that matters. Without it, next quarter's reader cannot tell whether the analysis predates the code that changed.
