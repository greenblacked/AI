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


def frontmatter(name: str) -> dict[str, str]:
    block = agent(name).split("---\n", 2)[1]
    return dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)


def test_every_agent_ships_the_tier_stage_tiering_states():
    # stage-tiering says each agent's tier is written in its own file; with no `model`
    # line the survey stages silently run on the main conversation's top-tier model.
    skill = (FAMILY / "skills" / "stage-tiering" / "SKILL.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| \w+ \| `(\w+)` \| (mid|top) \| ([\w ]+?) \|", skill, re.M)
    assert {row[0] for row in rows} == set(AGENTS), rows
    alias = {"mid": "sonnet", "top": "opus"}
    for name, tier, effort in rows:
        fields = frontmatter(name)
        assert fields.get("model") == alias[tier], (name, fields)
        expected = None if effort == "tool default" else effort
        assert fields.get("effort") == expected, (name, fields)


def test_stage_tiering_does_not_edit_the_installed_plugin():
    skill = (FAMILY / "skills" / "stage-tiering" / "SKILL.md").read_text(encoding="utf-8")
    tools = re.search(r"^allowed-tools: (.+)$", skill, re.M).group(1)
    assert "Edit" not in [tool.strip() for tool in tools.split(",")], tools


def test_no_skill_calls_an_agent_with_bash_read_only():
    # inspector holds unrestricted Bash, which can write; "no editing tools" is the
    # accurate claim for the stage agents as a set.
    assert "Bash" in frontmatter("inspector")["tools"]
    workflow = FAMILY / "skills" / "family-workflow"
    for path in [workflow / "SKILL.md", *sorted((workflow / "references").glob("*.md"))]:
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"(?:agents are|inspector`? is|, and) read-only", text), path


def test_an_unscoped_agent_grant_says_why_in_the_body():
    # Every other family skill names the agents it may start; one that does not has to
    # say why, or the grant reads as an oversight.
    for skill in sorted((FAMILY / "skills").glob("*/SKILL.md")):
        text = skill.read_text(encoding="utf-8")
        tools = re.search(r"^allowed-tools: (.+)$", text, re.M).group(1)
        if "Agent" in [tool.strip() for tool in tools.split(",")]:
            assert "unscoped on purpose" in text, skill
            # A Bash-holding research agent can write through the shell, so the
            # missing editing tools alone do not make it read-only.
            assert "`Bash`" in text.split("unscoped on purpose", 1)[1][:600], skill


VERDICT_LINE = re.compile(r"^[A-Z][A-Z -]*(?: \| [A-Z][A-Z -]*)+$")


def test_every_copied_return_block_matches_its_agent():
    # A skill reference that reproduces an agent's return block drifts when the agent
    # file changes; round-protocol.md kept the inspector's block without its Handoff.
    blocks = {block.splitlines()[0]: block for name in AGENTS for block in return_blocks(name)}
    copies = 0
    for path in sorted((FAMILY / "skills").rglob("*.md")):
        for block in re.findall(r"```text\n(.*?)```", path.read_text(encoding="utf-8"), re.S):
            first = block.splitlines()[0]
            if VERDICT_LINE.match(first) and first in blocks:
                copies += 1
                assert block == blocks[first], path
    assert copies, "no reference copies an agent's return block"


def test_the_claim_brief_forbids_writing_as_the_skill_says_it_does():
    # frame-claim-ledger says the brief forbids writes to a Bash-holding agent; the
    # brief itself has to carry that rule, or the claim is only in the skill.
    root = FAMILY / "skills" / "frame-claim-ledger"
    brief = (root / "references" / "claim-brief.md").read_text(encoding="utf-8")
    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    rule = re.search(r"^- \*\*The rule on writing\*\*: (.+)$", brief, re.M)
    assert rule, "claim-brief.md has no rule on writing"
    for phrase in ("writes no file", "changes the checkout", "read-only commands only"):
        assert phrase in rule.group(1), phrase
    assert "the brief says it writes no file and runs nothing that changes the checkout" in skill
