"""The two checks that keep the repository honest about itself.

Both guard failures with no symptom. A plugin whose listing has crept past the runtime
budget still installs, still validates, and quietly stops offering its least-used skills.
A README that no longer matches the tree still renders, and tells a reader the library
contains something it does not. Neither raises an error anywhere, which is why each
needed a gate rather than a habit.
"""

from __future__ import annotations

import json

from tests.conftest import load_script, write_skill

budget = load_script("check_listing_budget.py")
readme = load_script("check_readme.py")


# --- the listing ratchet --------------------------------------------------------------


def test_measure_counts_description_characters_per_plugin(mini_repo):
    sizes = budget.measure(mini_repo)
    assert set(sizes) == {"engineering"}
    assert sizes["engineering"] > 0


def test_a_generated_file_passes_the_check_it_was_generated_from(mini_repo, capsys):
    assert budget.check(mini_repo, update=True) == 0
    assert budget.check(mini_repo) == 0
    assert "engineering" in capsys.readouterr().out


def test_growth_past_the_ceiling_fails(mini_repo, capsys):
    budget.check(mini_repo, update=True)
    path = mini_repo / budget.BUDGET_FILE
    data = json.loads(path.read_text())
    # A ceiling below the measured total is what a new skill looks like from here.
    data["plugins"]["engineering"] = 10
    path.write_text(json.dumps(data), encoding="utf-8")
    assert budget.check(mini_repo) == 1
    assert "against a ceiling of 10" in capsys.readouterr().out


def test_a_plugin_with_no_ceiling_fails_rather_than_being_skipped(mini_repo, capsys):
    # The dangerous shape: a new plugin silently unmeasured because the file was never
    # regenerated. Passing here would make the whole check optional in practice.
    budget.check(mini_repo, update=True)
    path = mini_repo / budget.BUDGET_FILE
    data = json.loads(path.read_text())
    data["plugins"] = {}
    path.write_text(json.dumps(data), encoding="utf-8")
    assert budget.check(mini_repo) == 1
    assert "has no ceiling" in capsys.readouterr().out


def test_a_ceiling_for_a_plugin_that_is_gone_fails(mini_repo, capsys):
    budget.check(mini_repo, update=True)
    path = mini_repo / budget.BUDGET_FILE
    data = json.loads(path.read_text())
    data["plugins"]["retired"] = 5000
    path.write_text(json.dumps(data), encoding="utf-8")
    assert budget.check(mini_repo) == 1
    assert "which is not a plugin" in capsys.readouterr().out


def test_a_missing_or_malformed_budget_file_fails(mini_repo, capsys):
    path = mini_repo / budget.BUDGET_FILE
    assert budget.check(mini_repo) == 1
    path.write_text("[]", encoding="utf-8")
    assert budget.check(mini_repo) == 1
    path.write_text("{not json", encoding="utf-8")
    assert budget.check(mini_repo) == 1


def test_the_ceiling_leaves_room_to_reword_and_not_to_add_a_skill():
    # A description is 500-900 characters, so one step of slack is the line between
    # editing prose and adding a skill.
    assert budget.ceiling_for(4559) == 5000
    assert budget.ceiling_for(5000) == 5000
    assert budget.ceiling_for(5001) == 5500
    assert budget.ceiling_for(0) == budget.GRANULARITY


def test_main_reports_a_tree_with_no_plugins(tmp_path):
    assert budget.main([str(tmp_path)]) == 2


# --- the README catalogue -------------------------------------------------------------

README = """# Mini

[![Skills](https://img.shields.io/badge/skills-2-7c3aed)](#skills)

| Plugin | Focus | Contents |
| --- | --- | --- |
| `engineering` | Things | 2 skills, 1 subagent |

| Skill | What it does |
| --- | --- |
| [`alpha`](plugins/engineering/skills/alpha/SKILL.md) | First. |
| [`beta`](plugins/engineering/skills/beta/SKILL.md) | Second. |

| Subagent | Reads |
| --- | --- |
| `reader` | Things |
"""


def write_readme(root, text=README):
    (root / "README.md").write_text(text, encoding="utf-8")


def test_a_matching_readme_passes(mini_repo, capsys):
    write_readme(mini_repo)
    assert readme.check(mini_repo) == 0
    assert "README is current" in capsys.readouterr().out


def test_a_skill_with_no_row_fails(mini_repo, capsys):
    write_skill(mini_repo, "engineering", "gamma")
    write_readme(mini_repo)
    assert readme.check(mini_repo) == 1
    assert "gamma is in the repository and has no row" in capsys.readouterr().out


def test_a_row_for_a_skill_that_is_gone_fails(mini_repo, capsys):
    write_readme(
        mini_repo,
        README.replace(
            "| [`beta`](plugins/engineering/skills/beta/SKILL.md) | Second. |",
            "| [`beta`](plugins/engineering/skills/beta/SKILL.md) | Second. |\n"
            "| [`delta`](plugins/engineering/skills/delta/SKILL.md) | Gone. |",
        ),
    )
    assert readme.check(mini_repo) == 1
    out = capsys.readouterr().out
    assert "which does not exist" in out
    assert "not a skill in any plugin" in out


