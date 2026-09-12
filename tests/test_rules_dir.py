"""`.claude/rules/` is loaded into every session, so a broken rule is expensive twice.

Claude Code concatenates every Markdown file it finds under that directory into context
at session start, and a rule carrying a `paths:` glob loads only when a matching file is
read. That second form is the one worth checking: a glob that matches nothing produces
no error anywhere — the rule simply never loads, and the author goes on believing it
does. Everything else here is the same silent-failure class the validator already
catches for skills and commands.
"""

from __future__ import annotations

import pytest

from skillcheck.rules import ERROR, WARNING, check_rule, find_rules


def write_rule(root, name, text):
    directory = root / ".claude" / "rules"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.md"
    path.write_text(text, encoding="utf-8")
    return path


def codes(findings, level=ERROR):
    return {f.code for f in findings if f.level == level}


def test_an_unscoped_rule_is_valid(tmp_path):
    """No frontmatter means the rule loads every session, which is a choice not a bug."""
    path = write_rule(tmp_path, "house-style", "# House style\n\nWrite it plainly.\n")
    assert check_rule(path, tmp_path) == []


def test_a_glob_that_matches_something_produces_nothing(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "thing.py").write_text("x = 1\n", encoding="utf-8")
    path = write_rule(tmp_path, "src", '---\npaths:\n  - "src/**"\n---\n\n# Src\n\nBody.\n')
    assert check_rule(path, tmp_path) == []


def test_a_glob_that_matches_nothing_is_an_error(tmp_path):
    path = write_rule(tmp_path, "gone", '---\npaths:\n  - "src/gone/**"\n---\n\n# Gone\n\nBody.\n')
    findings = check_rule(path, tmp_path)
    assert "dangling-glob" in codes(findings)
    assert findings[0].line == 3


def test_only_the_unmatched_glob_is_reported(tmp_path):
    (tmp_path / "AGENTS.md").write_text("# Rules\n", encoding="utf-8")
    text = '---\npaths:\n  - "AGENTS.md"\n  - "nowhere/**"\n---\n\n# Two\n\nBody.\n'
    findings = check_rule(write_rule(tmp_path, "two", text), tmp_path)
    assert [(f.code, f.line) for f in findings] == [("dangling-glob", 4)]


def test_the_flow_sequence_form_is_read_too(tmp_path):
    text = '---\npaths: ["nowhere/**", "elsewhere/**"]\n---\n\n# Flow\n\nBody.\n'
    findings = check_rule(write_rule(tmp_path, "flow", text), tmp_path)
    assert [f.code for f in findings] == ["dangling-glob", "dangling-glob"]


def test_a_single_unwrapped_glob_is_read_too(tmp_path):
    text = "---\npaths: nowhere/**\n---\n\n# One\n\nBody.\n"
    assert "dangling-glob" in codes(check_rule(write_rule(tmp_path, "one", text), tmp_path))


def test_an_empty_paths_list_is_an_error(tmp_path):
    """Scoped to nothing is worse than unscoped: it looks deliberate and never fires."""
    text = "---\npaths: []\n---\n\n# Empty\n\nBody.\n"
    assert "empty-paths" in codes(check_rule(write_rule(tmp_path, "empty", text), tmp_path))


