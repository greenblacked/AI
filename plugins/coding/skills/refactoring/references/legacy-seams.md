# Refactoring code with no tests

## Contents

- [The order of operations](#the-order-of-operations)
- [Characterisation tests](#characterisation-tests)
- [Seam types and the smallest edit that introduces each](#seam-types-and-the-smallest-edit-that-introduces-each)
- [When the code cannot be instantiated at all](#when-the-code-cannot-be-instantiated-at-all)
- [Proving behaviour unchanged without a suite](#proving-behaviour-unchanged-without-a-suite)

## The order of operations

The trap is circular: the code cannot be tested until it is restructured, and it should not be restructured until it is tested. The way out is that a small class of edits is safe enough to make without tests, and those edits are exactly the ones that introduce a seam.

1. Characterise from the outside, at whatever boundary already exists — a CLI invocation, an HTTP endpoint, a function at the top of the module.
2. Make one seam edit, chosen from the table below, that is provably behaviour-preserving because every existing caller is untouched (a defaulted parameter, an extracted overridable method, a moved body).
3. Test through the seam.
4. Now refactor normally, in the small steps the main skill describes.

Never skip step 1 because step 2 looks trivial. The outside-in characterisation is what tells you the seam edit did not change anything.

## Characterisation tests

A characterisation test records what the code does, including behaviour you believe is wrong. Its purpose is a tripwire, not a specification.

Method:

1. Write a test that calls the code with realistic input and asserts something you know is false, such as equality with an empty string.
2. Run it, and read the actual value out of the failure message.
3. Paste that value into the assertion.
4. Repeat with input chosen to reach a different branch, using coverage to find the branches you have not reached yet — this is the one job coverage is genuinely good at.

Mark anything that looks like a defect with a comment naming it. Later, when someone decides to fix it, the test changes deliberately in a commit whose subject says so, rather than being adjusted to make a build pass.

Where the output is large or awkward — a rendered document, a serialised object, a sequence of log lines — record it to a committed file and compare. Approval-style tests are ideal here precisely because nobody has to understand the output to benefit from being told it changed.

## Seam types and the smallest edit that introduces each

| Obstacle | Seam | The edit, in full |
| --- | --- | --- |
| The code constructs its collaborators internally | Constructor or parameter injection | Add a parameter whose default is the current construction expression. Every caller compiles unchanged, and the test passes a stub. |
| A module-level or static call sits in the middle of the logic | An overridable method | Extract the call into a method of its own and override it in a test subclass. It is ugly and it is temporary; it buys the test that lets you inject properly. |
| A function computes and writes in one pass | Separation of compute from effect | Extract the pure calculation into a new function the effectful one calls. Test the pure half immediately, which is usually where the complexity was. |
| The entry point is a script body | A callable entry point | Move the body into `def main(argv)` and have the script call it. Nothing else in the commit. |
| Behaviour depends on environment variables read at import time | Read at call time, from a passed-in mapping | Change the read site to a parameter defaulting to `os.environ`. The default preserves behaviour exactly. |
| A dependency is a hard-coded network or database client | A narrow interface at the call site | Define an interface with only the methods actually used — typically two or three, not the client's forty — and pass the real client in. |
| Behaviour is selected by a global flag | Pass the flag | Thread it through as a parameter defaulting to the global. Delete the global once the last reader takes the parameter. |

Each of these is one commit, with the suite (or the manual check) run before and after. Introducing three seams in one commit forfeits the property that makes them safe.

## When the code cannot be instantiated at all

Some code resists every seam because construction pulls in the world — a constructor that opens a connection, a framework that only runs inside its container, a class with twelve constructor dependencies.

- **Subclass and stub** the construction: create a test-only subclass that overrides the expensive parts. It is the crudest technique available and it works when nothing else does.
- **Characterise at the process boundary** instead: run the binary or the container with fixed input and record stdout, exit code and the resulting state. Slow, but it requires no code change at all, so it is available before any edit.
- **Extract the logic to a new module** that the untestable class calls. The new module is testable from birth; the untestable shell shrinks with each extraction and eventually contains only wiring.

## Proving behaviour unchanged without a suite

- **Differential run.** Keep the old implementation under a different name, run both against a corpus of inputs — production samples where you can get them, generated ones where you cannot — and assert identical output. This is the strongest evidence available for a pure transformation, and it is cheap for parsers, serialisers, formatters and pricing logic.
- **Shadow traffic.** For a service, send a copy of real requests to both implementations and compare responses, logging differences rather than serving them. Run it for at least one full business cycle, because the request that differs is disproportionately likely to be a weekly or month-end shape.
- **Golden files.** Record outputs before the change, commit them, and diff after. Review every diff by hand; a golden file regenerated without reading is a rubber stamp.
- **Structural diff of the public surface.** List exported names and signatures before and after and diff the lists. This catches the accidental visibility change, which is the commonest unintended break in a move-heavy refactor.

Whichever you use, state it in the pull request. "Refactor, no behaviour change" without evidence is a claim; with a differential run over ten thousand recorded inputs it is a fact.
