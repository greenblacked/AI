# Using the skills with DeepSeek

## Why the tool, not the model, loads skills

A skill is read and matched by the agent tool sitting in front of a model — Claude
Code's runtime, Codex's — not by the model itself. The [provider table in the
README](../README.md#chatgpt-grok-codex-and-everything-else) lists DeepSeek's own API as
"not applicable" for exactly this reason: point one of the tools in that table at a
DeepSeek model instead, and the skills keep loading the same way they do against any
other model, because loading them was never the model's job.

This page covers one way to get a skills-aware tool talking to DeepSeek: through a
gateway. Claude Code has no native DeepSeek provider, so something has to present
DeepSeek behind an API shape the tool already speaks. One gateway is documented below,
OpenRouter, and it is not Anthropic's own — read "What to expect" below before relying
on it for anything that matters.

## Claude Code through OpenRouter to DeepSeek

OpenRouter's own Claude Code guide sets three environment variables, and is explicit that
`ANTHROPIC_API_KEY` has to be present and empty, not merely unset:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://openrouter.ai/api",
    "ANTHROPIC_AUTH_TOKEN": "<your-openrouter-key>",
    "ANTHROPIC_API_KEY": "",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "<deepseek-model-id>",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "<deepseek-model-id>"
  }
}
```

Take `<deepseek-model-id>` from OpenRouter's own model list at
[openrouter.ai/models](https://openrouter.ai/models), filtered to DeepSeek — current ids
could not be verified from here, so none is printed on this page. Pick one whose listing
shows tool calling, not just chat: Claude Code's agent loop, including every skill that
runs a command rather than just reading one, depends on the model being able to call
tools.

OpenRouter's guide says to clear a cached Anthropic login before the environment above
takes effect: run `/logout` inside Claude Code once, then quit and relaunch it. Skipping
this can surface "confusing model-not-found errors" for a gateway-only model name.

## What to expect

Anthropic does not support this arrangement, in its own words: "Anthropic doesn't
endorse, maintain, or audit third-party gateway products, and doesn't support routing
Claude Code to non-Claude models through any gateway." OpenRouter says the same about its
own integration: "Claude Code with OpenRouter is only guaranteed to work with the
Anthropic first-party provider" and "Claude Code is optimized for Anthropic models and
may not work correctly with other providers." Nothing below changes that; it only lists
which specific behaviour is affected, from Claude Code's own gateway protocol
documentation:

- Adaptive reasoning returns an HTTP 400 if the upstream model cannot accept the
  `thinking` field — Claude Code retries the request and disables the rejected
  capability for the rest of the conversation, so the session degrades rather than
  stopping outright.
- Prompt caching silently bills every turn as uncached input if the gateway does not
  forward `cache_control` — no error, just a larger bill than expected.
- Token counting falls back to a character estimate when the gateway has no
  `/v1/messages/count_tokens` endpoint.
- Extended context and interleaved thinking become silently unavailable if the gateway
  strips the `anthropic-beta` headers.

None of these is DeepSeek-specific; they follow from routing Claude Code through any
non-Anthropic gateway at all, DeepSeek included. Subagents shipped in this repository's
plugins are not exempt: none of them sets a `model` key, so Claude Code falls through its
documented order — a per-invocation choice, then the frontmatter, then
`CLAUDE_CODE_SUBAGENT_MODEL`, then the main conversation's model — and under the Claude
Code route above that ends at the DeepSeek model the session is running on, with the
same caveats.
To put them on a different model, set `CLAUDE_CODE_SUBAGENT_MODEL` to another model id
the gateway serves.

## Checking it works

In Claude Code, run `/status` first: OpenRouter's guide shows it printing an `Auth token`
line naming `ANTHROPIC_AUTH_TOKEN` and an `Anthropic base URL` line naming the gateway,
which confirms the environment reached the session before anything else does. Then ask
the tool something that should trigger a skill or list what is installed — "what skills
do you have installed" or a prompt that should match one by description.

Next check the gateway's own record of the request, not just the reply: OpenRouter's
Activity Dashboard (openrouter.ai/activity) shows which model handled each request; check
the model column there for DeepSeek. Seeing the DeepSeek model in that log is what
confirms the routing — regardless of whether the reply itself looks right, which is what
"What to expect" above is about.

## Not covered

Codex is not covered on this page: it requires a provider that speaks the OpenAI
Responses API, and whether OpenRouter exposes one directly could not be confirmed from
here, so no Codex route to DeepSeek is documented.
