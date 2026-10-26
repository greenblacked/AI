# Backtracking and ReDoS

Read this when the pattern is dangerous and you need the mechanics, the shapes with the input
that triggers each, or the rewrite that removes the ambiguity.

## How backtracking blows up

A backtracking engine walks the pattern left to right and, at each choice point — a quantifier
that can stop early, an alternation — it picks one and remembers the alternatives. When the
rest of the pattern fails, it returns to the last choice point and tries the next option. On a
pattern with two overlapping choices per character, the number of paths to explore is
exponential in the input length: 2^n, where n is the count of characters that can go either
way. That is why a 30-character string can take minutes and a 40-character string can take
longer than the age of the universe.

A DFA engine has no choice points to revisit: it reads each character once and the state
machine is fixed, so its time is linear in the input regardless of the pattern. This is the
whole difference between `regex`/RE2/Go and `re`/`java.util.regex`/PCRE.

## The shapes, with the trigger

| Shape | Example | Trigger input |
| --- | --- | --- |
| Nested quantifier | `(a+)+$` | `'a'*n + '!'` |
| Nested quantifier, digits | `(\d+)+$` | `'1'*n + 'x'` |
| Overlapping alternation | `(a\|a)+$`, `(ab\|a)+b` | `'a'*n` |
| Adjacent ambiguous repeats | `a*a*$` | `'a'*n + '!'` |
| Repetition then required suffix | `(.*)*,` | a long line with no comma |
| Nested groups | `((a)*)*$` | `'a'*n + '!'` |
| Ambiguous alternation in a loop | `(x+x+)+y` | `'x'*n` |

The common thread: at least two ways to partition the same characters, and a required suffix
that ultimately fails, forcing the engine to try every partition.

## Safe-looking patterns that are not

- `^(\w+\s?)*$` — the `\s?` overlaps `\w` on nothing and the outer `*` nests over `+`.
- `([a-zA-Z]+)*` — an inner `+` under an outer `*`; on a long non-letter run the splits explode.
- `^(([a-z])+.)+[A-Z]([a-z])+$` — a class-name validator and a widely used evil-regex example; a long lowercase run with no
  capital is exponential.
- `(.*),(.*),(.*)` applied to a line with no commas — each `.*` tries every split of every
  prefix.

## Measuring, safely

Always bound the measurement so a pathological case cannot take the machine down:

```bash
timeout 5 python3 - <<'PY'
import re, time, signal
signal.alarm(5)  # belt and braces on top of the shell timeout
pat = re.compile(r'(a+)+$')
for n in (18, 20, 22, 24, 26):
    s = 'a' * n + '!'
    t = time.perf_counter(); pat.search(s)
    print(n, f"{time.perf_counter()-t:.4f}s")
PY
```

Doubling the input roughly quadruples the time when the blow-up is quadratic and squares the
exponent when it is exponential; a linear engine's time simply doubles. The growth rate, not
the absolute time, is the evidence.

## The rewrites

**Remove the ambiguity.**

| Dangerous | Safe | Why |
| --- | --- | --- |
| `(a+)+` | `a+` | The outer quantifier is redundant; `a+` matches the same language |
| `(\d+)+` | `\d+` | same |
| `(a\|a)+` | `a+` | The branches are identical |
| `(ab\|a)+b` | `(ab\|a)*b` or `a+b` | Make the alternation's branches disjoint, or drop the redundant one |
| `a*a*` | `a*` | Two adjacent identical quantifiers are one |
| `(.*)*` | `.*` | same |
| `(x+x+)+y` | `x+y` | The inner pattern is just `x+` |

**Make the branches disjoint.** `(a|ab)` becomes `a(b)?`; each character is now consumed by one
branch, so there is one parse.

**Anchor and bound.** Add `^` and `$` so a failed match ends early, and a length limit
(`{1,64}`) so the engine never sees a megabyte. Reject the over-long input before the regex.

**Use a linear engine.** In Go and Rust the standard `regex` package is linear; in Python, the
`re2` bindings replace `re`; in the managed regex library (`System.Text.RegularExpressions`) in runtime version 7 and later, `RegexOptions.NonBacktracking` (with the caveat that it
rejects some constructs, like lookbehind and backreferences, which it cannot do linearly).

**Atomic groups and possessive quantifiers.** `(?>a+)` and `a++` (PCRE, Java, the managed regex library, Perl, not
JavaScript or Python's `re`) tell the engine not to backtrack into a group once matched. They
convert an exponential pattern to a linear one when the group is truly unambiguous — but they
change the language the pattern matches in edge cases, so verify the matches did not change.

## When a parser is the answer

An email address, a URL, an ISO date, a JSON document, a log line, a CSV row and a semver string
all have a defined grammar. A parser or a library reads it once, linearly, and reports where it
failed. Reach for the regex only when the input is genuinely a regular language and the pattern
is provably linear — a fixed set of literals, a bounded repetition, a simple character class.
