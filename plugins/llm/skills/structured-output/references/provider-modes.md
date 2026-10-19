# Provider modes

Read this before writing the request, when choosing between a JSON-schema response format and strict tool use, and again when a native-mode response still fails validation. It records what each provider documents, with the source, as checked on 2026-10-19. Provider limits and model lists change, so confirm anything you depend on against the page before shipping.

## Anthropic

Sources: [Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) and [Strict tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use).

Two features, usable alone or together in one request:

- **JSON outputs.** Put the schema in `output_config.format` as `{"type": "json_schema", "schema": {...}}`. The reply is JSON in the response's text content block. The older top-level `output_format` parameter is deprecated in favour of `output_config.format`.
- **Strict tool use.** Set `strict: true` on a tool definition and the tool name and its input are validated against `input_schema`. Use it when the response is a function call; use JSON outputs when the response is the data.

The SDK helpers take a Pydantic model (`client.messages.parse(..., output_format=Model)` in Python) or a Zod schema (`zodOutputFormat()` in TypeScript) and return the parsed value in `parsed_output`. The documentation marks `parse()` as the recommended route.

What the page says about shape and limits:

- Unsupported in constrained mode: recursive schemas, numerical constraints (`minimum`, `maximum`, `multipleOf`), string length constraints, `additionalProperties` other than `false`, and array `minItems` beyond 0 or 1. Using one returns a 400 error.
- Every object must set `additionalProperties: false`.
- Limits across all strict schemas in one request: 20 strict tools, 24 optional parameters, and 16 parameters with union types (`anyOf` or a type array such as `["string", "null"]`). Beyond these there are internal grammar-size limits that return "Schema is too complex for compilation".
- Properties come back required first, then optional. Mark everything required if the order matters.
- The first request with a new schema pays a grammar-compile delay; compiled grammars are cached for 24 hours from last use. Changing the schema invalidates the cache and any prompt cache for that conversation.
- Not compatible with citations (a 400 error) or with message prefilling.
- The schema is cached up to 24 hours, so keep protected health information and other sensitive data out of property names, enum values and patterns.

The SDK transformation: helpers remove unsupported constraints, add them to the field's description, set `additionalProperties: false`, and, if the helper validates responses, check the reply against your original schema. A helper that does not validate leaves those constraints unenforced, so validate yourself.

How a native-mode response still fails to match, from the same page:

- `stop_reason: "refusal"` arrives with HTTP 200 and may not match the schema. A property that asks for step-by-step reasoning can trigger a `reasoning_extraction` refusal; ask for a short explanation instead.
- `stop_reason: "max_tokens"` means the JSON may be incomplete. Raise `max_tokens` or shrink the schema.
- Enum and `const` strings can differ from the schema in capitalisation, with no error and no special stop reason. Compare case-insensitively and avoid values that differ only in case.

## OpenAI

Sources: the [API reference specification](https://github.com/openai/openai-openapi) (`openapi.yaml`, `manual_spec` branch), the [openai-python structured-output helpers](https://github.com/openai/openai-python/blob/main/helpers.md), and the SDK's strict-schema conversion in `src/openai/lib/_pydantic.py`. The Structured Outputs guide at `platform.openai.com/docs/guides/structured-outputs` was not reachable when this was written, so the supported-keyword list is not restated here: read it for the subset before you design the schema.

- **Response format.** `response_format` of `{"type": "json_schema", "json_schema": {"name": ..., "schema": {...}, "strict": true}}` on Chat Completions. The Responses API takes `type`, `name`, `schema` and `strict` under its `text` format. Both carry the guarantee only when `strict` is true; the specification gives `strict` a default of false and says the schema is followed exactly when it is true, with only a subset of JSON Schema supported.
- **JSON mode.** `{"type": "json_object"}` ensures valid JSON, not a shape. The specification requires you to also tell the model to produce JSON, warning that otherwise it may emit whitespace until the token limit, and calls it not recommended for newer models in favour of `json_schema`.
- **Function calling.** `strict: true` on the function definition applies the same schema adherence to the arguments.
- **SDK helpers.** `client.chat.completions.parse(..., response_format=Model)` and `client.responses.parse(..., text_format=Model)` convert a Pydantic model, send it and parse the reply. `openai.pydantic_function_tool(Model)` builds a strict function tool and exposes `parsed_arguments`. The conversion marks every property required and sets `additionalProperties` to false when absent, which is why optional fields are modelled as required and nullable on this provider.
- **Failure shapes.** A refusal does not follow your schema; it arrives in the message's `refusal` field instead of content, so check it before deserialising. `parse()` raises `LengthFinishReasonError` or `ContentFilterFinishReasonError` when `finish_reason` is `length` or `content_filter`. On the Responses API, `output_parsed` is `None` when there is no parsed result, and a refusal is not replaced by commentary text.

## Providers with no native mode

Use a prompt that states the shape, request JSON only, and treat the reply as untrusted text: parse, validate, repair, fail closed. If the runtime offers grammar-constrained or schema-guided decoding, prefer it and still validate. Expect more repairs and keep the schema smaller than you would for a native mode, because nothing but your own check backs it up.

## Choosing between the two modes

Use the JSON-schema format when the reply is the product: a classification, a record, a plan the program executes. Use strict tool use when the model chooses among actions and the arguments drive code. Use both when an agent calls tools and then returns a structured final answer. A tool the model may call with free-form arguments is a hole in the contract; make the schema strict or validate the arguments before running the tool.
