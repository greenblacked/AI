[RECOMMENDATION] · [Subject] · [YYYY-MM-DD]

**Situation.** [One or two sentences of context the reader already accepts. If they could
argue with it, it is not situation — move it to complication.]

**Complication.** [What changed, with a source. This is the engine of the document; if it
is weak, there is no reason to read on.]

**Question.** [Usually implicit — delete this line unless the reader might frame the
question differently than you do.]

**Recommendation.** [The answer, first, in one sentence: what you propose, what it costs,
and what you need from the reader.]

Reversibility: [Reversible — if wrong we lose [TK: cost] and revert by [TK: date] | One-way
— committed after [TK: milestone].]

**Because:**

1. **[Supporting argument, stated as a conclusion.]** [Two or three sentences of evidence,
   each with a link. Answer-first inside the group as well.]
2. **[Second argument.]** [Evidence with links.]
3. **[Third argument.]** [Evidence with links.]

[Groups should not overlap, and together should cover the case. If two arguments are
really the same argument, merge them — three strong groups beat five overlapping ones.]

**What we rejected:** [Alternative] — [the specific reason]. [Alternative] — [reason].
[Include doing nothing and what it costs.]

**Ask:** [The decision, the person who makes it, and the date it is needed by.]

---

Worked example:

> [RECOMMENDATION] · CI runner capacity · 2026-08-04
>
> **Situation.** All 14 product teams share one CI pool; pipeline health has not been a
> topic in the last three quarterly reviews.
>
> **Complication.** Median queue time went from 3 to 27 minutes since March
> ([CI dashboard]), and two teams have started merging without a green build
> ([INFRA-4471]).
>
> **Recommendation.** Add [TK: n] runners at [TK: monthly cost] for two quarters and
> revisit; this is reversible — the contract is monthly and we can drop back in 30 days.
>
> **Because:**
>
> 1. **The queue is the constraint, not test duration.** Test wall time is flat at
>    [TK: minutes]; queue wait accounts for [TK: %] of pipeline time ([dashboard]).
> 2. **The workaround is the expensive part.** Merging without a green build has already
>    produced [TK: n] rollbacks this quarter ([incident list]).
> 3. **Cheaper than the alternatives we assessed.** Test sharding is [TK: eng-weeks];
>    self-hosted runners add on-call load we cannot staff.
>
> **What we rejected:** Test sharding — right answer eventually, but [TK: eng-weeks] we
> do not have this quarter. Doing nothing — the merge-without-green habit spreads and is
> hard to reverse culturally.
>
> **Ask:** Budget approval from [name] by [date]; runners land within a week of approval.

Notes:

- Every `[TK]` in the example is a real gap the author must fill before sending. Leaving
  them visible is the point — a reader can see exactly what is unevidenced.
- Do not merge this with a status update. If the reader also needs to know where the
  project stands, send that separately in BLUF form.
