---
paths:
  - "**/*.rs"
---

# Unsafe code needs a written contract

Loads when a Rust file is read or edited. Every `unsafe` site carries the reasoning a
reviewer needs, because the compiler stops checking inside it.

- Put a `// SAFETY:` comment directly above every `unsafe` block and `unsafe impl`. Say what
  the operation requires, who upholds each requirement, and why it holds at this site.
  "This is fine" restates nothing a reviewer can check.
- Give every `unsafe fn` and `unsafe trait` a `# Safety` section in its doc comment that lists
  what the caller or implementer must guarantee.
- Keep each block to the one operation that needs it, behind a safe function whose signature
  makes the invariant impossible to break. A safe function that can cause undefined behaviour
  is unsound.
- Run the tests that reach the site under Miri, and record the verdict and the run in the
  `unsafe-site-ledger.md` template. Review the sites with the `rust-unsafe-review` skill.
