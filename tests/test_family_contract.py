"""The `family` plugin's skills make promises about its six stage agents; these hold them to it.

Every case here was a review finding: a skill that relied on a section, a setting or a
definition an agent file did not carry. Nothing else reads both sides together.
"""

from __future__ import annotations

import re

import pytest

from tests.conftest import REPO

FAMILY = REPO / "plugins" / "family"
AGENTS = ("framer", "architect", "maker", "inspector", "launcher", "yielder")


def agent(name: str) -> str:
    return (FAMILY / "agents" / f"{name}.md").read_text(encoding="utf-8")


def return_blocks(name: str) -> list[str]:
    text = agent(name)
    return re.findall(r"```text\n(.*?)```", text.split("## Return", 1)[1], re.S)


@pytest.mark.parametrize("name", AGENTS)
def test_every_return_block_ends_with_the_handoff_the_relay_passes_on(name):
    # family-relay passes the next hop "only the previous report's Handoff section".
    blocks = return_blocks(name)
    assert blocks, name
    for block in blocks:
        assert "### Handoff" in block, (name, block)


def test_stop_means_what_the_inspector_says_it_means():
    # inspector.md defines STOP as "no success criterion"; a skill that reads it as "found
    # something only a person can weigh" or "no checkout it may read" routes it wrongly.
    assert "frame supplied no success criterion" in agent("inspector")
    skills = FAMILY / "skills"
    routing = (skills / "family-relay" / "references" / "routing.md").read_text(encoding="utf-8")
    rounds = (skills / "fresh-inspector-rounds" / "references" / "round-protocol.md").read_text(
        encoding="utf-8"
    )
    stop_rows = [line for line in routing.splitlines() if "inspector" in line and "`STOP`" in line]
    assert stop_rows and all("success criterion" in row for row in stop_rows), stop_rows
    stop_line = next(line for line in rounds.splitlines() if line.startswith("- `STOP`"))
    assert "no success criterion" in stop_line and "checkout" not in stop_line, stop_line
