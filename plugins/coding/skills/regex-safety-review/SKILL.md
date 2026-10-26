---
name: regex-safety-review
description: "Review a regular expression that runs on untrusted input for catastrophic backtracking and other denial-of-service shapes. Identify the engine and whether it backtracks, spot nested quantifiers, overlapping alternations and unbounded repetition, measure the worst case with a long non-matching input instead of trusting a small test, and rewrite the pattern as a linear-time expression, an anchored one, or a parser. Use for \"is this regex safe\", \"one request body hangs the service\", \"a regex pinned the CPU at 100 percent\", or a ReDoS advisory in a dependency. Not for authoring a new pattern from scratch (code-scaffold), a broad input-validation review (security-review), a slow query (sql-performance), or a CPU profile of a running service (profiling)."
allowed-tools: Read, Glob, Grep, Edit
---

# Regex safety review

Good looks like a named pattern, the engine it runs on, a worst-case input that demonstrates the
blow-up (or a proof that the pattern is linear), and a replacement that is either safe by
construction or measured to be.

The job is hard because a backtracking regex can be fast on every input you try and then take
exponential time on one crafted string. A test suite with a short input proves nothing: the
failure needs a long, almost-matching string that forces the engine to try every split before
it gives up.

## Scope

Use for: reviewing a regex that runs on user input, a request body, a log line or a filename;
diagnosing a service that hangs on one input; assessing a ReDoS advisory in a dependency; and
choosing between a regex and a parser for a format.

Do not use for: writing a pattern for a known-safe job from scratch, which is `code-scaffold`;
a general review of input validation and injection on a diff, which is `security-review`; a
slow database query, which is `sql-performance`; a CPU profile of a running service whose cause
is not yet a regex, which is `profiling`; or triaging a dependency vulnerability alert in
general, which is `dependency-triage`.

## Hard gates

1. **Identify the engine before judging.** A pattern that is catastrophic in a backtracking
   engine is linear in a DFA engine, and the same pattern moved between runtimes changes class.
2. **Demonstrate, do not assert.** A finding says "this input takes this long", with the input
   and the timing, not "this looks dangerous".
3. **No live denial of service.** Measure in a scratch process with a timeout, never against
   the production service with a real payload.

## Workflow

### 1. Find the pattern and where it runs

Record the literal, the flags (case-insensitive, multiline, dotall), and the call site: is it
anchored, applied to a whole body or a line, run once or in a loop? A pattern run per line over
a large file is a different risk from one run per request.

### 2. Identify the engine

| Runtime | Engine | Backtracks? |
| --- | --- | --- |
| Python `re` | backtracking | yes |
| Java `java.util.regex` | backtracking | yes |
| JavaScript (without `l` flag) | backtracking | yes |
| .NET | backtracking | yes (non-backtracking with `RegexOptions.NonBacktracking`) |
| Perl, PCRE/PCRE2 | backtracking | yes |
| Go `regexp`, RE2 | DFA/NFA hybrid | no — linear time |
| Rust `regex` | finite automata | no — linear time |
| RE2, Hyperscan, `re2` bindings | DFA | no — linear time |

A pattern in Go or Rust `regex` is linear by construction and cannot ReDoS; the review is then
about correctness, not safety. Confirm the engine rather than assuming it from the language.

[Backtracking and ReDoS](references/backtracking-and-redos.md) has the mechanics and the
rewrites.

### 3. Read for the shapes

The dangerous shapes, in order of how often they appear:

1. **Nested quantifiers** — `(a+)+`, `(a*)*`, `(\d+)+`. An inner and an outer quantifier over
   overlapping input gives the engine exponentially many ways to split the same string.
2. **Overlapping alternation under a quantifier** — `(a|a)+`, `(ab|a)+b`. The branches can match
   the same text, so every position has multiple parses.
3. **Adjacent ambiguous repetition** — `a*a*` or `\d+\d+`; the split between the two is
   arbitrary and the engine tries all of them before failing.
4. **Unbounded repetition before a required suffix that never appears** — `(.*)*,` on a long
   line with no comma. The suffix forces the engine to exhaust every split.

A pattern is at risk when two quantifiers or branches can consume the same characters and the
match ultimately fails.

### 4. Measure the worst case

Write the input that almost matches and does not:

```bash
python3 - <<'PY'
import re, time
pat = re.compile(r'(a+)+$')
for n in (16, 20, 24, 28):
    s = 'a' * n + '!'
    t = time.perf_counter()
    try: pat.search(s)
    except Exception: pass
    print(n, round(time.perf_counter() - t, 3))
PY
```

Doubling the input roughly squares (or exponentiates) the time in a backtracking engine; a
linear engine's time doubles. Run it with a hard timeout (`timeout 5 python3 ...`) so a
pathological case does not hang the shell.

### 5. Rewrite

In order of preference:

1. **Drop the regex.** A URL, an email, a date, a JSON field or a log line has a parser or a
   library; a parser is linear and reads the grammar once.
2. **Use a linear engine.** Move the pattern to RE2/Go/Rust `regex`, or a runtime's
   non-backtracking mode, if the language allows.
3. **Remove the ambiguity.** `(a+)+` becomes `a+`; `(ab|a)+b` becomes `(ab|a)*b` with an anchor,
   or `a+b` if the branches are redundant; `a*a*` becomes `a*`.
4. **Anchor and bound.** `^...$` and a length limit (`{1,64}`) reduce the input the engine can
   explore and reject an over-long body before matching.
5. **Atomic groups / possessive quantifiers** (where the engine has them) — `(?>a+)`, `a++` —
   stop the engine from backtracking into a group it has committed to. They are a targeted fix,
   not a substitute for removing the ambiguity.

### 6. Report

Lead with the pattern, the engine and the demonstrated worst case. Give the replacement and why
it is safe (a parser, a linear engine, or the ambiguity removed). Say whether the finding is a
live exposure (the pattern runs on untrusted input) or latent (it runs on trusted input today).

## Anti-patterns

**"It passed our tests, so it is safe."** Tests use short inputs; the blow-up needs a long
near-miss. Measure the failing input, not a passing one.

**Adding a timeout as the fix.** A timeout bounds the damage; the pattern still burns CPU on
every such request and still starves other work. Fix the pattern or move the engine.

**Judging by the pattern's appearance.** `^(a|b)+$` is safe (the branches are disjoint);
`(a|ab)+$` is not. Read the input each branch can consume, not the shape alone.

**Assuming the language implies the engine.** JavaScript backtracks; Go's `regexp` does not;
Python's `re` does but `re2` bindings do not. Confirm the engine the call actually uses.
