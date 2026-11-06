# Schema change record

One change to an output schema. Fill in every field; delete the guidance in brackets. A
change to the prompt, the schema and the consumer lands in one commit, so this record
describes all three.

## Change

- Schema file: [path under schemas/]
- Old version: [version]
- New version: [version; every change gets a new one]
- Reason: [the failure or the consumer need that prompted it, with a link to the fixture]
- Kind: [field added / field removed / enum member added / enum member removed / type
  changed / description only]

## Compatibility

| Direction | Result | Handling |
| --- | --- | --- |
| New schema reads a stored result of the old version | [accepted / rejected] | [migrate, dual-read or discard] |
| Old consumer reads a new result | [accepted / rejected] | [deploy order] |

A new required field, even a nullable one, makes every stored result fail the new schema.
A new property or enum member is rejected by the old validator under `additionalProperties:
false`.

## Consumers and prompt

| Consumer or prompt | Change made in the same commit |
| --- | --- |
| [service, job or prompt file] | [what changed] |

## Provider subset

- Mode used: [native JSON schema / strict tool use / prompt-only fallback]
- Keywords stripped or unsupported by the provider: [list, and where code enforces them]
- Objects closed with `additionalProperties: false`: [yes, every one / exceptions and why]

## Fixtures

| Fixture | Raw reply | Stop condition | What the validator must say |
| --- | --- | --- | --- |
| [name] | [redacted reply] | [end_turn / refusal / max_tokens] | [pass / error path and message] |

## Rollback

[How to return to the old version: the commit to revert, and what happens to results
written under the new version.]
