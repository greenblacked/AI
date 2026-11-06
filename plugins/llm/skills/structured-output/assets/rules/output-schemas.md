---
paths:
  - "**/schemas/**/*.json"
---

# Output schemas

Loads when a schema file under a `schemas/` directory is read or edited. The schema is the
contract between the model and the program that reads its reply; write it for a strict
provider mode, and treat any change as an interface change.

- Close every object with `"additionalProperties": false`. Both providers' strict modes
  need it, and an open object lets the model invent a field that code then has to decide
  about.
- List every property in `required`. Express "not present" as a nullable type such as
  `["string", "null"]` that is still required, not as an omitted key.
- Use an `enum` for any value that code branches on, with an explicit `unknown` or `other`
  member so the model has an honest way out.
- Keep it flat and small. Drop a field no code reads; avoid recursion, deep nesting and
  long unions, which providers cap or reject.
- Keep minimums, lengths and patterns in the source-of-truth copy that code validates with,
  even where the provider strips them from the request.
- Any change gets a new schema version. Change the schema, the prompt and the consumer in
  one commit, add a fixture for the failure that motivated it, and record the change in
  `schema-change-record.md`, the template shipped beside the `structured-output` skill.
