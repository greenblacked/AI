# README template

## Contents

- Template
- Worked example
- Pre-submission checklist

## Template

```text
# <Project name>

One sentence on what this does and the assumptions made where the brief was silent, including whether assistance or code-generation tools were used and how the employer's rules were read.

## How to run
Requires: <language and version>
Install:  <command>
Run:      <command>
Test:     <command>

## Key decisions
1. <Decision>: chose X over Y because <reason>. Cost: <what this gives up>.
2. ...
3. ...

## What was cut
- <Item>: <why it was left out and what it would take>

## With another day
1. <Item>, about <estimate>, because <value>
2. ...
```

## Worked example

Exercise: a small service that ingests transactions and reports totals per category, four hours.

- Key decision 1: stored transactions in memory behind a repository interface, rather than a database, because persistence was out of scope and the interface keeps the swap cheap. Cost: data is lost on restart.
- Key decision 2: validated at the boundary and returned a typed error, rather than raising from deep inside, so failure paths are testable.
- Key decision 3: tested the aggregation and the validation paths; did not test the HTTP wiring beyond one smoke test.
- Cut: authentication, pagination, concurrency control, Docker packaging.
- Another day: persistence with migrations, then pagination, then structured logging.

## Pre-submission checklist

1. Fresh clone into an empty directory; follow the README literally; it runs and the tests pass.
2. No secrets, local paths or editor files committed.
3. Language version and dependency versions stated or pinned.
4. Commit history reads in order.
5. Time spent, stated honestly if asked.
6. The cut list matches what is actually missing.
7. Any use of assistance or code-generation tools matches what the employer permits and, where asked, is disclosed.
