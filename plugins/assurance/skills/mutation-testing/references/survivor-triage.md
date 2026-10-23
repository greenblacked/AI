# Survivor triage

How to reach a verdict on a surviving mutant quickly and defensibly, with worked survivors
for the mutators that produce most of them. Read it at step 4 when a verdict is not
obvious, and at step 5 when choosing the test that kills a real survivor.

## Contents

- [The three questions](#the-three-questions)
- [Worked survivors](#worked-survivors)
- [Equivalent-mutant patterns that recur](#equivalent-mutant-patterns-that-recur)
- [Writing the killing test](#writing-the-killing-test)
- [The survivor ledger](#the-survivor-ledger)

## The three questions

A test detects a fault only when three things happen in sequence. Ask them in order and stop
at the first "no":

1. **Reach.** Does any test execute the mutated line? If not, the verdict is an untested
   branch, whatever the tool's status says.
2. **Infect.** For some input that reaches it, does the mutated expression produce a
   different value or take a different branch from the original? If no input can, the
   mutant is equivalent.
3. **Propagate.** Does that different value reach something a caller can observe — a return
   value, a persisted row, a message sent, an exception raised, a file written? If it is
   always overwritten, discarded or normalised away before it leaves the unit, the mutant is
   equivalent from the outside. If it does reach an observable and no test checks it, the
   verdict is a missing assertion.

Write the input that answers question 2 down. It is the first half of the killing test.

## Worked survivors

| Mutation | Why it survived | Verdict | Test that kills it |
| --- | --- | --- | --- |
| `if amount > limit: reject()` became `>=` | Tests use amounts well below and well above the limit, never equal to it | Missing assertion at the boundary | `amount == limit` is accepted, and `limit + 0.01` (or `+ 1`) is rejected |
| `if not user.is_admin: raise Forbidden` had its condition negated | The only test uses an admin and asserts the response body, so the negated check raises for nobody it tries | Missing assertion: the denial path is never asserted | A non-admin call raises `Forbidden` and changes nothing in storage |
| `audit.record(event)` was removed | Tests assert the operation's return value; nothing reads the audit store | Missing assertion on a side effect | After the operation, a fake audit store holds exactly one entry with the actor, action and target |
| `return total` became `return 0` | The test calls the function for its side effect and ignores the result | Missing assertion | Assert the returned total for an input whose total is not zero |
| `cache.invalidate(key)` was removed | Tests never read after a write, so stale data is never observed | Missing assertion | Write, read, update, read again: the second read returns the updated value |
| The `except TimeoutError:` handler body was replaced | No test makes the dependency time out; the status is no coverage | Untested branch | Inject a client that raises `TimeoutError` and assert the retry count and the error the caller receives |
| `name.strip()` became `name` | The value was already stripped by the caller's validation layer | Redundant code, not a weak test | Delete the second `strip()`; note it in the hand-back |
| `"Invoice not found"` became `""` | No test reads the message | Usually accept or suppress; a missing assertion only if a client matches on the text | If the message or an error code is a contract, assert it; otherwise leave it to a log-string exclusion |
| `retries = 3` became `retries = 4` | Tests stub the dependency to succeed first time | Missing assertion if the retry budget is a documented behaviour; otherwise accept | Fail the dependency every time and assert exactly three attempts |

## Equivalent-mutant patterns that recur

- **Loop bounds that agree.** `i < n` and `i != n` for an index that starts at or below `n`
  and steps by one.
- **Ties that cannot be distinguished.** `max` written as `a if a > b else b`, mutated to
  `>=`: when `a == b` both branches return the same value.
- **Internal sizing.** A buffer size, a cache capacity or a batch size changed by one, when
  the only effect is performance and no test (rightly) asserts on it. Treat as equivalent for
  a functional suite; if the size is a documented limit, it is a missing assertion instead.
- **Overwritten values.** A default that every caller overrides, or a local that is
  reassigned before it is read.
- **Defensive checks the type system already guarantees.** A `None` check on a value that
  cannot be `None` on any reachable path. Consider deleting the check rather than suppressing
  the mutant.
- **Idempotent calls repeated.** Removing one of two calls to an idempotent operation.

Suppress each with the reason written where the next reader will see it, naming the mutator
rather than disabling all mutation on the line.

## Writing the killing test

- Start from the input you found at question 2, and assert on the observable you found at
  question 3. That pair is the whole test.
- Assert on the outcome, not the mechanism. A spy or fake is right when the side effect is
  the behaviour (an audit entry, an outgoing message); asserting that an internal helper was
  called is not.
- Name the test for the behaviour, not the mutant: `accepts_an_amount_equal_to_the_limit`,
  not `kills_mutant_412`. Mutant identifiers change between runs; the behaviour does not.
- Re-run the tool on that file alone and confirm the mutant is now killed. A test that passes
  but leaves the mutant alive is checking something else.
- When one test kills several survivors at once, that is expected; boundary tests often kill
  the `<`, `<=` and negation mutants on the same line together.

## The survivor ledger

Keep the triage in the pull request or beside the code, one row per survivor on a changed
line, so the gate can check that every survivor has a verdict and a reviewer can check the
verdicts:

```markdown
| Location | Mutator | Verdict | Action | Owner |
| --- | --- | --- | --- | --- |
| src/billing/limits.py:42 | `>` to `>=` | Missing assertion | Added `accepts_an_amount_equal_to_the_limit` | author |
| src/billing/limits.py:57 | `i < n` to `i != n` | Equivalent | Suppressed with reason on line 56 | author |
| src/billing/export.py:88 | String literal | Accepted | Log message only | author |
```

An "accepted" row is a decision, not a deferral: it says the fault would not matter if it
shipped. If it would matter and there is no time to write the test now, it is not accepted —
it is open, and it belongs in the backlog with an owner and a date.
