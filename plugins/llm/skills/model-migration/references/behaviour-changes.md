# Behaviour changes to look for

Read this at step 2, when you have the provider's migration guide and deprecation page
open and need to turn them into a list that applies to your own requests. The classes
below are provider-neutral. The examples are Claude's, taken from the pages cited at the
end as they read on 2026-10-19; read the guide for your own target model rather than
trusting an example here, because these pages change with each release.

## Contents

- [Build the list from your code, not from the guide](#build-the-list-from-your-code-not-from-the-guide)
- [Loud changes and silent changes](#loud-changes-and-silent-changes)
- [The classes](#the-classes)
- [Sources](#sources)

## Build the list from your code, not from the guide

A migration guide lists every change for every caller. Most do not apply to you, and the
ones that do are found by searching your code for the thing the guide names. For each
item in the guide, write one row:

| Change | Applies? | Where (file and line, or "not used") | What would show it |
| --- | --- | --- | --- |
| Name the change in the guide's words | Yes or no, from a search | `grep` result | The eval case, metric or error that would catch it |

The last column is the one that matters. A change with no way to observe it in your
baseline and candidate runs is a change you will find in production, so either add a case
that exercises it or mark it as an accepted risk in the decision record.

Search for parameters, beta headers, tool versions and stop-reason handling in every place
a request is built, not only the obvious client: other services, notebooks, batch jobs,
infrastructure templates and prompts stored in a database.

## Loud changes and silent changes

A loud change fails the request. It is the cheap kind: the first test that sends the old
request shape finds it. A silent change returns a normal response that is different, and
nothing fails. Spend the list on the silent ones, because only a comparison of outputs
finds them.

Claude Sonnet 5.5's migration guide shows both kinds side by side. Non-default sampling
parameters, thinking budgets, a prefilled final assistant turn and forced tool choice each
return a 400 error. Thinking blocks produced by a model the target cannot read are
dropped, "the request still returns 200, and dropped blocks aren't billed". The guide
also notes that text the model writes between tool calls now comes back in thinking
blocks: "No request fails, but an interface that shows those notes goes quiet."

## The classes

1. **Request parameters rejected.** Sampling parameters, thinking budgets, prefill and
   forced tool choice returned errors on the Claude Sonnet 5.5 target. A replacement is
   rarely one-to-one: the guide says there is "no fixed mapping from a budget to an effort
   level, so run your evaluations at two or three levels". Treat the replacement setting as
   something to tune against the eval set, not to translate.
2. **Defaults that change.** On Claude Sonnet 5.5 a request with no `thinking` field runs
   with adaptive thinking, where earlier Sonnet models and Claude Haiku 4.5 ran without it.
   The same request now spends more output tokens and takes longer, and `max_tokens` also
   covers thinking. An omitted field is a setting you chose by not choosing; list every
   field your requests omit and look up its default on the target.
3. **Response shape.** Code that reads `content[0].text` breaks when a response can begin
   with a thinking block. Check parsers for assumptions about block order, empty blocks,
   new stop reasons (the guide adds `refusal` and `model_context_window_exceeded` handling)
   and fields whose default display changed.
4. **Tool-use semantics.** Without forced tool choice the model may answer without calling
   the tool, so the prompt has to say when to use it. The guide also reports that escaping
   in tool-call arguments can differ and that tool string parameters keep trailing
   newlines; parse tool input with a standard JSON parser and compare real tool-call
   arguments between baseline and candidate, not only the final answer.
5. **State carried between turns.** Thinking blocks are tied to the model and, on newer
   accounts, signed over the conversation before them. A conversation that straddles the
   switch can lose its reasoning without an error, or fail on an edited history. Decide
   what happens to conversations in flight at cutover (see "Canary" in
   `references/comparison-and-rollout.md`).
6. **Caching.** The minimum cacheable prompt differs by model, and a prompt below it is
   processed without caching and no error. The cache-read price differs by model too, and
   changing `effort` or the thinking configuration invalidates cached message blocks.
   Check `cache_creation_input_tokens` and `cache_read_input_tokens` in the response
   usage on the target before you assume the hit rate carries over.
7. **Tokenizer and limits.** The guide reports that the same text produces about 30% more
   tokens on Claude Sonnet 5.5 than on Claude Sonnet 4.6 and earlier, depending on the
   content, and that images cost more tokens at the higher resolution tier. Recount with the
   provider's token-counting endpoint against the target model, then revisit `max_tokens`,
   context budgets, truncation rules and the cost estimate. Read the target's context and
   output limits from its model page.
8. **Refusal and safety behaviour.** Claude Sonnet 5.5 declines in more categories than
   Claude Sonnet 5, and the guide says "Benign work can also trigger this category" for one of them. Measure the refusal
   rate on your eval set; a rise is a regression even when the remaining answers are
   better.
9. **Platform differences.** The same model can differ by platform. The deprecation page
   says partner-operated platforms set their own retirement schedules, and the Sonnet 5.5
   guide says structured outputs, which include strict tool use, are not available there on
   Amazon Bedrock. Read the page for the platform you call, and note that model id formats
   differ per platform.
10. **Change under an unchanged id.** For the 4.6 generation and later, Anthropic says it
    does not update the weights of an existing model id, but serving infrastructure
    around the model can change and "occasionally" produces minor differences in observed
    behaviour. For earlier models an alias such as `claude-sonnet-4-5` points at the most
    recent snapshot. Re-run the baseline on the same day as the candidate rather than
    reusing last month's numbers.

If your provider is not Claude, ask the same ten questions of its documents. If a page is
unavailable or silent on one, say so in the decision record instead of assuming the answer
is "no change".

## Sources

- Claude Sonnet 5.5 migration guide:
  <https://platform.claude.com/docs/en/models/sonnet-5-5/migration-guide>
- Model deprecations: <https://platform.claude.com/docs/en/about-claude/model-deprecations>
- Model IDs and versioning:
  <https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions>
- Prompt caching: <https://platform.claude.com/docs/en/build-with-claude/prompt-caching>
