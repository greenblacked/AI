---
description: Run mechanical detectors — shrunk test counts, newly silenced checks including bulk lint suppressions, and dependencies that do not exist on their registry — over an agent-written diff against a base ref, then hand the flagged list to code-review for judgement.
argument-hint: '[base ref or PR number, default the default branch]'
allowed-tools: Bash(git:*), Bash(gh:*), Bash(jq:*), Bash(curl:*), Read, Grep, Glob
---

Audit the diff against `$0` — a base ref, or a PR number if it looks like one. This is a
mechanical pass, not a correctness review; that stays with `code-review`.

Resolve the base in prose, never inside a shell expansion. `$0` is replaced with literal
text before this file ever reaches a shell, so `${0:-fallback}` does not do what it looks
like it does: with no argument it exposes the running shell's own `$0` instead of a
fallback, with an argument like `main` it silently discards the argument and expands a
variable literally named `main` instead, and with an argument like `v1.2.0` it fails
outright with "bad substitution". Never put the placeholder inside a `${…}` expansion.

If `$0` was not given — the text above still reads literally `$0`, unsubstituted — the base
is the output of `git symbolic-ref --short refs/remotes/origin/HEAD`, falling back to
`origin/main` if that command fails. Otherwise the base is `$0` exactly as typed.

If that resolved value looks like a PR number, run:

```bash
gh pr diff <number> --patch
```

naming the actual number in place of `<number>`. Otherwise diff directly against the
resolved base — write its actual value into the command, never a shell variable built from
the placeholder:

```bash
git diff "<base>"...HEAD 2>/dev/null
```

Read the actual patch this produces, not a `--stat` summary — every detector below needs
the added and removed lines themselves, and a line count alone shows neither.

If the diff is empty, stop here and say so. An empty diff is not a clean pass on every
detector below; it is nothing to have run them against.

**1. Test tampering.** Count test functions (the language's own marker — `def test_`,
`it(`, `func Test`, `@Test`) before and after in the diff; a shrinking count is flagged
regardless of anything else that changed. Grep added lines under a test-glob path for
`skip(`, `xfail`, `.only(`, `t.Skip(`, `@Disabled`. Flag an assertion or tolerance literal
changed in a test file whose production counterpart did not change in the same diff. Flag
the unit under test newly wrapped in a mock (`mock.patch` or `jest.mock` naming the file
the test is named for). A green run proves nothing here — the tests may be the thing that
changed, which is exactly what this step exists to catch.

**2. Silenced checks.** Grep added lines for `noqa`, `type: ignore`, `@ts-ignore`,
`eslint-disable`, `nolint`, `#[allow(`. Separately, flag a diff touching
`eslint-suppressions.json` or a path passed to `--suppressions-location`, or adding
`--suppress-all` or `--pass-on-unpruned-suppressions` to a lint script or CI step — ESLint's
own bulk-suppression surface, a one-flag way to silence a whole gate rather than one line at
a time. Flag any edit to lint config, a coverage-floor threshold, or a CI workflow file,
named rather than let through unremarked.

**3. Invented or unrequested dependencies.** Check first whether the project points at a
private registry instead of the public default — a `registry=` line in `.npmrc`, an
`index-url` in `pip.conf`, an `index` in `uv.toml`, or a `--index-url` or
`--extra-index-url` line added directly inside `requirements.txt` itself, which overrides
the default for that install regardless of what `pip.conf` says. When one is configured,
report the new dependency as "unverifiable, private registry" rather than querying the
public registry at all; a miss against the wrong registry is not evidence of anything.

This pass queries a public registry for npm (`package.json`) and Python (`requirements.txt`
and `pyproject.toml`'s own dependency tables — `[project.dependencies]`,
`[tool.poetry.dependencies]`, `[tool.pdm.dependencies]`, whichever the project uses) only —
it flags a new `go.mod` or `Cargo.toml` line as added surface in step 4's scope check, but
does not verify it against a registry, since neither Go's module proxy nor crates.io is
queried here; say that plainly rather than imply the same coverage for all four manifests.
For each added npm or Python dependency line, query the public registry with a single
read-only GET of the bare package name, capped so a hanging connection cannot stall the
whole audit — nothing else about the diff leaves this machine — and report the actual
result, never a name that "looks wrong". Read the HTTP status rather than trusting curl's
own exit code, so a 404 (does not exist) is never confused with a DNS failure or a timeout
(unreachable):

```bash
resp=$(mktemp)
status=$(curl -sS -m 10 -o "$resp" -w '%{http_code}' https://registry.npmjs.org/"$pkg" 2>/dev/null) || status="000"
case "$status" in
  000) echo "UNREACHABLE" ;;
  404) echo "NOT FOUND" ;;
  2*)  jq -r '.name // "NOT FOUND"' "$resp" ;;
  *)   echo "UNREACHABLE (HTTP $status)" ;;
esac
rm -f "$resp"
# the same shape against https://pypi.org/pypi/"$pkg"/json for Python, reading .info.name
```

A registry 404 is the highest-severity finding this command raises — a package that does
not exist on the public registry actually in use. `UNREACHABLE` is a network failure, not a
finding; report it as unresolved rather than as a miss. A first-publish date recent
relative to the project's other dependencies is a softer signal, reported alongside it
rather than instead of it. `curl` here only ever targets the registry's own API —
`registry.npmjs.org` or `pypi.org` — never a URL taken from the diff itself.

**4. Scope.** Flag a touched file with no corresponding line in a supplied task brief or
ticket, when one was given as context.

Report a short table, one row per finding — `file:line`, category (test tampering /
silenced check / invented dependency / scope), the one-line evidence — then a single
verdict line: hand the flagged list to `code-review` for the correctness and merge
decision, to `dependency-triage` if a flagged package turns out to be a real compromise
rather than a hallucination, and to `security-review` for anything touching authorisation
or secrets. Fix nothing here; a command that "helpfully" strips a flagged suppression
destroys the evidence this audit exists to surface.

For the full review this mechanises, use the `code-review` skill.
