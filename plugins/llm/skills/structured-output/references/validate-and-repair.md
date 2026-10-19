# Validate and repair

Read this when writing the code between the model call and the rest of the program: the parse, the validation, the semantic checks and the bounded repair loop. The code below is provider-neutral; wrap your SDK call in `call_model` and normalise its stop condition into the four values `StopReason` allows.

It uses the third-party `jsonschema` package. If a dependency is not allowed, use the schema validator your SDK already depends on (Pydantic's `model_validate_json` does the parse and the schema check together); the order of checks stays the same.

## Contents

- [The implementation](#the-implementation)
- [Why it is shaped this way](#why-it-is-shaped-this-way)
- [Two semantic checks](#two-semantic-checks)

## The implementation

```python
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum

from jsonschema import Draft202012Validator


class StopReason(Enum):
    END = "end"  # a normal, complete reply
    MAX_TOKENS = "max_tokens"  # cut off: the JSON may be incomplete
    REFUSAL = "refusal"  # the model declined: no schema match is expected
    OTHER = "other"  # anything else the provider reports


@dataclass
class ModelReply:
    text: str
    stop: StopReason


@dataclass
class Attempt:
    raw: str
    stop: StopReason
    problems: list[str]


class StructuredOutputError(Exception):
    """No usable value was obtained. Callers must not continue as if one was."""

    def __init__(self, attempts: list[Attempt]):
        self.attempts = attempts
        last = attempts[-1]
        super().__init__(
            f"{len(attempts)} attempt(s); last stop={last.stop.value}; "
            f"problems={last.problems}"
        )


SemanticCheck = Callable[[object], list[str]]


def check_reply(
    reply: ModelReply,
    validator: Draft202012Validator,
    semantic_checks: Sequence[SemanticCheck] = (),
) -> tuple[object | None, list[str]]:
    """Return (value, problems). The value is usable only when problems is empty."""
    if reply.stop is not StopReason.END:
        return None, [f"reply did not finish normally: {reply.stop.value}"]
    try:
        value = json.loads(reply.text)
    except json.JSONDecodeError as exc:
        return None, [f"not valid JSON: {exc.msg} at position {exc.pos}"]
    errors = sorted(validator.iter_errors(value), key=lambda e: list(map(str, e.path)))
    problems = [
        f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
        for e in errors
    ]
    if not problems:  # semantic checks assume a well-shaped value
        for check in semantic_checks:
            problems.extend(check(value))
    return (None if problems else value), problems


def get_structured(
    call_model: Callable[[list[dict]], ModelReply],
    messages: list[dict],
    schema: dict,
    semantic_checks: Sequence[SemanticCheck] = (),
    max_repairs: int = 2,
    max_problems_sent: int = 10,
) -> object:
    Draft202012Validator.check_schema(schema)  # a broken schema is a bug, not a retry
    validator = Draft202012Validator(schema)
    history = list(messages)
    attempts: list[Attempt] = []
    for _ in range(max_repairs + 1):
        reply = call_model(history)
        value, problems = check_reply(reply, validator, semantic_checks)
        attempts.append(Attempt(reply.text, reply.stop, problems))
        if not problems:
            return value
        if reply.stop in (StopReason.REFUSAL, StopReason.MAX_TOKENS):
            break  # repeating the request does not change a refusal or a limit
        shown = problems[:max_problems_sent]
        history = history + [
            {"role": "assistant", "content": reply.text},
            {
                "role": "user",
                "content": "Your previous reply failed validation:\n- "
                + "\n- ".join(shown)
                + "\nReturn a corrected reply that satisfies the schema.",
            },
        ]
    raise StructuredOutputError(attempts)
```

## Why it is shaped this way

- **The stop condition comes first.** A refusal and a truncated reply are not malformed output to repair. Repeating the call reproduces a refusal and a token limit, so the loop stops and the caller decides: raise the limit, shrink the schema, or route the item to a person.
- **Problems are paths and messages.** They tell the model where the reply is wrong and cost few tokens. Cap how many are sent so one badly broken reply does not flood the retry prompt.
- **Semantic checks run only on a well-shaped value.** A check that indexes a field the schema did not guarantee raises a `KeyError` instead of reporting a problem.
- **The error carries every attempt.** The raw replies are the raw material for fixtures; write them to your log before anything else consumes the exception.
- **There is no default branch.** Exhausting the attempts raises. The only code that decides what a failure means is the caller that knows the business context.

## Two semantic checks

Worth writing in almost every integration, with the enum check kept for a field whose schema
does not carry the `enum` (`SKILL.md` step 4 says the same). These run after the schema validator, and the JSON
Schema `enum` keyword is case-sensitive, so `enum_case_insensitive` is only reached for a field
whose schema does not carry that `enum`. For a field where casing drift is tolerable, normalise
the case before schema validation, or drop the `enum` from the validation copy of the schema
and let this check own it; otherwise a value such as `Invoice` fails the schema and spends a
repair attempt. This is a reference implementation, not a tested one.

```python
def enum_case_insensitive(field: str, allowed: set[str]) -> SemanticCheck:
    lowered = {a.lower() for a in allowed}

    def check(value: object) -> list[str]:
        got = str(value[field])  # type: ignore[index]
        return (
            []
            if got.lower() in lowered
            else [f"{field}: {got!r} is not an allowed value"]
        )

    return check


def quote_in_source(field: str, source: str) -> SemanticCheck:
    def check(value: object) -> list[str]:
        quote = value[field]  # type: ignore[index]
        if quote is None or quote in source:
            return []
        return [f"{field}: quoted text does not appear in the source"]

    return check
```

The second one is the cheapest defence against a plausible value the source never contained: ask for the supporting quote as a field and verify it by string search.

When a value is normalised after validation (case folded to the canonical enum member, whitespace trimmed), do it in one function and store the normalised value, not the raw one.
