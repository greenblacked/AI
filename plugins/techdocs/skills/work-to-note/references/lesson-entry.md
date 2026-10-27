# Lesson-ledger entry

Read this when the work revealed a defect class that will come back: a kind of mistake, not just this instance. A ledger is memory for whoever reviews or writes next; an entry is pruned only when a check makes the mistake impossible.

## The rule

The entry lands in the same change as the fix, not as a follow-up and not written from memory afterwards. A follow-up is the one that never gets written, and an entry paraphrased later loses the specific shape that made it searchable.

## The shape

Four parts, in this order, under a heading that states the class as a sentence:

- **The class.** What kind of mistake this is, named generally enough to recognise in a different file.
- **How it shows up.** The concrete shape it took, specific enough to search for: the command, the setting, the sequence of events.
- **The check that catches it.** The test, validator rule or CI step that now exercises it, with its location. If there is none, say that review has to read for it. The entry doubles as a pointer to where the guarantee actually lives.
- **Where it was first caught.** The change number, and which stage caught it: review, an automated reviewer, or a live run.

A later occurrence adds a short recurrence paragraph rather than a second entry, because the repeat is itself information: the first fix addressed an instance, not the cause.

Where the ledger pairs each entry with a benchmark case, write the smallest real patch that reproduces the defect, and name the entry's heading in the case. An entry with no case is a class somebody is asked to remember and nothing ever checks.

## Not every defect is a lesson

Skip the entry when the mistake is a one-off typo, when a gate already makes it impossible (the entry would be pruned the day it was written), or when it is general good practice with no specific shape. A ledger of everything is read by nobody.

## Worked example

A change set a job to retry on any non-zero exit. During the work, a retry loop re-ran a command that had already half-applied, and the second run duplicated a record. The ledger entry:

```markdown
### A retry re-runs a step that already took effect

**Class.** A retry wrapper treats a failure to confirm as a failure to apply, so
a non-idempotent step runs twice.

**How it shows up.** The worker posted an order, timed out waiting for the reply,
retried, and the service held two orders for one request. The log showed one
timeout and a successful second call, so nothing looked wrong.

**The check that catches it.** `tests/test_retry.py` replays a timeout after a
successful apply and asserts one record. Review also checks every wrapped call for
an idempotency key.

**First caught:** change 412, the review stage.
```

The pattern note that goes with it, if the technique is worth keeping, is a separate file of type `pattern` about idempotency keys; the entry stays short and points at it.
