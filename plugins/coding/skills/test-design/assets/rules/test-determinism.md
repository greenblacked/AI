---
paths:
  - "**/*_test.go"
  - "**/test_*.py"
  - "**/*_test.py"
  - "**/*.test.ts"
  - "**/*.test.js"
  - "**/*.spec.ts"
  - "**/*Test.java"
  - "**/tests/**"
---

# Test determinism

Loads when a test file is read or edited. A test that depends on the wall clock, an unseeded
random source or a fixed wait passes on the author's machine and fails on a loaded runner,
and a suite that fails for no reason teaches the team to re-run rather than read. The
`test-design` skill holds the reasoning in its determinism reference; this is the short form.

- Inject the clock and pass a fixed instant. Do not assert on `now()`: a test that passes at
  23:59 and fails at 00:00 is the one the team stops trusting.
- Seed random generators explicitly and print the seed in the failure output, so a failure
  from a generated case can be replayed.
- Wait on the condition, not the clock: a latch, a barrier, a completion callback or a poll
  with a deadline. A fixed `sleep` is a race with a longer fuse, and it makes every run
  slower by its whole length.
- Put I/O behind a seam: a real engine on an ephemeral instance for the database, a stub
  server for HTTP, a temporary directory for files. Build state fresh per test; a test that
  failed did not run its cleanup.
- A sleep that is the behaviour under test, such as a backoff delay or a rate limit, is
  allowed. Inject the clock there too, and put `sleep-ok` and the reason on the line so the
  next reader and the hook know it is deliberate.
- Suppressed assertions and surviving mutants are a different question; the
  `mutation-testing` skill owns them.
