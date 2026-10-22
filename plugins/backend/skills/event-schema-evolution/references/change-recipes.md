# Change recipes

Contents: common changes by format, rename, split, type change, retirement.

## Common changes

| Change | Avro | Protobuf | JSON Schema |
| --- | --- | --- | --- |
| Add optional field | Add with a `default`; compatible both ways | Add with a new field number; compatible both ways | Add as not required; fine unless `additionalProperties` is false |
| Remove field | Only if it had a default | Remove and `reserved` its number and name | Remove from properties; old readers that require it break |
| Rename field | Add the new one, keep the old; or use `aliases` for readers only | Add a new field number; never change a number | Add new, keep old, dual-write |
| Change type | Breaking, except allowed promotions such as int to long | Breaking, except compatible scalar groups | Breaking |
| Add enum value | Breaking for readers without an enum default | Safe if readers handle unknown values | Breaking for readers using closed `enum` |
| Make optional field required | Breaking | Not applicable in proto3 | Breaking |

## Rename procedure

1. Add the new field alongside the old, populated with the same value on every event.
2. Upgrade consumers to read the new field, falling back to the old.
3. Confirm through consumer versions that none read only the old field.
4. Stop writing the old field; keep it in the schema, reserved if protobuf.

## Split or merge of meaning

Treat as a new field with new semantics, never as a reinterpretation. A `status` split into `payment_status` and `fulfilment_status` adds two fields and keeps `status` frozen until retired.

## Retirement

For protobuf, mark the removed number and name `reserved` so they are never reused. For Avro, record the removed name in the schema documentation and never reintroduce it with a different type. In both, keep the field readable for as long as retained events carry it.
