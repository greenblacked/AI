# The clean-room protocol

Read this before step 3 of the main workflow. "Clean room" names a specific, well-established
discipline: a person who implements and has never had access to the reference's internals is
what makes independent creation demonstrable, because copying is usually inferred from access
plus similarity, and a clean-room implementer never had the access to infer from. That is a
property of a person, not of how much time passed, so it only exists when there is a second
person to hand the spec to.

Working alone, there is no one without access — you read the reference and you write the
code. Closing the reference and waiting before you implement is still worth doing: it cuts
down the accidental copying that happens when a detail is still on screen while you type. But
it does not show independent creation the way the two-role version does, and it is not a
substitute for it. Treat the solo version as good practice for the ordinary case, and get a
second person onto the two-role split, or legal review, when the stakes are higher: the
reference's own source was read under a licence (gate 4), or the feature is a core
differentiator or a direct competitor's (gate 5).

## On a team: two roles, one document

- **The reader** studies the reference (within the boundaries the other file in this
  directory sets) and writes the behaviour spec from step 1. They do not write any
  implementation code, and once the spec is handed off they stop looking at the reference for
  this feature.
- **The implementer** never opens the reference, the reader's notes beyond the spec itself,
  or any capture of the reference's code or traffic. They work from the spec, and when it is
  ambiguous they ask the reader a question about *behaviour* ("what happens if the input is
  empty") and get a behavioural answer, never "look at line 40."
- The spec is the only thing that crosses the boundary. If the implementer's question cannot
  be answered without the reader going back to the reference, the answer belongs in the spec,
  written down, before the implementer uses it.

## Working alone: a weaker discipline, separated in time rather than by person

Without a second person, this reduces accidental copying; it does not establish independent
creation. Use the two-role version above instead whenever gate 4 or gate 5 is live.

1. Read and observe the reference. Write the spec. Close every tab, file or capture related
   to the reference. Note the date and what you looked at.
2. Leave real time between this and the next step — overnight is enough for most features;
   for anything you are tempted to "just double check" against the reference, treat that
   temptation as a sign the spec is incomplete rather than a reason to reopen it.
3. Implement from the spec alone, with nothing related to the reference open. If a gap
   surfaces, go back to step 1's observation method (use the product again, re-read the
   docs) rather than to anything you captured of its internals, and update the spec before
   continuing.

## What a clean-room log looks like

Keep a short, dated note alongside the spec: what you observed, when, and by which method
(using the product, reading docs, a capture from your own authorised use). This is the same
reasoning as citing a primary source elsewhere: if an IP question comes up later, "I used the
product on this date and wrote this spec from that" is something you can show, and "I don't
remember exactly what I read" is the position this log exists to avoid.

## When the gap cannot be closed from outside

If implementing the spec genuinely requires a detail that using the product, reading its
docs, and your own experimentation cannot surface, that is a sign the feature cannot be
reproduced by observation alone — which is useful information in itself. Reopening the
reference's source at that point to find the missing detail, then implementing with it still
open, is exactly the sequence this protocol exists to prevent; closing the gap with your own
design decision, and noting that you made one, keeps the separation intact.
