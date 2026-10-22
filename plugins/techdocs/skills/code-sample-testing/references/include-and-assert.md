# Including regions and asserting output

Read this at step 2 to wire includes into the docs toolchain, and at step 3 to choose how
each language's output is checked. The pattern is the same everywhere: the sample file is
the source, a named region is what the page shows, and the whole file is what CI runs.

## Contents

- [Region includes by docs toolchain](#region-includes-by-docs-toolchain)
- [Output assertion by language](#output-assertion-by-language)
- [The expected-output runner](#the-expected-output-runner)
- [Normalising volatile output](#normalising-volatile-output)

## Region includes by docs toolchain

Make the build fail when an include points at a missing file or region. A silent empty
code block is the pasted-snippet failure in a new form.

**MkDocs with pymdown-extensions snippets.** Mark the region in the source with
`# --8<-- [start:list]` and `# --8<-- [end:list]` (using the language's comment
character), then in the page:

````markdown
```python
--8<-- "examples/python/list_orders.py:list"
```
````

Set `check_paths: true` under `pymdownx.snippets` in `mkdocs.yml` so a missing file fails
the build, and set `base_path` to the repository root so paths read the same in every
page.

**Sphinx**, in reStructuredText or MyST:

```rst
.. literalinclude:: ../examples/python/list_orders.py
   :language: python
   :start-after: [start:list]
   :end-before: [end:list]
   :dedent:
```

`literalinclude` can also select by `:pyobject:` for a Python function or class, and by
`:lines:`. Prefer markers over line numbers: line numbers move with every edit above them
and nothing notices.

**Asciidoctor and Antora.** Tag the source with `# tag::list[]` and `# end::list[]`, then
`include::example$list_orders.py[tag=list]` in Antora or a relative path with
`[tag=list]` in plain Asciidoctor.

**mdBook.** Mark with `// ANCHOR: list` and `// ANCHOR_END: list`, then
`{{#include ../examples/list_orders.rs:list}}`. For Rust samples, `{{#rustdoc_include}}`
keeps the rest of the file available as hidden lines so `mdbook test` can run it.

**Docusaurus and other MDX sites.** The documented route imports a whole file as a raw
string and renders it with the theme's code block component:

```jsx
import CodeBlock from '@theme/CodeBlock';
import ListOrders from '!!raw-loader!@site/examples/js/list-orders.js';

<CodeBlock language="js">{ListOrders}</CodeBlock>
```

That shows the whole file, so keep each MDX-included sample to exactly what the reader
should see and put the scaffolding (client set-up, credentials) in a separate module the
sample imports. Region-extraction plugins exist; check one is maintained before adopting
it.

## Output assertion by language

| Language | Mechanism | How the assertion is written |
| --- | --- | --- |
| Go | `Example` functions run by `go test` | A trailing `// Output:` comment with the exact expected lines, or `// Unordered output:` where order is not guaranteed. An example with no output comment is compiled but not run |
| Python, REPL style | `doctest` | `>>>` lines followed by the expected output. `pytest --doctest-glob='*.md'` runs them inside Markdown; `python -m doctest file.md` without pytest |
| Python, script style | Expected-output file | Run the script, compare stdout with the committed `.out` file, as below |
| Rust | Doc tests | `cargo test --doc` for crate docs, `mdbook test` for a book. Assert inside the sample with `assert_eq!`, and hide set-up lines from the reader with a leading `#` and a space |
| TypeScript | Type-check, then run | `npx tsc --noEmit -p examples/ts` catches the renamed-parameter class of break on its own; run the compiled output and compare with the `.out` file for behaviour |
| Java, C#, others | Build as a project, run, compare | One small project per sample set, built with the reader's build tool, run, and compared with the `.out` file |
| Shell | Run in a container, compare | Treat each command block as a script; where a command changes the system, it belongs in a `tutorial-clean-room` replay instead |

For HTTP examples shown as `curl` commands, run the command against the sandbox and assert
on the status and the fields the page names, not the full body: the body is long, carries
volatile values, and the page only promises a few fields.

## The expected-output runner

A minimal runner for samples without a native mechanism. Each sample `foo.py` (or any
extension) has a sibling `foo.out`, and a `samples.json` maps extension to command.

```python
#!/usr/bin/env python3
"""Run every sample that has a .out file and diff its normalised stdout."""

import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
commands = json.loads((root / "samples.json").read_text())  # {".py": ["python3"], ".js": ["node"]}
masks = [(re.compile(p), r) for p, r in json.loads((root / "masks.json").read_text())]
failed = 0

# A wrong root or an empty one runs nothing and would stay green.
if not any(p.suffix in commands for p in root.rglob("*")):
    print(f"nothing checked: no samples under {root}")
    sys.exit(1)

# A sample with no .out file would never run and the job would stay green, so list them.
# Helper modules the samples import start with an underscore and are skipped.
for source in sorted(
    p for p in root.rglob("*") if p.suffix in commands and not p.name.startswith("_")
):
    if not source.with_suffix(".out").exists():
        print(f"NO EXPECTED OUTPUT {source}")
        failed += 1

for expected in sorted(root.rglob("*.out")):
    source = next(
        (s for s in expected.parent.glob(expected.stem + ".*") if s.suffix in commands), None
    )
    if source is None:
        print(f"NO SOURCE {expected}")
        failed += 1
        continue
    run = subprocess.run(
        commands[source.suffix] + [str(source)], capture_output=True, text=True, timeout=120
    )
    actual = run.stdout
    for pattern, replacement in masks:
        actual = pattern.sub(replacement, actual)
    if run.returncode != 0 or actual != expected.read_text():
        failed += 1
        print(f"FAIL {source} (exit {run.returncode})")
        sys.stdout.writelines(
            difflib.unified_diff(
                expected.read_text().splitlines(True), actual.splitlines(True), "expected", "actual"
            )
        )
        print(run.stderr[-2000:])

sys.exit(1 if failed else 0)
```

To create or refresh a `.out` file, run the sample, read the output as a reviewer would,
and commit it in the same pull request as the code change that altered it. A `.out` diff
in review is the moment someone notices the behaviour change the page now documents.

## Normalising volatile output

`masks.json` is a list of `[pattern, replacement]` pairs applied before comparison, and
the `.out` file is written with the replacements already in it:

```json
[
  ["ord_[A-Za-z0-9]{12}", "ord_<id>"],
  ["\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z", "<timestamp>"],
  ["took \\d+ ms", "took <n> ms"]
]
```

Mask the shape of a value, never the whole line. A mask such as `".*"` passes any output,
which turns the check back into an exit-code test. Review a new mask the way you would
review a deleted assertion.

Where order is not guaranteed (a listing from an API), sort in the sample before printing
rather than masking order away, and say so on the page if the reader's output may differ.
