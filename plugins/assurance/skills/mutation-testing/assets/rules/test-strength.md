---
paths:
  - "**/*_test.go"
  - "**/test_*.py"
  - "**/*_test.py"
  - "**/*.test.ts"
  - "**/*.test.js"
  - "**/*.spec.ts"
  - "**/*Test.java"
  - "**/*Tests.cs"
  - "**/tests/**"
---

# Test strength

Loads when a test file is read or edited. Every assertion you add must be one a wrong
implementation could fail; a test that cannot fail only raises coverage.

- No literal-true assertions such as `assert True` or `expect(true).toBe(true)`. They pass
  against any code, so they prove nothing.
- Do not assert on internal call counts or private methods the caller cannot observe. Assert
  on a return value, a stored record, an emitted event or an exception, so a harmless
  refactor does not break the test.
- Do not suppress a mutant without its reason written beside it. A bare disable comment
  cannot be re-checked later.
- Triage surviving mutants with the `mutation-testing` skill, and record each verdict in
  its survivor ledger template, `survivor-ledger.md`.
