# Schema rules and fixtures

Read this when drafting or changing a schema, when a field keeps coming back wrong, and when setting up the tests that guard the contract. It covers the shape rules in more detail than the body, the versioning rule, and the fixture format with a test that replays it without a model.

## Contents

- [Schema rules](#schema-rules)
- [Versioning](#versioning)
- [Fixtures of real failures](#fixtures-of-real-failures)

## Schema rules

1. **One consumer per field.** For each field, name the line of code that reads it. Delete the field if there is none.
2. **Flat before nested.** One object holding scalars and short arrays of simple records. Reach for a nested object only when the consumer treats the group as a unit. Anthropic limits optional parameters and unions across a request, and nesting multiplies both (see `references/provider-modes.md`).
3. **Required and nullable, not optional.** Mark every field required and allow `null` where the source may be silent: `"type": ["string", "null"]`. One provider's SDK rewrites optional fields this way anyway, and the code then has one place to handle absence. A nullable field is still a union, so spend them where absence is real rather than on every field.
4. **Closed vocabularies.** `enum` for any value code branches on, with an `unknown` or `other` member. Keep members distinct by more than case. Document each member in the field's `description` in a clause, because the name alone is where the model guesses.
5. **Typed values.** Booleans, integers and `date` or `date-time` formats instead of strings the code parses later. Money as an integer of minor units with a currency field.
6. **Descriptions say what to do when unsure.** "The invoice total in minor units; null if the document shows no total." A description steers the value without changing the grammar.
7. **Keep constraints you will enforce yourself.** `minimum`, `maxLength` and `pattern` may be stripped or rejected by the provider's mode. Keep them in the schema your validator uses, and send the provider the simplified copy.
8. **No self-assessment fields.** A `confidence`, `is_valid` or `reasoning` field is more output, not a check. If you want an explanation for a human, ask for a short one; one provider documents that asking for step-by-step reasoning in a field can trigger a refusal.
9. **Evidence before the claim.** Where a value is derived from the source, put a `quote` or `evidence` field ahead of it in the schema. Verify the quote against the source in a semantic check. This is judgement; confirm it helps on your own cases.

### Before and after

A schema that invites the failures:

```json
{
  "type": "object",
  "properties": {
    "result": {
      "type": "object",
      "properties": {
        "kind": {"type": "string"},
        "urgency": {"type": "string"},
        "summary": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1}
      }
    },
    "is_valid": {"type": "boolean"}
  }
}
```

The same job, as a contract:

```json
{
  "type": "object",
  "properties": {
    "category": {
      "type": "string",
      "enum": ["billing", "outage", "access", "other"],
      "description": "The main topic; other when none of the first three fits."
    },
    "urgency": {
      "type": "string",
      "enum": ["low", "normal", "high"],
      "description": "high only when the customer reports lost service."
    },
    "customer_quote": {
      "type": ["string", "null"],
      "description": "The sentence that supports the category, copied exactly; null if none."
    }
  },
  "required": ["category", "urgency", "customer_quote"],
  "additionalProperties": false
}
```

The first has no required fields, free-text categories, no closing `additionalProperties`, a number the provider may not constrain and a validity flag nobody can trust. The second has three fields the router reads, two closed vocabularies and one supporting quote the code can check against the ticket text.

## Versioning

- Store a `schema_version` next to every persisted result. Keep it in your storage, not in the model's output, so the model never has a field it can get wrong.
- Additive and safe: a new nullable field, a new member added to an enum that consumers already handle with a default branch.
- Breaking: removing or renaming a field, changing a type, removing an enum member, making a nullable field non-null. Ship a new version and keep the old validator for stored values as long as they exist.
- Change the schema, the prompt and the consumer in one commit, with the fixtures updated in the same change.

## Fixtures of real failures

Every attempt in a `StructuredOutputError` is a candidate. Save the raw reply and the stop condition, and record what the validator must say about it. Keep real replies, lightly scrubbed of personal data, over invented ones: the inputs that fail in production are rarely the ones you would think to write.

```json
[
  {
    "name": "prose-before-json",
    "stop": "end",
    "source": "I was charged twice this month.",
    "text": "Here is the result: {\"category\": \"billing\"}",
    "expect_problem": "not valid JSON"
  },
  {
    "name": "enum-near-miss",
    "stop": "end",
    "source": "I was charged twice this month.",
    "text": "{\"category\": \"Billing issue\", \"urgency\": \"low\", \"customer_quote\": \"I was charged twice this month.\"}",
    "expect_problem": "category"
  },
  {
    "name": "truncated",
    "stop": "max_tokens",
    "source": "The site has been down since 9am.",
    "text": "{\"category\": \"outage\", \"urg",
    "expect_problem": "did not finish normally"
  },
  {
    "name": "non-finite-number",
    "stop": "end",
    "source": "The site has been down since 9am.",
    "text": "{\"category\": \"outage\", \"urgency\": NaN, \"customer_quote\": \"The site has been down since 9am.\"}",
    "expect_problem": "not valid JSON"
  },
  {
    "name": "unsupported-claim",
    "stop": "end",
    "source": "Can you change the email on my account?",
    "text": "{\"category\": \"outage\", \"urgency\": \"high\", \"customer_quote\": null}",
    "expect_problem": "no supporting quote"
  },
  {
    "name": "valid",
    "stop": "end",
    "source": "The site has been down since 9am.",
    "text": "{\"category\": \"outage\", \"urgency\": \"high\", \"customer_quote\": \"The site has been down since 9am.\"}",
    "expect_problem": null
  }
]
```

Replay them without calling a model, so the test runs in every build:

```python
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from validate_and_repair import ModelReply, StopReason, check_reply, quote_in_source  # your module

SCHEMA = json.loads(Path("schemas/ticket_v2.json").read_text())
CASES = json.loads(Path("tests/fixtures/ticket_v2_failures.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_fixture(case):
    reply = ModelReply(case["text"], StopReason(case["stop"]))
    validator = Draft202012Validator(SCHEMA, format_checker=Draft202012Validator.FORMAT_CHECKER)
    checks = [quote_in_source("customer_quote", case["source"])]  # the checks production runs
    value, problems = check_reply(reply, validator, checks)
    if case["expect_problem"] is None:
        assert problems == [] and value is not None
    else:
        assert value is None
        assert any(case["expect_problem"] in p for p in problems)
```

Each case carries the source text its semantic checks read, so the replay runs the same checks production does; a fixture replayed through the schema alone would pass a claim with no supporting quote. These tests guard the contract: the validator, the schema and the semantic checks still reject what they rejected before. They do not show that the answers are right. For that, run the same inputs against a labelled set with a live model whenever the prompt, the schema or the model changes, and score it with `agent-evaluation`.

When a failure the loop could not repair reaches a person, add the case to the fixtures before closing the ticket.
