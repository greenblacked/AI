# Using the skills with DeepSeek

## Why the tool, not the model, loads skills

A skill is read and matched by the agent tool sitting in front of a model — Claude
Code's runtime, Codex's — not by the model itself. The [provider table in the
README](../README.md#chatgpt-grok-codex-and-everything-else) lists DeepSeek's own API as
"not applicable" for exactly this reason: point one of the tools in that table at a
DeepSeek model instead, and the skills keep loading the same way they do against any
other model, because loading them was never the model's job.

This page covers one way to get a skills-aware tool talking to DeepSeek: through a
gateway. Neither Claude Code nor Codex has a native DeepSeek provider, so something has
to present DeepSeek behind an API shape the tool already speaks; Bifrost's DeepSeek page
says DeepSeek itself exposes an Anthropic-compatible Messages endpoint, but pointing
Claude Code at it directly was not verified here and is not covered below. Two gateways
are documented instead, Bifrost and OpenRouter, and neither is Anthropic's or OpenAI's
own — read "What to expect" below before relying on either for anything that matters.

## Route 1: Claude Code through Bifrost to DeepSeek

Run Bifrost locally, either with Node or with Docker:

```bash
npx -y @maximhq/bifrost
```

```bash
docker run -p 8080:8080 maximhq/bifrost
```

Either way it listens on port 8080 by default. Since Claude Code 2.1.212 the `anthropic-version` header and several others are enforced, and Bifrost's Claude Code guide warns its default Allowed Headers list does not include them: set
Allowed Headers to `*` under Settings > Client Settings, or add the guide's own
comma-separated list there instead —
`anthropic-dangerous-direct-browser-access, anthropic-version, content-type, user-agent, x-api-key, x-stainless-arch, x-stainless-helper-method, x-stainless-lang, x-stainless-os, x-stainless-package-version, x-stainless-retry-count, x-stainless-runtime, x-stainless-runtime-version, x-stainless-timeout`.

Add a DeepSeek key, either in Bifrost's `config.json`:

```json
{
  "providers": {
    "deepseek": {
      "keys": [
        {
          "name": "deepseek-key-1",
          "value": "env.DEEPSEEK_API_KEY",
          "models": ["*"],
          "weight": 1.0
        }
      ]
    }
  }
}
```

or through the Web UI, under Models > Model Providers > DeepSeek. The `env.DEEPSEEK_API_KEY`
form reads the key from an environment variable rather than storing it in the file, which
is the one worth using if `config.json` is ever committed anywhere.

Then point Claude Code at Bifrost's Anthropic-compatible endpoint. Bifrost's own Claude
Code guide sets `ANTHROPIC_BASE_URL` and `ANTHROPIC_AUTH_TOKEN`, and picks a model by
prefixing it with the provider name — its examples are `openai/…` and `vertex/…`, so
`deepseek/<model-id>` here follows the same documented rule rather than being an example
Bifrost's docs show directly. Add this to the `env` block of `~/.claude/settings.json`:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://localhost:8080/anthropic",
    "ANTHROPIC_AUTH_TOKEN": "<your-bifrost-key>",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek/<model-id>",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek/<model-id>"
  }
}
```

`<your-bifrost-key>` is a Bifrost virtual key (an `sk-bf-…` value created under Virtual
Keys in the Web UI), with the DeepSeek provider allowed on it — a virtual key denies
every provider it does not list. Bifrost does not require one by default; the reason to
set it is that Claude Code then needs no Anthropic login. `<model-id>` is one of
DeepSeek's own model ids; Bifrost's DeepSeek page says its model listing passes through
to DeepSeek's `/models`, so the gateway's model list shows what your key can reach.
Keeping the key in `settings.json`'s `env` block, or in an environment file your shell
loads on its own, keeps it out of shell history; do not pass it on a command line you
will run interactively.

## Route 2: Claude Code through OpenRouter to DeepSeek

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

Both Route 1's and Route 2's guides say to clear a cached Anthropic login before the
environment above takes effect: run `/logout` inside Claude Code once, then quit and
relaunch it. OpenRouter's guide says skipping this can surface "confusing model-not-found
errors" for a gateway-only model name; Bifrost's guide additionally says to open
`settings.json` first and remove a `model` field if one is present, because it
"overwrites the `env`-based model selection and can cause unexpected behavior."

## Route 3: Codex through Bifrost to DeepSeek

Codex CLI always prefers OAuth over a custom API key when both are configured, so
Bifrost's Codex guide says to run `/logout` before configuring the gateway below —
otherwise the cached login is used instead of the key you set here.

Codex selects its model provider from `~/.codex/config.toml`, and only accepts an API
shaped like the OpenAI Responses API for a user-defined provider — `wire_api = "chat"` is
a hard configuration error in current Codex, removed rather than merely discouraged.
Bifrost's OpenAI-compatible endpoint speaks Responses, so it is the one to point at:

```toml
model_provider = "bifrost"
model = "deepseek/<model-id>"

