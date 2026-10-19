---
name: structured-output
description: "Get machine-readable output from a language model that a program can trust: JSON, tool-call arguments, enums and extraction records. Write the schema first as the contract, small and flat; use the provider's native structured-output, strict tool-use or strict JSON-schema mode rather than prompt-only instructions; validate every response in code; repair in a bounded loop that feeds the error back, then fail closed; version the schema and test it with fixtures of real failures. Use whenever someone asks how to make an LLM return valid JSON, why parsing keeps breaking, JSON mode versus function calling versus a schema, or how to retry a malformed reply. Not for fields from scans and images (document-extraction), the HTTP interface around the result (api-design), database tables (schema-design), retrieval over documents (rag-design) or scoring agent quality (agent-evaluation)."
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(python3:*), Bash(jq:*)
---

# Structured Output

A structured-output integration is finished when the program downstream of the model can only ever receive a value that passed the schema and the semantic checks, and every other outcome is a named failure that someone can see.

The job is hard because the failure is partial and quiet. A prompt that says "respond with JSON" works in the demo, then a fenced block, a trailing comment, a string where a number belongs or a made-up enum value reaches a parser at three in the morning. The provider's constrained mode closes most of that gap, but not all of it: a refusal or a truncated response does not match the schema, the SDK may strip constraints before sending them, and a valid shape can still carry a wrong value. The model's own statement that its output is valid is not evidence of anything. Only code that reads the response is.

## Scope

Use for: getting JSON, tool-call arguments, enums, booleans and extraction records out of a model and into a program, including choosing the provider mode, shaping the schema, validating, retrying and testing.

Do not use for: reading fields out of scans, photographs and PDFs, where the hard part is the document rather than the output contract, which is `document-extraction`. Designing the HTTP or RPC interface that serves the result, which is `api-design`. Modelling the tables that store it, which is `schema-design`. Grounding an answer in your own documents, which is `rag-design`. Measuring whether an agent or a prompt is good enough to ship, which is `agent-evaluation`; the fixtures here guard the output contract, not answer quality. Cutting the token bill of the calls, which is `llm-cost`.

## Hard gates

1. No prompt before the schema. The schema is the contract between the model and the program, so write it, and the consumer code that reads it, first.
2. Use the provider's native constrained mode whenever one exists for the model. A prompt-only instruction is a fallback for runtimes with no such mode, and it makes step 5 the only thing standing between the model and the program.
3. Every response is parsed and validated against the schema in code before anything reads a field, in native mode too. Constrained decoding is a strong prior, not a receipt.
4. A failed validation gets a bounded repair loop and then fails closed. No unbounded retry, no default value standing in for a missing answer, no partial result passed on.
5. Never act on the model's claim about its own output: a field such as `is_valid`, `confident` or `follows_schema` is just more output to validate.

## Workflow

### 1. Write the schema as the contract

Start from the consumer: list what the program does with each field, and drop any field no code reads. A field that exists "in case it is useful" is a place for the model to be wrong.

Keep the schema small and flat. Prefer one level of objects, a short list of required fields and arrays of simple records over nesting. Every optional field and every union makes constrained decoding costlier, and Anthropic caps both (see step 3). Split one large schema into two calls when the pieces do not depend on each other.

Replace free text with a closed vocabulary wherever code branches on the value:

- Use an `enum` for any categorical field, with an explicit `unknown` or `other` member so the model has an honest way out instead of inventing a near-miss.
- Express "not present" as a nullable field that is still required, not as an omitted field. The key is always there, so absence is a value the code handles in one place.
- Use `boolean`, `integer` and `date` types and formats rather than strings that code later parses.
- Put a short `description` on each field saying what it means and what to do when the source is silent; descriptions are the cheapest way to steer a value and do not change the grammar.
- When a field is derived from evidence, place the evidence field before it so the model writes the support first. This is judgement, not a provider guarantee, and the evals are where to confirm it helps.

Read `references/schema-and-fixtures.md` for the full set of schema rules and a worked before-and-after.

### 2. Choose the mechanism

| The response is | Use | Fallback |
| --- | --- | --- |
| Data the program consumes | The provider's JSON-schema response format | Prompt, parse, validate (step 4) |
| A decision to call a function | Strict tool use with the schema as the tool input | Same fallback, tool arguments validated as JSON |
| Both: tool calls, then a structured final answer | Strict tools and a JSON-schema format in one request where the provider allows it | Two calls |

On the Anthropic API that is `output_config.format` with `type: "json_schema"`, and `strict: true` on a tool definition. On the OpenAI API it is `response_format` with `type: "json_schema"` (the Responses API takes the same schema under its text format), and `strict: true` on a function definition. Set `strict` explicitly on OpenAI: the API reference defaults it to false, and without it the request does not get the schema-adherence guarantee. JSON mode (`json_object`) guarantees syntactically valid JSON and nothing about its shape, and the API reference marks it as not recommended for newer models; do not use it where a schema mode exists.

