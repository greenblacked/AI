"""The Copilot wrappers, which copy rules from files Claude Code reads.

A wrapper restates its source's key rules inline, so it is a copy that goes stale without
any error: edit a rule and the Copilot text keeps saying the old thing. These cases are the
ways that happens, plus the real tree, which has to stay in step with its own sources.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from tests.conftest import REPO, load_script

copilot = load_script("check_copilot.py")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_pair(root: Path, source: str, wrapper: str, text: str = "Rule one.\n") -> Path:
    """A source and the wrapper that mirrors it, with the hash recorded correctly."""
    src = root / source
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(text, encoding="utf-8")
    out = root / wrapper
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        f"---\ndescription: A wrapper.\n---\n<!-- source: {source} sha256: {digest(src)} -->\n\n"
        "Inline rule.\n",
        encoding="utf-8",
    )
    return out


def test_wrappers_in_step_with_their_sources_pass(tmp_path, capsys):
    write_pair(tmp_path, ".claude/rules/skills.md", ".github/instructions/skills.instructions.md")
    write_pair(tmp_path, "REVIEW.md", ".github/instructions/review.instructions.md")
    write_pair(tmp_path, ".claude/agents/explorer.md", ".github/agents/explorer.agent.md")
    write_pair(tmp_path, ".claude/commands/ship.md", ".github/prompts/ship.prompt.md")
    assert copilot.check(tmp_path) == 0
    assert "4 Copilot wrapper(s) match their sources; 4 source(s) covered" in (
        capsys.readouterr().out
    )


def test_a_tree_with_nothing_to_mirror_passes(tmp_path):
    (tmp_path / ".claude").mkdir()
    assert copilot.check(tmp_path) == 0


def test_a_root_that_is_not_a_repository_fails(tmp_path, capsys):
    assert copilot.check(tmp_path / "missing") == 1
    assert copilot.check(tmp_path) == 1
    assert "is not a repository root" in capsys.readouterr().err


def test_a_source_outside_the_repository_fails(tmp_path, capsys):
    root = tmp_path / "repo"
    (root / ".claude/rules").mkdir(parents=True)
    outside = tmp_path / "outside.txt"
    outside.write_text("secret\n", encoding="utf-8")
    wrapper = root / ".github/instructions/hand.instructions.md"
    wrapper.parent.mkdir(parents=True)
    for named in ("../outside.txt", str(outside)):
        wrapper.write_text(
            f'---\napplyTo: "**"\n---\n<!-- source: {named} sha256: {digest(outside)} -->\n',
            encoding="utf-8",
        )
        assert copilot.check(root) == 1
        assert "which is outside the repository" in capsys.readouterr().out


def test_a_hand_written_wrapper_cannot_pin_a_file_that_is_not_mirrored(tmp_path, capsys):
    (tmp_path / ".claude").mkdir()
    (tmp_path / "notes.md").write_text("Notes.\n", encoding="utf-8")
    wrapper = tmp_path / ".github/instructions/hand.instructions.md"
    wrapper.parent.mkdir(parents=True)
    recorded = digest(tmp_path / "notes.md")
    wrapper.write_text(
        f'---\napplyTo: "**"\n---\n<!-- source: notes.md sha256: {recorded} -->\n',
        encoding="utf-8",
    )
    assert copilot.check(tmp_path) == 1
    assert "not a source that is mirrored" in capsys.readouterr().out


def test_a_source_with_no_wrapper_fails(tmp_path, capsys):
    write_pair(tmp_path, ".claude/rules/skills.md", ".github/instructions/skills.instructions.md")
    (tmp_path / ".claude/rules/workflows.md").write_text("Pin actions.\n", encoding="utf-8")
    assert copilot.check(tmp_path) == 1
    out = capsys.readouterr().out
    assert ".claude/rules/workflows.md has no Copilot wrapper" in out
    assert ".github/instructions/workflows.instructions.md" in out


def test_each_kind_of_source_needs_its_own_wrapper(tmp_path, capsys):
    for source in (".claude/agents/reviewer.md", ".claude/commands/verify.md", "REVIEW.md"):
        path = tmp_path / source
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Text.\n", encoding="utf-8")
    assert copilot.check(tmp_path) == 1
    out = capsys.readouterr().out
    assert ".github/agents/reviewer.agent.md" in out
    assert ".github/prompts/verify.prompt.md" in out
    assert ".github/instructions/review.instructions.md" in out


def test_a_changed_source_fails_and_names_the_new_hash(tmp_path, capsys):
    write_pair(tmp_path, ".claude/rules/skills.md", ".github/instructions/skills.instructions.md")
    source = tmp_path / ".claude/rules/skills.md"
    source.write_text("Rule one, reworded.\n", encoding="utf-8")
    assert copilot.check(tmp_path) == 1
    out = capsys.readouterr().out
    assert "update the wrapper to match the source" in out
    assert digest(source) in out


def test_a_single_changed_byte_is_enough(tmp_path):
    # The hash is over bytes, not meaning: a trailing newline is a change a person must
    # look at, which is cheap, where deciding which edits are cosmetic is not.
    write_pair(tmp_path, ".claude/rules/skills.md", ".github/instructions/skills.instructions.md")
    source = tmp_path / ".claude/rules/skills.md"
    source.write_text(source.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert copilot.check(tmp_path) == 1


def test_a_wrapper_pointing_at_a_missing_source_fails(tmp_path, capsys):
    wrapper = write_pair(
        tmp_path, ".claude/rules/old.md", ".github/instructions/old.instructions.md"
    )
    (tmp_path / ".claude/rules/old.md").unlink()
    assert wrapper.is_file()
    assert copilot.check(tmp_path) == 1
    assert "points to .claude/rules/old.md, which does not exist" in capsys.readouterr().out


def test_a_wrapper_pointing_at_another_source_fails(tmp_path, capsys):
    write_pair(tmp_path, ".claude/rules/skills.md", ".github/instructions/skills.instructions.md")
    other = tmp_path / ".claude/rules/agents.md"
    other.write_text("Agents.\n", encoding="utf-8")
    wrapper = tmp_path / ".github/instructions/agents.instructions.md"
    wrapper.write_text(
        f'---\napplyTo: "**"\n---\n<!-- source: .claude/rules/skills.md sha256: '
        f"{digest(tmp_path / '.claude/rules/skills.md')} -->\n",
        encoding="utf-8",
    )
    assert copilot.check(tmp_path) == 1
    assert "its name maps to .claude/rules/agents.md" in capsys.readouterr().out


def test_a_wrapper_with_no_source_comment_fails(tmp_path, capsys):
    write_pair(tmp_path, ".claude/rules/skills.md", ".github/instructions/skills.instructions.md")
    wrapper = tmp_path / ".github/instructions/skills.instructions.md"
    wrapper.write_text('---\napplyTo: "**"\n---\nInline rule only.\n', encoding="utf-8")
    assert copilot.check(tmp_path) == 1
    assert "does not start with `<!-- source:" in capsys.readouterr().out


def test_the_comment_must_open_the_body_not_follow_other_text(tmp_path):
    write_pair(tmp_path, ".claude/rules/skills.md", ".github/instructions/skills.instructions.md")
    wrapper = tmp_path / ".github/instructions/skills.instructions.md"
    lines = wrapper.read_text(encoding="utf-8").splitlines()
    wrapper.write_text("\n".join([*lines[:3], "Inline rule.", *lines[3:]]) + "\n", encoding="utf-8")
    assert copilot.check(tmp_path) == 1


def test_a_comment_inside_an_unclosed_front_matter_does_not_count(tmp_path):
    write_pair(tmp_path, ".claude/rules/skills.md", ".github/instructions/skills.instructions.md")
    wrapper = tmp_path / ".github/instructions/skills.instructions.md"
    wrapper.write_text(wrapper.read_text(encoding="utf-8").replace("---\n<!--", "<!--", 1))
    assert copilot.check(tmp_path) == 1


def test_a_hand_written_instruction_file_is_left_alone(tmp_path):
    # No source of that name and no comment: it is a Copilot-only file, not a copy.
    (tmp_path / ".claude").mkdir()
    path = tmp_path / ".github/instructions/extra.instructions.md"
    path.parent.mkdir(parents=True)
    path.write_text('---\napplyTo: "**"\n---\nA rule only Copilot needs.\n', encoding="utf-8")
    assert copilot.check(tmp_path) == 0


def test_the_hash_is_compared_case_insensitively(tmp_path):
    wrapper = write_pair(
        tmp_path, ".claude/rules/skills.md", ".github/instructions/skills.instructions.md"
    )
    text = wrapper.read_text(encoding="utf-8")
    start = text.index("sha256: ") + len("sha256: ")
    wrapper.write_text(text[:start] + text[start:].upper(), encoding="utf-8")
    assert copilot.check(tmp_path) == 0


def test_benchmark_cases_under_agents_are_not_sources(tmp_path):
    # `.claude/agents/benchmarks/` holds cases for the review benchmark, not agent files.
    case = tmp_path / ".claude/agents/benchmarks/case-one/case.json"
    case.parent.mkdir(parents=True)
    case.write_text("{}", encoding="utf-8")
    assert copilot.check(tmp_path) == 0


def test_the_main_entry_point_takes_a_root(tmp_path, capsys):
    write_pair(tmp_path, "REVIEW.md", ".github/instructions/review.instructions.md")
    assert copilot.main([str(tmp_path)]) == 0
    assert "1 Copilot wrapper(s)" in capsys.readouterr().out


def test_the_help_text_carries_the_update_steps(capsys):
    try:
        copilot.main(["--help"])
    except SystemExit as stop:
        assert stop.code == 0
    out = capsys.readouterr().out
    assert "To update a wrapper after its source changed" in out
    assert "sha256sum" in out


def test_this_repository_is_in_step_with_its_wrappers(capsys):
    assert copilot.check(REPO) == 0, capsys.readouterr().out
