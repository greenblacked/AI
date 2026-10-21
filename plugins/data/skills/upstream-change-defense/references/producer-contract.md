# Producer contract

## Contents

- What to ask for, and in what order
- Contract template
- The semantic section
- Compatibility checks in the producer's CI
- Which compatibility mode a warehouse consumer needs
- Change notice

## What to ask for, and in what order

1. A named contact on each side and one channel for change notices. This costs the producer nothing and prevents most surprises, so ask for it first.
2. A contract file in the producer's repository, reviewed by both sides when it changes.
3. A check in the producer's CI that fails a breaking change to the contract.

Asking for the CI check first, before there is a contract or a relationship, usually gets a polite no. Arriving with the list of past incidents from step 1 of the skill, and their cost, is what moves the conversation.

## Contract template

```yaml
source: orders
owner:
  team: checkout
  contact: named person, and the team channel
consumers:
  - team: analytics engineering
    contact: named person
delivery:
  mechanism: replicated table app.orders
  schedule: continuous, at most 15 minutes behind
fields:
  - name: order_id
    type: string
    required: true
    unique: true
  - name: status
    type: string
    required: true
    allowed_values: [pending, paid, shipped, cancelled, refunded]
    meaning: lifecycle state at the time of the row's last update
  - name: amount
    type: integer
    required: true
    unit: minor units of the currency in `currency`
  - name: currency
    type: string
    required: true
    format: ISO 4217 alphabetic code
  - name: created_at
    type: timestamp
    required: true
    time_zone: UTC, with offset suffix
  - name: customer_id
    type: string
    required: false
    null_means: guest checkout, no customer account
change_policy:
  notice_period: two weeks for any change listed under breaking
  breaking:
    - removing or renaming a field
    - changing a type, unit, time zone or the meaning of a field
    - adding a value to allowed_values
    - changing what null means
  additive:
    - adding a new optional field
```

Adding an allowed value is listed as breaking on purpose: every downstream `case` statement over that field has an `else` branch that will silently absorb it.

## The semantic section

Schema tools check names and types. They cannot see these, so the contract must say them in words and both sides must review a change to them:

- Allowed values of every enum, and what each means.
- Units and currency of every amount and quantity.
- Time zone of every timestamp, and whether an offset is present.
- What null means, field by field, and whether absent and null differ.
- When the record is written: at creation, on every update, or at the end of a process.
- Whether ids are stable, and whether a deleted id can be reused.

## Compatibility checks in the producer's CI

| Producer format | Check | Notes |
| --- | --- | --- |
| Protobuf | `buf breaking --against '.git#branch=main'` | Fails on changes that break the configured rule category against the main branch: `FILE` by default, `WIRE` or `WIRE_JSON` when only the encoding matters |
| Avro, JSON Schema or Protobuf with a schema registry | The registry's compatibility test: Confluent Schema Registry exposes `POST /compatibility/subjects/{subject}/versions/latest` | Set the subject's compatibility mode first; the test applies that mode |
| Producer's own dbt models | Model contracts with `contract: {enforced: true}`, and model versions for breaking changes | Enforces the shape of their output at build time |
| Database table replicated to the warehouse | A CI step that diffs the contract file against the migration's resulting schema | Usually a short script in their repository; the migration review is where it belongs |

Each catches structural change only. The semantic section and the notice period cover the rest.

## Which compatibility mode a warehouse consumer needs

Confluent Schema Registry modes, read from the warehouse's side:

| Mode | Guarantees | What it means here |
| --- | --- | --- |
| `BACKWARD` (registry default) | Consumers on the new schema can read data written with the previous one | The parser can be updated first; does not protect a parser that has not been updated yet |
| `FORWARD` | Consumers on the previous schema can read data written with the new one | The producer can ship first without breaking the current parser |
| `FULL` | Both, against the previous version | Either side can move first |
| `*_TRANSITIVE` variants | The same, against every earlier version, not only the previous one | Needed for replay from raw, where the current parser reads batches landed under every old version |
| `NONE` | Nothing checked | Every change is a potential incident |

A warehouse that lands raw and replays wants `FULL_TRANSITIVE`: the current parser must read everything ever landed, and the existing parser must survive a new producer version until it is updated. If the producer will accept only one direction, ask for `FORWARD_TRANSITIVE`, which protects the running parser from a new producer version, and make replay of old batches version-aware by recording the writer's schema id on every landed row.

## Change notice

A change notice names the source, the fields, the class of change (structural or semantic), the date it ships, how to tell old rows from new (a version field, or a cut-over timestamp), and the producer contact. The cut-over marker is what makes a unit or meaning change fixable on replay: the parsing model converts rows before the marker one way and after it the other.