The SDK helpers (`messages.parse` with a Pydantic model on Anthropic, `chat.completions.parse` or `responses.parse` on OpenAI) keep the schema and the type in one place and are the default way in. Read `references/provider-modes.md` before writing the request: it has the exact parameters, the incompatibilities, the failure shapes and the sources, each checked against the provider's own documentation.

### 3. Fit the schema inside the provider's subset

Both providers support a subset of JSON Schema in constrained mode. Anthropic documents the unsupported keywords and rejects a request that uses one with a 400 error, so a schema that works in one provider can fail on another. Anthropic also caps optional parameters and union-typed parameters across a request, so a flat schema with required fields is also the one that compiles.

Keep the original schema, with its minimums, lengths and patterns, as the source of truth for step 4 even when the SDK strips those constraints before sending. A stripped constraint still has to be enforced somewhere, and that place is your code.

### 4. Validate every response in code

Do the checks in this order, because each makes the next one meaningful:

1. Check the stop condition. A refusal and a response cut off at the token limit do not match the schema by design. Neither is a validation error to repair; handle them as their own outcomes.
2. Parse the text as JSON.
3. Validate against the schema with a real validator, not a field-by-field `if`.
4. Run the semantic checks the schema cannot express: a value that must appear in the source text, a total that must equal the sum of its lines, an end date that must follow a start date.
5. Only then hand the value to the program.

A schema `enum` is case-sensitive and the provider can return a member in different case, so an enum case check placed here never fires for a field whose schema still carries the `enum`. Fold the case before step 3, or leave the `enum` out of the validation copy and let a semantic check own it.

Read `references/validate-and-repair.md` for a reference implementation of this order and the repair loop.

### 5. Repair in a bounded loop, then fail closed

When validation fails and the stop condition was normal, send the failing output back with the validation errors, as paths and messages, and ask for a corrected reply. Cap the attempts at a small fixed number, one or two as a starting point (a judgement, not a provider figure): the error is the only new information a retry has, so when it does not fix the output the schema or the input is usually the problem, and each retry costs latency and tokens.

When the cap is reached, fail closed: raise a named error that carries the attempts and the problems, and let the caller route the item to a queue, a human or a documented fallback. Do not substitute a default, do not pass on a partial record and do not loosen the schema until it passes. Log the raw reply of every failure; each one is a fixture for step 6.

### 6. Version the schema and test it with real failures

Give the schema a version that travels with every stored result, and treat a change like an interface change: adding a nullable field is additive, while removing a field, narrowing an enum or changing a type breaks every stored value and every consumer. Change the prompt, the schema and the consumer in one commit.

Keep a fixture file per failure that production or evals actually produced: the raw reply, the stop condition and what the validator must say. Replay the fixtures in the unit tests without a model, so a schema or validator change that would have let a past failure through fails the build. Read `references/schema-and-fixtures.md` for the fixture format and the test.

### 7. Hand off

Hand scoring of whether the extracted values are right, across prompts and models, to `agent-evaluation`. Hand the endpoint that exposes the result to `api-design`, and the storage of it to `schema-design`.

## Anti-patterns

**Stripping code fences and hoping.** A regex that peels a markdown fence off a prompt-only reply works until the model adds a sentence before it. Use a constrained mode, and when there is none, treat a failed parse as a failure to repair, not a string to massage.

**Trusting native mode and skipping validation.** The provider documents refusals and truncation as cases where the output does not match the schema, and casing differences in enum values as a case where it can differ quietly. The validator is what notices.

**A defaulted value on failure.** Filling in `"unknown"` or `0` after the final retry turns a visible failure into wrong data that looks real. Fail closed and let the caller decide.

**Asking the model to certify itself.** A `valid: true` or a self-reported confidence field is not independent of the answer it describes. Validate in code; calibrate any confidence against labelled data before it gates anything.

**Retrying without a bound, or without the error.** An identical retry mostly reproduces the failure, and an unbounded one turns a bad input into a runaway bill. Send the validation error, cap the attempts and stop.

**One schema for every task.** A wide schema with dozens of optional fields is expensive to compile and invites the model to fill fields the source does not support. Several small schemas, each with a consumer, are easier to validate and to version.

**Free text where code branches.** A `category` string compared with `==` fails on the first synonym. Use an enum with an escape member.

**Letting the prompt and the schema drift.** A prompt that restates the field list by hand is a second copy that goes stale. Generate it from the schema or leave the shape to the schema and the descriptions.
