# The CI gate for samples

Read this at steps 4 to 6. The examples use GitHub Actions and a Python package called
`shop`; the shape carries to any CI and any language. Pin each action to a full commit
SHA with its exact release tag in a comment, as below, and replace the SHAs with the ones
your repository already uses.

## Contents

- [Released and main, on every change](#released-and-main-on-every-change)
- [The nightly run](#the-nightly-run)
- [The pasted-block lint](#the-pasted-block-lint)
- [Routing failures to owners](#routing-failures-to-owners)

## Released and main, on every change

```yaml
name: docs-samples
on:
  pull_request:
    paths: ["examples/**", "docs/**", "src/**", "pyproject.toml"]
  schedule:
    - cron: "17 4 * * *"
permissions:
  contents: read
jobs:
  samples:
    runs-on: ubuntu-latest
    timeout-minutes: 20
    strategy:
      fail-fast: false
      matrix:
        source: [released, main]
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          persist-credentials: false
      - uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97  # v7.0.0
        with:
          python-version: "3.12"
      - name: Install the package under test
        env:
          SOURCE: ${{ matrix.source }}
        run: |
          set -Eeuo pipefail
          if [ "$SOURCE" = released ]; then
            python -m pip install "shop==$(cat docs/PACKAGE_VERSION)"
          else
            python -m pip install .
          fi
      - name: Run samples and compare output
        env:
          SHOP_API_KEY: ${{ secrets.SHOP_SANDBOX_API_KEY }}
        run: |
          set -Eeuo pipefail
          python3 tools/run_samples.py examples/python
```

`tools/run_samples.py` is the expected-output runner from `include-and-assert.md`, kept
wherever the repository keeps its tooling. `fail-fast: false` keeps the released job running when main fails, because the two
failures mean different things: main failing is a change to fix before release, released
failing is a page wrong for readers today. `docs/PACKAGE_VERSION` is whatever file your
docs build already reads the advertised version from; pin to it rather than to "latest",
so the job tests the version the page claims.

Secrets are not passed to workflows triggered from forks, so on a fork's pull request
`SHOP_API_KEY` is empty and, as written above, every sandbox sample runs and fails. Add
the split before accepting fork contributions: run the sandbox samples only when the pull
request's head repository is this one, run the samples that need no sandbox everywhere,
and print a visible notice on a fork that the sandbox set was skipped. The nightly run and
the post-merge run cover what a fork skips.

## The nightly run

The `schedule` trigger above runs both matrix legs against the default branch every
night. It exists for samples that call a hosted service, which can change with no commit
here, and for dependencies a sample installs without a lock. Stagger the minute away from
the hour, when scheduled jobs queue up.

## The pasted-block lint

Run on every pull request that touches the docs. It fails on a fenced block in a runnable
language whose body is code rather than an include directive. Blocks in `text`,
`console`-output or other non-runnable info strings pass, which is how the pseudo-code
label works. A bare fence fails, so a pasted program cannot hide without a label, and
every non-runnable block is counted by info string, so relabelling shows up as a count
moving between `text`, `sh` and `console`. Give a bare fence that holds output a
`text` label rather than exempting it.

```python
#!/usr/bin/env python3
"""Fail on pasted runnable code blocks in Markdown docs."""

import re
import sys
from pathlib import Path

RUNNABLE = {
    "python",
    "py",
    "go",
    "rust",
    "rs",
    "js",
    "javascript",
    "ts",
    "typescript",
    "java",
    "kotlin",
    "csharp",
    "cs",
    "ruby",
    "rb",
    "php",
    "swift",
}
INCLUDE = re.compile(r"^\s*(--8<--|\{\{#(rustdoc_)?include|include::)")
# Any indent: fences inside list items and admonitions sit four or more spaces in.
OPEN = re.compile(r"^(\s*)(`{3,}|~{3,})\s*([\w+-]*)")

pasted, labels, bare = [], {}, []
docs_root = Path(sys.argv[1])
pages = sorted(p for ext in ("*.md", "*.mdx") for p in docs_root.rglob(ext))
# A mistyped path finds no pages and would stay green forever.
if not docs_root.is_dir() or not pages:
    print(f"nothing checked: {docs_root} is not a directory or holds no pages")
    sys.exit(1)
for page in pages:
    lines = page.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        m = OPEN.match(lines[i])
        if not m:
            i += 1
            continue
        fence, lang, start = m.group(2), m.group(3).lower(), i
        body = []
        i += 1
        while i < len(lines) and not lines[i].strip().startswith(fence):
            body.append(lines[i])
            i += 1
        i += 1
        code = [b for b in body if b.strip()]
        if lang in RUNNABLE and code and not all(INCLUDE.match(b) for b in code):
            pasted.append(f"{page}:{start + 1}: pasted {lang} block")
        elif lang not in RUNNABLE and code and not all(INCLUDE.match(b) for b in code):
            labels[lang] = labels.get(lang, 0) + 1
            if not lang:
                bare.append(f"{page}:{start + 1}: bare fence")

print("\n".join(pasted + bare))
print(f"{len(pasted)} pasted runnable blocks, {len(bare)} bare fences")
print("other blocks by info string:", dict(sorted(labels.items())))
sys.exit(1 if pasted or bare else 0)
```

The fence pattern accepts any indent and the page glob includes `.mdx`, because a pasted block
inside a list item, an admonition or an MDX page would otherwise pass unseen. Extend `RUNNABLE` to the languages your docs use and `INCLUDE` to your toolchain's
directive. For reStructuredText, flag `.. code-block::` and `.. code::` directives in a
runnable language the same way; `literalinclude` is the passing form. The same lint
counts blocks for the coverage number in step 7.

Introduce it with the current pasted blocks listed in a baseline file the lint subtracts,
and shrink that file with each conversion. A lint that fails on day one on two hundred
existing blocks gets disabled the same week.

## Routing failures to owners

`CODEOWNERS` routes pull-request reviews, so a sample change already reaches its owning
team. A nightly failure has no pull request, so route it explicitly:

- One issue per failing sample, found by a stable title such as
  `Docs sample failing: examples/python/list_orders.py`, updated rather than duplicated
  on each failing night, and closed by the job when the sample passes again.
- Label it with the sample's area and mention the owning team named in `CODEOWNERS`.
  Issues cannot be assigned to a team, only to people, so the mention is what notifies.
- The step that files issues needs `issues: write` and nothing else; give it to that
  job alone rather than to the whole workflow.
- Record the first failing date in the issue body. That date drives the expiry in step
  6: past the agreed window, the owner fixes the sample or relabels it as illustrative.