[model_providers.bifrost]
name = "Bifrost"
base_url = "http://localhost:8080/openai/v1"
env_key = "OPENAI_API_KEY"
wire_api = "responses"
supports_websockets = false
```

`env_key` names the environment variable Codex reads the bearer token from — here it is
`OPENAI_API_KEY`, holding Bifrost's key rather than an actual OpenAI one. Set it in an
environment file your shell loads rather than exporting it on an interactive command
line, for the same reason as Route 1. Unlike Route 1's inferred `deepseek/<model-id>`,
Bifrost's Codex guide names `deepseek` directly among the twenty providers it accepts in
`provider/model-name` form, alongside `openai`, `gemini` and `mistral`.
`supports_websockets = false` is there because Codex defaults to WebSocket mode for the
Responses API, falling back to HTTPS only if that connection fails, and Bifrost's guide
says non-OpenAI models are not supported in WebSocket mode — because that mode expects
the server to hold the conversation's state itself — so this setting puts Codex in HTTPS
mode for the DeepSeek model configured here. Codex loads this repository's skills from
`~/.codex/skills` regardless of which model provider is configured, so nothing here
changes how `make install` or the [provider table](../README.md#chatgpt-grok-codex-and-everything-else)'s Codex row apply.

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
`CLAUDE_CODE_SUBAGENT_MODEL`, then the main conversation's model — and under either route
above that ends at the DeepSeek model the session is running on, with the same caveats.
To put them on a different model, set `CLAUDE_CODE_SUBAGENT_MODEL` to another model id
the gateway serves.

## Checking it works

In Claude Code (Routes 1 and 2), run `/status` first: OpenRouter's guide shows it
printing an `Auth token` line naming `ANTHROPIC_AUTH_TOKEN` and an `Anthropic base URL`
line naming the gateway, which confirms the environment reached the session before
anything else does. Then ask the tool something that should trigger a skill or list what
is installed — "what skills do you have installed" or a prompt that should match one by
description.

Next check the gateway's own record of the request, not just the reply: Bifrost's
observability view shows which provider and model handled each request, with real-time
log streaming, so DeepSeek should appear there as the provider. OpenRouter calls the
equivalent view the Activity Dashboard (openrouter.ai/activity); check the model column
there for the same thing. Either way, seeing the DeepSeek model in that log is what
confirms the routing — regardless of whether the reply itself looks right, which is what
"What to expect" above is about.

## Not covered

Pointing Claude Code directly at DeepSeek's own Anthropic-compatible Messages endpoint,
with no gateway in front of it, is not documented here: Bifrost's DeepSeek page says the
endpoint exists, but using it directly with Claude Code was not verified.

Codex through OpenRouter is not documented on this page either: Codex requires a provider
that speaks the OpenAI Responses API, and whether OpenRouter exposes one could not be
confirmed from here.