@pytest.mark.parametrize("pattern", ["/etc/**", "../outside/**"])
def test_a_glob_outside_the_repository_is_dangling(tmp_path, pattern):
    """The sibling is created on purpose: `Path.glob` resolves `..` and would otherwise
    pass a rule scoped where Claude Code will never look."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (tmp_path / "outside").mkdir()
    (tmp_path / "outside" / "x.md").write_text("x\n", encoding="utf-8")
    text = f'---\npaths:\n  - "{pattern}"\n---\n\n# Bad\n\nBody.\n'
    assert "dangling-glob" in codes(check_rule(write_rule(repo, "bad", text), repo))


def test_malformed_frontmatter_is_an_error(tmp_path):
    text = "---\npaths:\n  - x\n\n# Never closed\n"
    assert "frontmatter" in codes(check_rule(write_rule(tmp_path, "open", text), tmp_path))


def test_a_rule_with_no_body_is_an_error(tmp_path):
    text = '---\npaths:\n  - "*.md"\n---\n\n'
    assert "empty-rule" in codes(check_rule(write_rule(tmp_path, "hollow", text), tmp_path))


def test_a_dangling_pointer_in_a_rule_is_an_error(tmp_path):
    """Paths in rule prose are repository-relative, because that is where a rule sits."""
    text = "# Scripts\n\nRun `scripts/missing.py` before you stop.\n"
    assert "dangling-reference" in codes(check_rule(write_rule(tmp_path, "p", text), tmp_path))


def test_a_pointer_that_exists_is_accepted(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "check.py").write_text("", encoding="utf-8")
    text = "# Scripts\n\nRun `scripts/check.py` before you stop.\n"
    assert check_rule(write_rule(tmp_path, "p", text), tmp_path) == []


def test_shouting_in_a_rule_is_a_warning(tmp_path):
    text = "# Loud\n\nNEVER do the thing.\n"
    findings = check_rule(write_rule(tmp_path, "loud", text), tmp_path)
    assert "shouting" in codes(findings, WARNING)


def test_find_rules_recurses_and_exempts_nothing(tmp_path):
    """Every Markdown file under the directory is loaded, a README included, so every
    one of them is checked."""
    directory = tmp_path / ".claude" / "rules"
    (directory / "nested").mkdir(parents=True)
    for name in ("a.md", "README.md"):
        (directory / name).write_text("body\n", encoding="utf-8")
    (directory / "nested" / "b.md").write_text("body\n", encoding="utf-8")
    assert [p.name for p in find_rules(directory)] == ["README.md", "a.md", "b.md"]


def test_find_rules_on_a_repository_without_the_directory(tmp_path):
    assert find_rules(tmp_path / ".claude" / "rules") == []


def test_other_frontmatter_keys_are_stepped_over(tmp_path):
    """The sequence is read from the raw lines, so it has to find `paths` among them
    and stop at the next key rather than swallowing it."""
    text = (
        "---\n"
        "description: A scoped rule.\n"
        "paths:\n"
        '  - "nowhere/**"\n'
        "enabled: true\n"
        "---\n\n# Keys\n\nBody.\n"
    )
    findings = check_rule(write_rule(tmp_path, "keys", text), tmp_path)
    assert [(f.code, f.line) for f in findings] == [("dangling-glob", 4)]


def test_a_brace_group_is_expanded_before_matching(tmp_path):
    """`pathlib` has no brace expansion and the documented idiom uses one, so handing
    the pattern straight to `Path.glob` would fail a correct rule."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.tsx").write_text("", encoding="utf-8")
    text = '---\npaths:\n  - "src/**/*.{ts,tsx}"\n---\n\n# TS\n\nBody.\n'
    assert check_rule(write_rule(tmp_path, "ts", text), tmp_path) == []


def test_a_brace_group_matching_no_branch_is_still_dangling(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("", encoding="utf-8")
    text = '---\npaths:\n  - "src/**/*.{ts,tsx}"\n---\n\n# TS\n\nBody.\n'
    assert "dangling-glob" in codes(check_rule(write_rule(tmp_path, "ts", text), tmp_path))


def test_nested_brace_groups_expand(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "two.md").write_text("", encoding="utf-8")
    text = '---\npaths:\n  - "{a,b}/{one,two}.md"\n---\n\n# N\n\nBody.\n'
    assert check_rule(write_rule(tmp_path, "n", text), tmp_path) == []


def test_the_flow_form_does_not_split_inside_a_brace_group(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.tsx").write_text("", encoding="utf-8")
    (tmp_path / "b.md").write_text("", encoding="utf-8")
    text = '---\npaths: ["src/**/*.{ts,tsx}", "b.md"]\n---\n\n# Flow\n\nBody.\n'
    assert check_rule(write_rule(tmp_path, "flow", text), tmp_path) == []


def test_a_flow_sequence_wrapped_over_lines_is_refused_loudly(tmp_path):
    """The frontmatter reader takes one line per value on purpose. A wrapped sequence is
    rejected with a message rather than half-read, which is the failure worth having."""
    text = '---\npaths: [\n  "nowhere/**",\n]\n---\n\n# Wrapped\n\nBody.\n'
    assert "frontmatter" in codes(check_rule(write_rule(tmp_path, "wrapped", text), tmp_path))


def test_a_trailing_comment_is_not_part_of_the_glob(tmp_path):
    (tmp_path / "AGENTS.md").write_text("", encoding="utf-8")
    text = "---\npaths:\n  - AGENTS.md  # the contract\n---\n\n# C\n\nBody.\n"
    assert check_rule(write_rule(tmp_path, "c", text), tmp_path) == []


def test_a_blank_line_before_the_first_entry_does_not_hide_it(tmp_path):
    text = "---\npaths:\n\n  - nowhere/**\n---\n\n# B\n\nBody.\n"
    findings = check_rule(write_rule(tmp_path, "b", text), tmp_path)
    assert [f.code for f in findings] == ["dangling-glob"]


@pytest.mark.parametrize("pattern", ['""', '"a/"'])
def test_a_glob_the_interpreter_refuses_is_reported_not_raised(tmp_path, pattern):
    """`Path.glob` raises on an empty pattern and on some trailing-separator forms, and
    the version it raises on moves. One bad glob names itself rather than ending the run
    for every other rule in the repository."""
    text = f"---\npaths:\n  - {pattern}\n---\n\n# Bad\n\nBody.\n"
    assert "dangling-glob" in codes(check_rule(write_rule(tmp_path, "bad", text), tmp_path))
