# The operations, with preconditions and checks

## Contents

- [Rename](#rename)
- [Extract function or variable](#extract-function-or-variable)
- [Inline](#inline)
- [Move](#move)
- [Split a module](#split-a-module)
- [Break a dependency cycle](#break-a-dependency-cycle)
- [Replace a conditional](#replace-a-conditional)
- [Change a signature](#change-a-signature)

Each operation below states what must be true before starting, the mechanical steps, and the check that proves the step was safe. Run the suite after every operation, and commit before starting the next.

## Rename

**Precondition:** the new name is accurate for what the thing does now, not for what you intend it to do after the refactor. Renaming to the future name leaves the code lying until the rest lands.

**Steps:** use the language server or IDE rename, which resolves references rather than matching text. Where none exists, list occurrences with `rg -w '\boldName\b'`, review each, and edit deliberately — then search once more for the name in strings, serialised data, database columns, configuration keys and documentation, because those are where a rename leaks out of the codebase and becomes a behaviour change.

**Check:** the diff contains no line where the surrounding logic changed. A rename commit where one hunk looks different is a rename commit with a bug in it.

**Public names** need the parallel-change treatment: keep an alias delegating to the new name, deprecate it with a date, delete it when the callers are gone. A rename of a widely-imported symbol in one commit conflicts with every open branch.

## Extract function or variable

**Precondition:** the block being extracted has a name — a concept someone would recognise. Extraction purely to reduce line count produces functions called once with eight parameters.

**Steps:** identify the block, identify the variables it reads (parameters) and writes (return values). If it writes more than one variable used afterwards, extract a smaller block or return a small structure; a function with three out-parameters is harder to read than the code it replaced. Extract, call it from the original site, and leave the body byte-identical in the first commit.

**Check:** the caller's diff is a deletion of the block and one call. If the extracted body differs from the deleted lines by anything other than indentation and the parameter names, you changed behaviour in an extraction commit.

**Extract variable** is the same operation for an expression: name a subexpression, then use it. It is the cheapest way to make a dense condition readable, and it is safe as long as the expression has no side effects and the evaluation order does not change — which is exactly the case that catches people out in short-circuited boolean chains.

## Inline

**Precondition:** the indirection buys nothing — a function whose body is as clear as its name, a variable used once, a delegation that adds no meaning.

**Steps:** replace every call with the body, adjusting names. Then delete the definition and search for remaining references, including dynamic ones (reflection, string-keyed dispatch, test doubles), which the compiler will not find.

**Check:** the symbol no longer appears anywhere, including in tests and configuration. Inlining is the operation most likely to leave an unused private helper behind; delete it in the same commit.

## Move

**Precondition:** the thing being moved is already correctly named and self-contained — it does not reach back into the module it is leaving.

**Steps:** move, fix imports, change nothing else. If the move requires an edit to the body, that edit is a separate commit before or after, never during.

**Check:** `git diff -M --stat` reports a rename or a high similarity index. Deletions plus additions of similar size mean git could not match them, which usually means the body changed.

## Split a module

**Precondition:** the pieces are already extracted and named, and you can state what each new module owns in one sentence. A split before the extraction produces two modules importing each other.

**Steps:** group the members by what they know about, not by kind — a module of "all the validators" from across three domains is a worse module than one per domain. Create the new module, move one group, fix imports, run the suite, commit. Repeat per group. Leave the original module as the public surface re-exporting the moved names until callers migrate.

**Check:** the import graph after the split is acyclic, and the new module's import list is shorter than the original's. A split that leaves both halves importing everything did not separate anything.

## Break a dependency cycle

Three techniques, in order of preference:

1. **Extract the shared thing into a third module.** Usually the cycle exists because both modules need one type or constant. Move it to a leaf module with no dependencies of its own. This is the right answer far more often than the other two.
2. **Invert the dependency.** Define the interface in the consumer, implement it in the provider. The provider now depends on the consumer's interface and the arrow has turned round.
3. **Merge the two modules.** If every attempt to separate them fails, they may genuinely be one concept that was split by file size rather than by responsibility.

Deferring an import inside a function body removes the tool's warning and leaves the cycle in place, moving the failure from import time to the first call at runtime. Treat it as a temporary measure with a follow-up, not as a fix.

**Check:** run the cycle detector (`import-linter` or `pydeps` in Python, `madge` in JavaScript, `go list` with a graph tool) and see the cycle gone from the report, rather than inferring it from the code.

## Replace a conditional

**Precondition:** the branches are already extracted into functions with identical signatures, and there are at least three of them. Two branches are an `if`, and turning an `if` into a class hierarchy is a cost with no return.

**Steps:** choose the target shape by what varies. A dispatch table (a map from key to function) suits branching on a value with no shared state. Polymorphism suits branching on a type where each branch also carries data. A guard-clause flattening suits a deeply nested conditional where the branches are not parallel at all — and it is often the whole fix.

**Check:** every branch of the original is reachable in the new shape, and the default or unknown-key case is explicit. The commonest defect here is a dispatch table that silently returns nothing for a key the old `else` handled.

## Change a signature

The riskiest operation, because callers you do not compile against will not tell you. Do it in phases: add the new parameter with a default that preserves current behaviour; migrate callers in separate commits; make it required last, once no caller omits it. For a public API, each phase is a release, and the removal of the old form is a major version.

**Check:** search for dynamic call sites — reflection, serialised call records, RPC stubs, test doubles that implement the same interface — before making anything required. The type checker sees none of them.
