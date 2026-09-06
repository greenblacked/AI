"""Regenerate block_scalars.json from PyYAML.

The validator's YAML subset is measured against a real parser, and this is where the
measurement is taken: every indicator crossed with every body below is resolved by
PyYAML and by ``skillcheck.frontmatter``, and the fixture is only written when the two
agree on all of them. PyYAML is deliberately not a dependency of the validator, so this
script is the one place it is imported, and the recorded answers are what the test
suite replays. Run it from the repository root after installing ``pyyaml``:

    python tests/fixtures/generate_block_scalars.py
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from skillcheck.frontmatter import _block_scalar  # noqa: E402

bodies = [
    ["  one", "  two"],
    ["  one", "", "  two"],
    ["  one", "", "", "  two"],
    ["  one", "    more", "  two"],
    ["  one", "", "    more", "", "  two"],
    ["  one", "    more", "    more2", "  two"],
    ["  one", "  two", ""],
    ["  one", "  two", "", ""],
    ["  trailing space ", "  two"],
    ["  one", "    more", ""],
    ["  only"],
    [""],
    ["", ""],
    ["  one", "  ", "  two"],
    ["  one", "      ", "  two"],
    ["  a", "    b", "", "    c", "  d"],
    ["  a", "", "    b"],
]
indicators = [">", ">-", ">+", "|", "|-", "|+"]
cases: list[dict] = []
bad: list[tuple] = []
for ind, body in itertools.product(indicators, bodies):
    doc = "key: " + ind + "\n" + "\n".join(body) + "\n"
    expected = yaml.safe_load(doc)["key"]
    got = _block_scalar(ind, body)
    cases.append({"indicator": ind, "lines": body, "expected": expected})
    if got != expected:
        bad.append((ind, body, expected, got))
print(f"{len(cases)} cases generated, {len(bad)} disagreements")
for b in bad:
    print(" ", b)
if bad:
    sys.exit(1)
out = Path(__file__).with_name("block_scalars.json")
out.write_text(json.dumps(cases, indent=1) + "\n", encoding="utf-8")
print("wrote", out)
