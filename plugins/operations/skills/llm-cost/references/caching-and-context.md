# Caching and context

Read this before designing a prompt cache or a truncation rule, or when caching is
enabled and the bill has not moved. Cache mechanics, lifetimes and minimum lengths are
provider-specific and change between versions: look up the current numbers in the
vendor's documentation and record the date you did. What is below is the design and the
diagnosis, which do not change with the price list.

## Contents

- [How a prompt cache actually matches](#how-a-prompt-cache-actually-matches)
- [Ordering the prompt by volatility](#ordering-the-prompt-by-volatility)
- [Placing breakpoints](#placing-breakpoints)
- [The invalidation checklist](#the-invalidation-checklist)
- [Proving a cache is paying](#proving-a-cache-is-paying)
- [When caching does not pay](#when-caching-does-not-pay)
- [Retrieval instead of stuffing](#retrieval-instead-of-stuffing)
- [Conversation history](#conversation-history)
- [Truncation that keeps the deciding content](#truncation-that-keeps-the-deciding-content)
- [Tool schemas](#tool-schemas)

## How a prompt cache actually matches

A prompt cache stores the model's internal state after processing a prefix of the prompt
and reuses it on a later request whose prompt begins with exactly the same content. Five
properties follow, and almost every caching failure is one of them.

It is a **prefix** match, from the first byte. A cache never helps with content that sits
in the middle of a prompt, after something variable.

It is an **exact** match on the serialised request as the provider sees it, which includes
things you may not think of as prompt: the system block, tool definitions, and often the
model identifier and some parameters. Equal-looking JSON serialised in a different key
order is a different prefix, and several languages do not guarantee key order at all.

It matches over a **hierarchy of levels** — tool definitions, then the system block, then
messages — and a change at any level invalidates that level and every level after it.
Editing one word of one tool description therefore invalidates the entire cache for that
path, while a message-level change such as attaching an image or altering a message-level
parameter invalidates only the message blocks. Check the exact hierarchy in the provider's
documentation; the shape is what matters here.

It has a **minimum cacheable prefix length that differs per model**, and the values are not
ordered by model tier, price or size, so the threshold cannot be inferred from anything
you already know — published minimums have spanned several hundred to a few thousand
tokens. Below the threshold the cache marker is ignored and no error is returned. Do not
carry the widely repeated "cache anything over a couple of thousand tokens" rule; look up
the number for the model you call.

It has a **lifetime**, usually short, usually refreshed by a hit, and commonly measured
from the *start* of the request that writes the entry rather than from the end of its
response — so a slow generation eats part of its own window. Some providers offer a
longer-lived tier at a higher write premium, which changes the break-even in
`token-accounting.md` and nothing else. There is also a bound on how far back the matcher
looks for a match, counted in content blocks, so a conversation that keeps growing
silently stops matching with no error at all.

## Ordering the prompt by volatility

Arrange every prompt most-stable-first. The boundary between stable and volatile is where
the cache ends, so the goal is to push that boundary as late as possible.

| Position | Content | Changes |
| --- | --- | --- |
| 1 | System instructions, role, output contract | Per release |
| 2 | Tool definitions | Per release |
| 3 | Static corpus: policy documents, schemas, style guides, long few-shot sets | Per release |
| 4 | Per-tenant static context | Per tenant |
| 5 | Retrieved chunks for this request | Per request |
| 6 | Conversation history | Per turn |
| 7 | The current user message | Per request |

Two reorderings pay for themselves immediately. Move any "today is `2026-09-15`" line out
of the system prompt and into the final user message, or pass the date as a tool result
instead — it is one line that invalidates everything. And put per-tenant context after
everything global rather than at the top: a per-tenant prefix is a cache per tenant, so
the hit rate falls by roughly the number of tenants sharing that path.

## Placing breakpoints

Where the provider requires explicit cache breakpoints, place them at the end of stable
regions, not at the end of the prompt:

- One after the tool definitions, which covers the whole preamble for every path sharing
  it.
- One after the static corpus.
- One after per-tenant context, when there are enough calls per tenant within the
  lifetime to earn the write.

A breakpoint after volatile content writes a new cache entry on every call and pays the
write premium for nothing. If the vendor caps the number of breakpoints, spend them on
the largest stable blocks.

## The invalidation checklist

Walk this list against a real serialised request, not against the template:

- [ ] No timestamp, date, request id, trace id or random value anywhere before the last
      breakpoint.
- [ ] No per-user or per-tenant text before the global blocks.
- [ ] Tool definitions serialised from an ordered structure, with stable key order and
      stable float and whitespace formatting.
- [ ] Any JSON embedded in the prompt serialised with sorted keys.
- [ ] Retrieved chunks placed after all static content, and in a deterministic order for
      a given query.
- [ ] Few-shot examples not shuffled per request.
- [ ] The model identifier fixed to a dated version rather than a moving alias.
- [ ] Sampling parameters and system-level flags constant across calls on this path.
- [ ] The stable prefix longer than this model's minimum cacheable length, looked up
      rather than assumed.
- [ ] The conversation short enough to stay inside the matcher's lookback bound on
      content blocks; if it grows past that, summarise rather than accumulate.
- [ ] No tool description edited as a routine matter — a one-word change at the tools
      level invalidates every level after it.
- [ ] No A/B experiment or feature flag rewriting the preamble per request; if one does,
      each arm needs its own stable prefix and its own traffic share to earn a cache.

The one that hides longest is a serialisation difference, because the prompt is identical
when printed and different in bytes. When the checklist passes and hits still do not
appear, diff the raw request bodies of two consecutive calls byte for byte.

## Proving a cache is paying

The question is not whether the cache is hit. It is whether reads per write clears the
break-even, because a write costs more than an uncached call.

```bash
set -Eeuo pipefail

# One path, one hour. reads_per_write is the number; compare it against the break-even
# computed from today's multipliers.
jq -rs --arg path "support.triage.classify" '
  map(select(.prompt_path == $path))
  | {calls: length,
     write: (map(.cache_write_tokens // 0) | add),
     read:  (map(.cache_read_tokens  // 0) | add),
     plain: (map(.input_tokens) | add)}
  | . + {reads_per_write: (if .write > 0 then (.read / .write) else null end)}' calls.jsonl
```

Read it as follows:

| Pattern | Meaning |
| --- | --- |
| `reads_per_write` comfortably above the break-even | Working, and worth the write premium |
| `reads_per_write` near zero, `write` tracking calls | Paying the premium on every call and never reading. Either the prefix is unstable — run the checklist — or the traffic arrives further apart than the lifetime, in which case turn caching off on this path |
| `reads_per_write` positive but below the break-even | Caching is enabled and losing money. Consolidate traffic onto fewer prefixes, or stop |
| Both zero, `plain` large | Caching is not enabled here, or the prefix is below the model's minimum cacheable length and the marker is being ignored silently |
| `read` present but `plain` still large | Only part of the preamble is covered; the breakpoint is too early |

Do this per prompt path and per tenant. An aggregate averages a warm path against a cold
one and reports a figure that describes neither — and a vendor or dashboard "hit rate",
which usually counts calls with caching enabled or prompt tokens covered by a marker, can
read near 100% while reads per write is zero.

## When caching does not pay

Enabling it is not free, so each of these is a reason to leave it off rather than a reason
to tune it:

- **Low call rate per distinct prefix.** Reuse has to fall inside the lifetime. Compute
  inter-arrival time per prefix from the log before enabling anything; traffic spread
  further apart than the lifetime writes an entry every call and reads none.
- **High prefix cardinality.** Per-user preambles mean one cache per user; unless each
  user is active enough within the window, every call pays the write premium.
- **A short preamble.** Below the model's minimum cacheable length nothing is cached and
  nothing tells you so.
- **A prompt that is mostly the user's input anyway.** There is little stable prefix to
  cache, and the effort belongs in output control instead.
- **A preamble under active editing.** During a week of prompt iteration each change
  invalidates the cache; the write premium is being paid for a prefix nobody reuses.

In each case the evidence is the same: reads per write below the break-even. Turning
caching off is a legitimate outcome of this analysis and it is the one nobody writes
down.

## Retrieval instead of stuffing

Stuffing a corpus into every prompt pays to re-read it on every request. Retrieval pays a
retrieval cost once and sends only what decides the answer.

- Tune `k` against measured answer quality, not intuition. Plot accuracy against `k` on
  an eval set: it usually flattens well before the `k` in production, and token cost is
  linear in `k` the whole way.
- Rerank a wider candidate set down to a small final set. Reranking is cheap relative to
  generation and is the usual way to cut `k` without losing recall.
- Trim chunks to the passage that matched rather than sending the whole document that
  contained it.
- Deduplicate. Overlapping chunks from the same source are common and pure waste.
- Cache the retrieval results themselves for repeated queries; identical questions arrive
  far more often than people expect.
- Check the empty case: when retrieval returns nothing relevant, sending the top `k`
  irrelevant chunks costs tokens and degrades the answer. A threshold that sends nothing,
  and a prompt that handles that, is cheaper and better.

## Conversation history

History resent in full every turn grows the session's total cost with the square of the
turn count. Three controls, in order of preference:

1. **Summarise on a threshold.** Past a token budget, roll the oldest turns into a
   summary and keep the last few verbatim. The summary is generated once and then
   becomes stable prefix, so it caches.
2. **Drop tool output first.** Large tool results are usually the bulk of the history and
   the least useful to carry forward; replace them with a one-line result and a handle.
3. **Start a new session on a topic change.** Cheaper and usually better than carrying an
   unrelated hundred turns, and it is a product decision as much as a cost one.

Whichever you use, make the point of truncation deterministic. A boundary that depends on
a fuzzy signal produces sessions that behave differently for no reason a user can see.

## Truncation that keeps the deciding content

When something has to be cut, the ranking is by what determines the answer, not by
position in the buffer:

| Keep | Cut first |
| --- | --- |
| The instruction and the output contract | The middle of long documents |
| The user's current question | Older tool outputs, already summarised |
| Retrieved evidence that matched the query | Few-shot examples beyond the first few |
| The last few conversation turns | Boilerplate headers, navigation, licence blocks |
| Anything the output must quote verbatim | Repeated or overlapping chunks |

Two rules on top of the ranking. Cut the middle of a long document before the head or the
tail: recall over a long context is weakest in the middle at most models, so those tokens
are the ones paying least — but measure it on your own data and model before relying on
it, because the size of the effect varies and it is the kind of claim that goes stale.
And mark every elision in the text, so the model can say the document was truncated
rather than answering confidently from the half it received. A silent truncation is a
correctness bug that presents as a cost optimisation.

## Tool schemas

Tool definitions are input tokens on every call in a loop, and they are the context cost
people forget because they are configuration rather than content.

- Give each step only the tools it can use. A planning step rarely needs the same set as
  an execution step.
- Keep descriptions to what disambiguates the tool from its neighbours; a paragraph per
  tool, multiplied by twenty tools and twelve steps, is a real number.
- Trim parameter schemas to the fields the model sets. Generated schemas often carry
  every optional field of an internal type.
- Put the tool block early so it sits inside the cached prefix, and keep its serialisation
  stable so it stays there.
