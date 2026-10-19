# The test-first loop for a coding agent

## Contents

- [Why an agent needs the red run](#why-an-agent-needs-the-red-run)
- [The loop](#the-loop)
- [Reading the red run](#reading-the-red-run)
- [Editing a test](#editing-a-test)
- [A bug fix](#a-bug-fix)
- [When test-first is the wrong tool](#when-test-first-is-the-wrong-tool)
- [Sources](#sources)

## Why an agent needs the red run

A passing test is evidence only if you have seen the same test fail. An agent that writes the code and then a test for it has produced a test that agrees with the code, and "the tests pass" in its report then means nothing a reviewer can use. The red run is the proof that the test can tell the difference, so it is the step to protect when time is short.

The cycle is Kent Beck's: a small failing test, the least change that passes it, then clean-up with the tests green (*Test-Driven Development: By Example*). The rest of this file is that cycle adapted to a session where you cannot ask what was meant and a reviewer reads only what you report.

## The loop

1. **Turn one acceptance criterion into one test.** Name it from the criterion, in the caller's terms (`rejects_a_transfer_that_would_overdraw`). If the criterion needs two assertions about unrelated things, it is two criteria. Pick the order so each test asks for a small step; write down the remaining criteria as a list and take them one at a time.
2. **Run that test alone and confirm it fails for the expected reason.** Read the failure message, not only the exit code. See the next section.
3. **Make the smallest change that turns it green.** Do not add the branch the next criterion will need; that criterion has no test yet. When the right shape is unclear, returning the expected constant and letting a second test force the general rule is a legitimate step, and the one Beck calls triangulation.
4. **Rerun the single test, then the whole suite.** A green file is not a green suite. Run the project's own test command even when the task named one file, and list any failure by name in your report, including one you did not cause.
5. **Refactor only while green.** Rename, extract, remove duplication, rerunning after each step. If a refactor needs a new assertion, you changed behaviour; stop and go back to step 1.
6. **Take the next criterion.**

Run a single test with the runner's own selector: `pytest path/to/test_file.py::test_name`, `go test -run TestName ./pkg`, or `npx jest path/to/file.test.js -t "name"`.

The `superpowers` test-driven-development skill goes further and deletes any production code written before its test. The part worth keeping is the evidence, not the ritual. If you wrote the code first, write the test now, revert the change locally, and watch the test fail for the expected reason before restoring it.

## Reading the red run

| What you see | What it means | Next |
| --- | --- | --- |
| A syntax, import or collection error; a missing fixture | The test is broken, not failing | Fix the test until it runs and fails on an assertion |
| It passes at once | It exercises behaviour that already exists, or the wrong target | Fix the test; do not write code |
| It fails on a different assertion from the one you intended | The test checks something else | Correct the test or the criterion |
| It fails with the message you expected, because the behaviour is absent | A true red | Write the change |

A `NameError` or `AttributeError` for the function you have not written yet is a legitimate red only when the test is calling the interface you intend to ship. Add the empty function with the right signature and rerun, so the next failure is the assertion rather than a missing name.

## Editing a test

A test changes for exactly two reasons: the requirement changed, or the test was wrong. Say which, in the report and the commit, with the old and new assertion. Do not loosen an assertion, widen a tolerance, add a skip or delete a case because the code does not meet it; that turns the check into a copy of the current behaviour, and it is the quickest way for an agent to make a failing task look finished.

When the output differs from what the test expects, decide first which is right. Only then edit one of them. After a legitimate test edit, repeat the red run against the code without your change, because the earlier red no longer describes the test you are about to rely on.

## A bug fix

`SKILL.md` step 8 sets the order. Four additions for an agent working from a report:

- The red run must show the reporter's symptom. A different failure means you reproduced a different bug; keep it for a separate test and keep looking.
- If you cannot make it fail, stop and say so. A fix shipped on a reproduction that never went red is a guess with a test attached.
- Keep the test and the fix in one commit, so no commit on the branch is red.
- Confirm the fix by the same test, then the suite. Do not describe the bug as fixed on the strength of a manual run.

## When test-first is the wrong tool

- **An exploratory spike.** When you do not yet know the shape of the answer, a test written first only encodes a guess. Spike freely, throw the spike away, and write the real thing test-first from what you learned. Say in the report that the code is a rewrite, not the spike.
- **Visual layout.** Alignment, spacing and rendering are judged by looking, and a test on pixel positions pins the implementation. Check them in a browser or a screenshot review (`e2e-testing` owns the end-to-end side), and still write the logic behind the screen, such as which state shows which element, test-first.
- **Generated code and configuration.** The generator's own tests are the place to prove behaviour; a test over its output restates it.
- **Code that already exists without tests.** Tests written afterwards pin what it does, not what it should do. That is a characterisation test, which is a different task and belongs with `refactoring`.

Whenever you skip the loop, say that you did and why. The cost of skipping is the missing evidence, and the reviewer should know it is missing.

## Sources

- Kent Beck, *Test-Driven Development: By Example*, Addison-Wesley, 2002: the cycle and triangulation.
- `skills/test-driven-development/SKILL.md` in the `obra/superpowers` repository, read on 2026-10-19: the rule to confirm the failure is the expected one, the instruction to run the project's whole suite and name every failure, and the position that exploration is thrown away before building test-first.
