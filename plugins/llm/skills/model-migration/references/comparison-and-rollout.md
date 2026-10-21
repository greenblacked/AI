# Comparing and rolling out

Read this at steps 3 to 8, when you are about to run the baseline, diff the candidate
against it, price the change or put it in front of traffic. It covers the method; the
procedure and its order are in `SKILL.md`.

## Contents

- [The baseline](#the-baseline)
- [Porting the prompt](#porting-the-prompt)
- [The case-by-case diff](#the-case-by-case-diff)
- [Cost and latency per request](#cost-and-latency-per-request)
- [Shadow](#shadow)
- [Canary and rollback](#canary-and-rollback)
- [Config and the deprecation date](#config-and-the-deprecation-date)

## The baseline

Run the current model on the feature's eval set before you change anything, because the
baseline is the only thing that makes a candidate score mean something. If the feature has
no eval set, build one first with `agent-evaluation`; a migration without one is a
comparison of two impressions.

Record for every run, one row per case and repeat:

- case id, repeat index, run date and the eval set revision;
- the model id you requested and, where the response reports it, the id that answered;
- a hash of the prompt and the full request parameters, including every field you omitted
  on purpose;
- the raw output, the stop reason and the grader result;
- input tokens, output tokens, cache-write tokens and cache-read tokens from the response
  usage, and latency.

Repeat each case. A model that answers the same case differently on two runs has a noise
floor, and the candidate has to be judged against the baseline's disagreement with
itself, not against a single baseline answer. Cases where the baseline is itself
inconsistent are worth listing separately: they are either unstable prompts or ambiguous
cases, and neither should decide the migration. Where the feature has to be right every
time, report the share of cases that pass on all repeats as well as the mean, as
Anthropic describes for `pass^k` in
<https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents>.

Re-run the baseline on the same day as the candidate for every decision, even when the
provider says a model id is fixed (Anthropic does for the 4.6 generation and later):
serving infrastructure around an unchanged id can still shift observed behaviour, and an
old run would credit that drift to the candidate. Keep earlier runs as history, never as
the comparison. See `references/behaviour-changes.md`, class 10.

A judge model is a dependency on the same schedule as the feature. If an LLM judge scores
your outputs and it runs on the model being retired, the migration changes the
instrument as well as the subject. Pin the judge and rubric version, keep them fixed
across baseline and candidate, and re-check judge agreement with human labels before
trusting it when you eventually have to move it.

## Porting the prompt

Port in two steps, never one.

1. **Mechanical port.** Change only what the provider requires for the request to be
   accepted and to mean the same thing: the model id, rejected parameters, replaced
   settings, response parsing. Leave the prompt text alone. Run the eval set. This isolates
   what the model did from what you changed.
2. **Prompt changes.** For each regression the mechanical port exposes, form a hypothesis
   (the new model reads this instruction more literally, the format example is now
   ignored, the tool is no longer called when it was forced), change that one thing, and
   re-run. Keep a one-line changelog of prompt edits with the case that motivated each.

Tune on a development split and decide on cases you did not tune on. A prompt edited until
every visible case passes has learned those cases. `agent-evaluation` covers the split and
the sealed holdout.

Settings that replace old ones, such as an effort level in place of a thinking budget, are
part of the port and need their own sweep over two or three values; the best value on one
model is not the best on the next.

## The case-by-case diff

An aggregate score can rise while a case that matters flips from right to wrong, so the
decision is made on the per-case table.

Join baseline and candidate on case id. For each case compare the pass rate across its
repeats and put it in one bucket:

| Bucket | Meaning | What to do |
| --- | --- | --- |
| Regressed | Passed under the baseline, fails under the candidate beyond the baseline's own noise | Read the transcript; fix, accept with a recorded reason, or block |
| Improved | The reverse | Sample a few; confirm the grader is not rewarding something else |
| Unchanged | Same result, pass or fail | Nothing, except cases that fail on both: note them |
| Within noise | Differs by no more than the baseline differed from itself | Do not count as a change either way |

Then:

- **Read the transcripts of every regressed case.** The output tells you whether the model
  failed or your grader rejected a valid answer in a new format. This is the step teams
  skip, and Anthropic's note on evals is blunt about it: "Read the transcripts!"
  (<https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents>).
- **Slice.** Report by task family, input length, language and risk tag, so a collapse in
  one slice does not average away.
- **Compare distributions, not only correctness.** Output length, refusal rate, schema
  violation rate and stop-reason mix often move before any grader notices.
- **Decide the gate before you look.** Write down which slices may not regress, what
  aggregate change is not worth the migration and which regressions block, then apply it.
  A paired test on the discordant cases (a sign test or McNemar's test) tells you whether
  a small set of flips is distinguishable from noise; with few cases the honest answer is
  often "cannot tell", and the response is more cases, not a looser gate.

## Cost and latency per request

Compare cost per request on the replay set, from the usage the provider returned, not from
the ratio of two list prices. Three things move it independently of price:

- **Tokens for the same text.** A different tokenizer changes the count; the Sonnet 5.5
  migration guide reports that it shares Claude Sonnet 5's tokenizer and that the same text
  produces about 30% more tokens than on Claude Sonnet 4.6, Claude Sonnet 4.5 and Claude
  Haiku 4.5. Recount on the target model.
- **Output tokens you did not write.** Thinking is billed as output tokens, and a changed
  default or effort level changes how many.
- **Cache behaviour.** Per request, cost is uncached input, plus cache writes, plus cache
  reads, plus output, each at the target's own rate. The cache-read rate, the write
  premium and the minimum cacheable length can all differ between models, and a prompt
  that falls below the new minimum is not cached and raises no error
  (<https://platform.claude.com/docs/en/build-with-claude/prompt-caching>). Replay the
  requests in production order and at production spacing, because hits depend on how soon
  the next request arrives; a shuffled replay measures a cache that production never has.
  Read the usage fields on the first requests after a switch and expect them to be writes.

Get the current prices from the provider's pricing page on the day you compare, and say
which date in the record. For designing the cache itself, or for deciding where a cheaper
model belongs, hand off to `llm-cost`.

Measure latency as time to first token and total time at p50 and p95 under the same
concurrency for both models. Extra thinking can raise the second without moving the first.

## Shadow

Shadow traffic sends a copy of real requests to the candidate and discards its output. It
finds what the eval set did not contain, which is real inputs.

- Make the copy side-effect free. A shadowed agent must not send the email or write the
  row; stub or read-only its tools, or replay only the model call.
- Hold the same data-handling rules as the live call. The candidate sees the same user
  content.
- Budget for it: the shadowed share of traffic costs the candidate's price on top of the
  live call.
- Grade what you can without a reference: schema validity, refusal, length, stop reason,
  tool-call arguments, plus a calibrated judge on a sample. Compare against the live
  response on the same request.
- Run it across a full traffic cycle so rare request types appear. `release-strategy`
  covers bake times.

Promote from shadow only on the numbers you wrote down before it started.

## Canary and rollback

`release-strategy` owns the mechanics of rings, percentages and promotion. These are the
parts that are specific to a model swap.

- **Assign by conversation, session or user, not by request.** Reasoning state and context
  can be tied to the model that produced them, so a conversation that flips models
  mid-way can lose state without an error
  (`references/behaviour-changes.md`, class 5). Decide up front whether conversations in
  flight at cutover finish on the old model.
- **Write the rollback trigger as numbers.** Name each signal, its threshold and its
  window: error rate on the new request shape, schema-violation rate, refusal rate, p95
  latency, cost per request, user retry or edit rate, sampled judge score. Thresholds come
  from the baseline's noise and the business tolerance, agreed before the canary; this
  skill does not supply them. The trigger fires the rollback itself, without a person
  deciding at 3 a.m. whether it is really bad.
- **Make the rollback possible.** The migration changed the request shape (parameters
  removed, a thinking setting added), so the old model may not accept the new shape and
  the new may not accept the old. Keep a request profile per model id and select it with
  the model id, so flipping the id flips the whole request. Test the flip in staging before
  the first canary percentage.
- **Watch cost as a rollback signal.** A model that is right and four times the price per
  request is a regression of a different kind.

## Config and the deprecation date

- **Model id and request profile live in configuration, in one place.** No model id string
  in code paths, prompts' metadata or notebooks. Use a pinned id rather than an alias
  where the provider offers one.
- **Keep the old id until its retirement date.** It is your rollback. Anthropic states
  that requests to a model past its retirement date fail and gives at least 60 days'
  notice for publicly released models
  (<https://platform.claude.com/docs/en/about-claude/model-deprecations>), so after that
  date rollback is no longer a model change; the fallback is a flag that turns the feature
  off or degrades it. Retirement dates on that page can be marked tentative or "not sooner
  than", so recheck the page rather than copying a date once.
- **Finish early.** Set the cutover date with enough margin before retirement that a failed
  canary leaves time to fix and retry.
- **Find every use.** The same page describes exporting usage by API key and model from the
  console; run the equivalent before you declare the old id gone, and search code and
  config for the id string, since a forgotten batch job fails on the retirement date.
- **Remove the old id and its request profile after retirement**, and delete the calendar
  entry with them. A dated follow-up in the decision record makes this happen.
