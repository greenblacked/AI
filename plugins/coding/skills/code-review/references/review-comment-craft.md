# Review comment craft

How to write findings people act on, what to do when a review turns contentious, and how
to review code a model wrote. Read this before writing up a review carrying several
blocking findings or one you expect to be argued with.

## Contents

- [Worked examples by severity](#worked-examples-by-severity)
- [Phrasings that provoke a defence](#phrasings-that-provoke-a-defence)
- [When you are not sure](#when-you-are-not-sure)
- [Disagreement, and how to end it](#disagreement-and-how-to-end-it)
- [Reviewing generated code](#reviewing-generated-code)
- [Receiving a review](#receiving-a-review)

## Worked examples by severity

**Blocking.** Name the input or sequence that makes it fail.

> Weak: "This isn't safe with concurrent requests."
>
> Strong: "blocking — `checkout.py:88`. `balance = read(); if balance >= amount: write(balance - amount)`. Two checkouts for the same account that both read 100 will both pass the check and both write 20, so a 160 spend succeeds against a 100 balance. Needs a conditional update (`UPDATE … WHERE balance >= :amount`) or a row lock; a re-read before the write does not close the window."

**Should-fix.** Name the cost and who pays it.

> Weak: "Please add a test."
>
> Strong: "should-fix — there is no test that fails if this change is reverted. The retry behaviour in `client.go:140` is the whole point of the change and nothing exercises it, so the next refactor removes it silently. A test with a stub failing twice then succeeding covers it."

**Consider.** State what the alternative buys, and accept a no.

> Weak: "Would be cleaner as a map."
>
> Strong: "consider — this if-chain over six statuses will need editing every time a status is added, and the compiler will not tell you when one is missed. A map from status to handler makes the missing case a key error at startup. Fine to leave if statuses are stable."

**Nit.** One line, prefixed, droppable.

> "nit: `usr` reads as a typo for `user` here."

**A question with a consequence attached.**

> Weak: "Is this inside the transaction?"
>
> Strong: "question — I cannot tell from the diff whether `applyCredit` at line 92 runs inside the transaction opened at line 71. If it does not, a failure at line 96 leaves the credit applied and the order unpaid, which is a blocking issue; if it does, this is fine."

## Phrasings that provoke a defence

| Avoid | Because | Use instead |
| --- | --- | --- |
| "Why didn't you just …" | Carries an assumption that the author did not think, and the answer is usually a constraint you cannot see. | "What made this preferable to X? X would avoid the extra round trip." |
| "This is wrong." | Leaves the author with nothing to act on and a reason to argue. | "This returns the wrong total when `items` is empty: `sum` starts at 1 on line 30." |
| "Nit: …" attached to nine lines | Turns one preference into the impression of the review and buries the blocking finding. | Say it once at the first occurrence and note that it recurs. |
| "I would have written this differently." | Invites a redesign after the work is done and stalls the change for a week. | Either a blocking finding with a named failure, or nothing. |
| "Needs more tests." | Unactionable; the author cannot tell when they are done. | Name the behaviour that needs a test and what it should assert. |

Two more habits that change how a review reads. Note what is good, once and specifically
— "the idempotency key on the webhook handler is the right call" — because it tells the
author which of their decisions was legible and costs one line. And review the change in
front of you against the codebase as it is, not against the codebase you wish existed;
raising the pre-existing pattern as a finding on the person who happened to touch the file
is how reviews become punitive.

## When you are not sure

Uncertainty is fine and hiding it is not. Say which of the three you are in:

- **Unverified but consequential.** Raise it as a blocking finding labelled unverified,
  with what would settle it: "if `resp` can be nil on the 204 path, this panics. I could
  not tell from the client library — can you confirm?"
- **A gap in your knowledge of the domain.** Ask, and say so. A reviewer who admits the
  gap gets a real answer; one who guesses gets a polite correction and stops being read.
- **A feeling that something is off with no finding behind it.** Either spend ten more
  minutes and produce the finding, or drop it. "This feels fragile" is not reviewable.

## Disagreement, and how to end it

A review thread that has gone three rounds is not going to be settled by a fourth. Move
it: a call, a pairing session, or a decision from whoever owns the code. Threads of nine
comments cost more than the defect almost always.

When you and the author disagree on a blocking finding, separate the two questions —
whether the failure you describe can happen, and whether it matters. The first is
factual and can be settled with a test; write the test. The second is a judgement about
risk and belongs to the owner of the service, not to the reviewer.

If you were wrong, say so plainly in the thread. It costs one line and it is what makes
your next blocking finding believable.

## Reviewing generated code

Treat the source as a prior on where to look rather than as a reason to review
differently. Sonar's 2026 survey reports 96% of developers do not fully trust the
functional accuracy of generated code and that the work has shifted from creation to
verification; Stack Overflow's 2025 survey reports 66% naming "almost right, but not quite" as a
frustration and 45% naming debugging it as more time-consuming. That near-miss shape has
specific tells:

- **Plausible API usage that does not exist** in the version you depend on, or that
  exists with different semantics. Check the signature against the installed version
  rather than against memory.
- **Error handling that is present and shallow.** A `try` around everything with a log
  and a default return reads as diligence and swallows the failure.
- **Tests that assert the implementation.** Generated tests frequently mirror the code
  they were generated alongside, so they pass by construction and fail to pin behaviour.
  Ask whether each test would fail if the change were reverted.
- **Defaults invented to fill a gap** — a timeout, a page size, a retry count with no
  stated source. Each is a decision that nobody made.
- **Code that handles a case the system does not have**, which is dead weight, and
  missing the case it does have, which is the defect.
- **Confident comments describing behaviour the code does not implement.** Read the code,
  not the comment, and raise the mismatch as a finding either way.

The author is accountable for the change regardless of how it was produced. Address
findings to the change, not to the tool.

## Receiving a review

- Answer every finding, including the ones you decline, with a reason. Silence reads as
  disagreement and the thread stays open.
- Fix the finding rather than the instance of it when the reviewer found one of five.
- Push back on severity when you think it is wrong, and say why: "this is a consider for
  me, not should-fix, because the path is admin-only and behind a feature flag."
- A review that misunderstood the change is usually a signal the description was thin.
  Fix the description; the next reviewer has the same problem.
