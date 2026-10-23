# Walkthrough log

Read this at step 1, before the first clean-machine run.

## Contents

- Setup
- Log table
- What to count as a finding

## Setup

Use a fresh clone in an empty directory, on a clean container or account with only the operating system's standard tools plus what the README says. Record the operating system and architecture. Start a timer. Do not use remembered knowledge of the project; when you guess, write the guess down.

## Log table

| Step | Started | Finished | Commands or actions | Guesses or searches | Result |
| --- | --- | --- | --- | --- | --- |
| Find where to start | | | | | |
| Choose an issue | | | | | |
| Clone and build | | | | | |
| Run the tests (before editing) | | | | | |
| Change, push, open the PR | | | | | |
| First review received | | | | | |

## What to count as a finding

- A command that fails, or needs a tool the docs do not name.
- A version requirement stated nowhere, or stated differently in two files.
- A test that fails on a clean checkout.
- An issue with no scope, or one that depends on an unwritten decision.
- A wait longer than the stated response target.
- Any step where you opened a search engine.

Give each finding the step it occurred at, the minutes it cost, and the fix. Totals per step feed the ranking in step 6 of the skill.
