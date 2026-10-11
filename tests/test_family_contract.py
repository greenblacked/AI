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