def test_a_stale_badge_fails(mini_repo, capsys):
    write_readme(mini_repo, README.replace("skills-2-", "skills-9-"))
    assert readme.check(mini_repo) == 1
    assert "the skills badge says 9, and there are 2" in capsys.readouterr().out


def test_a_stale_contents_count_fails(mini_repo, capsys):
    write_readme(mini_repo, README.replace("2 skills, 1 subagent", "7 skills, 1 subagent"))
    assert readme.check(mini_repo) == 1
    assert "says engineering has 7 skills, and it has 2" in capsys.readouterr().out


def test_a_subagent_with_no_row_fails(mini_repo, capsys):
    write_readme(mini_repo, README.replace("| `reader` | Things |\n", ""))
    assert readme.check(mini_repo) == 1
    assert "subagent reader ships with engineering and has no row" in capsys.readouterr().out


def test_a_plugin_missing_from_the_contents_table_fails(mini_repo, capsys):
    write_readme(
        mini_repo, README.replace("| `engineering` | Things | 2 skills, 1 subagent |\n", "")
    )
    assert readme.check(mini_repo) == 1
    assert "has no row in the contents table" in capsys.readouterr().out


def test_a_row_pointing_at_a_different_skill_fails(mini_repo, capsys):
    # The link resolves, so nothing else would catch it: the reader is sent to the wrong
    # skill and the page renders perfectly.
    write_readme(
        mini_repo,
        README.replace(
            "[`beta`](plugins/engineering/skills/beta/SKILL.md)",
            "[`beta`](plugins/engineering/skills/alpha/SKILL.md)",
        ),
    )
    assert readme.check(mini_repo) == 1
    assert "which is a different skill" in capsys.readouterr().out


def test_a_duplicated_row_fails(mini_repo, capsys):
    write_readme(
        mini_repo,
        README.replace(
            "| [`beta`](plugins/engineering/skills/beta/SKILL.md) | Second. |",
            "| [`beta`](plugins/engineering/skills/beta/SKILL.md) | Second. |\n"
            "| [`beta`](plugins/engineering/skills/beta/SKILL.md) | Again. |",
        ),
    )
    assert readme.check(mini_repo) == 1
    assert "has 2 rows in the README" in capsys.readouterr().out


def test_main_reports_a_tree_with_no_readme(tmp_path):
    assert readme.main([str(tmp_path)]) == 2


def test_a_malformed_skill_is_left_to_the_validator(mini_repo, capsys):
    # Two checks reporting the same broken file is noise, and the one that owns it is
    # the validator. This has to skip rather than crash, or one bad file takes the
    # listing check down with it.
    broken = mini_repo / "plugins" / "engineering" / "skills" / "alpha" / "SKILL.md"
    broken.write_text("---\nname: [unclosed\n", encoding="utf-8")
    sizes = budget.measure(mini_repo)
    assert sizes["engineering"] > 0  # beta still counted
    assert budget.check(mini_repo, update=True) == 0


def test_a_plugin_over_the_runtime_default_is_reported_and_not_failed(mini_repo, capsys):
    # Being above the runtime's own budget is a fact about the plugin, not a defect in
    # the change in front of you: someone who installs one plugin is unaffected.
    budget.check(mini_repo, update=True)
    path = mini_repo / budget.BUDGET_FILE
    data = json.loads(path.read_text())
    data["plugins"]["engineering"] = 99_000
    path.write_text(json.dumps(data), encoding="utf-8")
    monkey = budget.RUNTIME_DEFAULT
    budget.RUNTIME_DEFAULT = 1
    try:
        assert budget.check(mini_repo) == 0
    finally:
        budget.RUNTIME_DEFAULT = monkey
    assert "over the runtime default" in capsys.readouterr().out


def test_update_through_main_writes_the_file(mini_repo):
    assert budget.main([str(mini_repo), "--update"]) == 0
    assert (mini_repo / budget.BUDGET_FILE).is_file()
    assert budget.main([str(mini_repo)]) == 0


def test_a_readme_with_no_badge_fails(mini_repo, capsys):
    write_readme(
        mini_repo,
        README.replace("[![Skills](https://img.shields.io/badge/skills-2-7c3aed)](#skills)", ""),
    )
    assert readme.check(mini_repo) == 1
    assert "no skills badge found" in capsys.readouterr().out


def test_a_backticked_name_in_another_table_is_not_read_as_a_plugin(mini_repo, capsys):
    # The contents-row pattern matches any three-column row starting with a backticked
    # name, and the README has several such tables. Treating one of those as a plugin
    # row would invent a failure on a correct README.
    write_readme(
        mini_repo,
        README + "\n| `some-tool` | Not a plugin | No counts here |\n",
    )
    assert readme.check(mini_repo) == 0
