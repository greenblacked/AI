"""The checks that keep the repository honest about itself.

Every one guards a failure with no symptom. A plugin whose listing has crept past the
runtime budget still installs, still validates, and quietly stops offering its least-used
skills. A README that no longer matches the tree still renders, and tells a reader the
library contains something it does not. A command with an unbalanced quote reads fine
until someone runs it. And a flattened export can ship a pointer to a file the reader
does not have while its own check reports clean. None of them raises an error anywhere,
which is why each needed a gate rather than a habit.
"""

from __future__ import annotations

import json
import re
import shutil

import pytest

from tests.conftest import REPO, load_script, write_skill

budget = load_script("check_listing_budget.py")
readme = load_script("check_readme.py")
ci_docs = load_script("check_ci_docs.py")


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
    assert budget.ceiling_for(5001) == 5500
    assert budget.ceiling_for(0) == budget.GRANULARITY
    # Rounding alone is not enough. A total that lands just under a boundary would earn
    # a ceiling one character above it, and four documents promise rewording is free.
    for size in (4499, 5000, 11998):
        assert budget.ceiling_for(size) - size >= budget.HEADROOM, size


def test_main_reports_a_tree_with_no_plugins(tmp_path):
    assert budget.main([str(tmp_path)]) == 2


# --- the per-skill description ratchet -------------------------------------------------


def raise_the_plugin_ceiling(root, value=99_000):
    """Lift the per-plugin ceiling out of the way.

    It is a separate gate with its own tests, and a test of the per-skill one that hits
    it first would pass for the wrong reason.
    """
    path = root / budget.BUDGET_FILE
    data = json.loads(path.read_text())
    data["plugins"]["engineering"] = value
    path.write_text(json.dumps(data), encoding="utf-8")


def test_a_new_description_past_the_target_fails(mini_repo, capsys):
    # A skill with no record is new, and new is the half of the corpus this gates.
    budget.check(mini_repo, update=True)
    write_skill(
        mini_repo, "engineering", "gamma", description="g" * (budget.DESCRIPTION_TARGET + 1)
    )
    raise_the_plugin_ceiling(mini_repo)
    assert budget.check(mini_repo) == 1
    out = capsys.readouterr().out
    assert "gamma is new" in out
    # Both ways out have to be in the message, or the cheap one is the only one found.
    assert "trim the description" in out and "--update and say why" in out


def test_a_new_description_inside_the_target_passes(mini_repo):
    budget.check(mini_repo, update=True)
    write_skill(mini_repo, "engineering", "gamma", description="g" * budget.DESCRIPTION_TARGET)
    raise_the_plugin_ceiling(mini_repo)
    assert budget.check(mini_repo) == 0  # at the target, which is a target and not a limit


def test_a_description_already_over_the_target_is_grandfathered(mini_repo, capsys):
    # Why this is a ratchet and not a threshold: a third of the descriptions in this
    # repository are already past the guidance, and trimming them to clear a new check is
    # the one edit AGENTS.md refuses. They are recorded at what they measure instead.
    write_skill(mini_repo, "engineering", "gamma", description="g" * 960)
    assert budget.check(mini_repo, update=True) == 0
    assert json.loads((mini_repo / budget.BUDGET_FILE).read_text())["skills"]["gamma"] == 960
    assert budget.check(mini_repo) == 0
    assert "1 grandfathered above it (longest gamma at 960)" in capsys.readouterr().out


def test_a_grandfathered_description_growing_past_its_record_fails(mini_repo, capsys):
    # A description already over the target is pinned where it is. That growth is the
    # only growth this ratchet exists to stop.
    over = budget.DESCRIPTION_TARGET + 40
    budget.check(mini_repo, update=True)
    write_skill(mini_repo, "engineering", "alpha", description="a" * over)
    raise_the_plugin_ceiling(mini_repo)
    budget.check(mini_repo, update=True)
    write_skill(mini_repo, "engineering", "alpha", description="a" * (over + 1))
    raise_the_plugin_ceiling(mini_repo)
    assert budget.check(mini_repo) == 1
    assert f"against a limit of {over:,}" in capsys.readouterr().out


def test_rewording_under_the_target_stays_free(mini_repo):
    # The per-plugin half of this file carries slack so that rewording stays free. A
    # record under the target is a floor of the target, not a second flat rule, or every
    # reworded sentence would conflict on listing-budget.json.
    budget.check(mini_repo, update=True)
    recorded = json.loads((mini_repo / budget.BUDGET_FILE).read_text())["skills"]["alpha"]
    assert recorded < budget.DESCRIPTION_TARGET
    write_skill(mini_repo, "engineering", "alpha", description="a" * budget.DESCRIPTION_TARGET)
    raise_the_plugin_ceiling(mini_repo)
    assert budget.check(mini_repo) == 0


def test_a_shorter_description_than_the_record_passes(mini_repo):
    # Trimming is the fix the error message recommends, so it cannot itself fail. The
    # record catches up at the next --update.
    budget.check(mini_repo, update=True)
    recorded = json.loads((mini_repo / budget.BUDGET_FILE).read_text())["skills"]["alpha"]
    write_skill(mini_repo, "engineering", "alpha", description="a" * (recorded - 20))
    assert budget.check(mini_repo) == 0


def test_a_record_for_a_skill_that_is_gone_fails(mini_repo, capsys):
    # Not harmless drift: a skill added later under the same name would inherit a
    # grandfathered length nobody decided to give it.
    budget.check(mini_repo, update=True)
    path = mini_repo / budget.BUDGET_FILE
    data = json.loads(path.read_text())
    data["skills"]["retired"] = 960
    path.write_text(json.dumps(data), encoding="utf-8")
    assert budget.check(mini_repo) == 1
    assert "records a skill named retired" in capsys.readouterr().out


def test_update_records_the_length_of_every_skill(mini_repo):
    assert budget.check(mini_repo, update=True) == 0
    data = json.loads((mini_repo / budget.BUDGET_FILE).read_text())
    assert set(data["skills"]) == {"alpha", "beta"}
    assert data["skills"] == {skill: n for _plugin, skill, n in budget.walk(mini_repo)}
    # One measurement feeds both numbers, so a plugin total is the sum of its skills.
    assert sum(data["skills"].values()) == budget.measure(mini_repo)["engineering"]


def test_a_budget_file_with_no_skills_map_fails(mini_repo, capsys):
    # The file predates the per-skill ratchet, so the shape without it has to be an
    # error rather than a map that silently grandfathers everything.
    budget.check(mini_repo, update=True)
    path = mini_repo / budget.BUDGET_FILE
    data = json.loads(path.read_text())
    del data["skills"]
    path.write_text(json.dumps(data), encoding="utf-8")
    assert budget.check(mini_repo) == 1
    assert "'plugins' and 'skills'" in capsys.readouterr().err


def test_the_committed_budget_file_is_what_the_writer_emits(tmp_path):
    """The file is generated, and a hand edit to it survives until the next --update.

    Formatting, key order and the note all come from write(); the skill map has to name
    exactly the skills on disk, and every recorded length has to be one this tree still
    satisfies, or the committed ratchet is one nobody could have generated.
    """
    text = (REPO / budget.BUDGET_FILE).read_text(encoding="utf-8")
    committed = json.loads(text)
    assert text == json.dumps(committed, indent=2) + "\n"
    assert list(committed["skills"]) == sorted(committed["skills"])
    assert list(committed["plugins"]) == sorted(committed["plugins"])

    scratch = tmp_path / budget.BUDGET_FILE
    budget.write(scratch, {"any": 0})
    assert committed["_comment"] == json.loads(scratch.read_text(encoding="utf-8"))["_comment"]

    measured = {skill: n for _plugin, skill, n in budget.walk(REPO)}
    assert set(committed["skills"]) == set(measured)
    assert {n for n, length in measured.items() if length > committed["skills"][n]} == set()


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


def test_a_repo_local_subagent_with_no_readme_row_is_caught(mini_repo, capsys):
    # Skills, and anything a plugin ships, were gated from the start. `.claude/` was not,
    # so the three-stage loop's own documentation went stale without any gate noticing.
    write_readme(mini_repo)
    agents = mini_repo / ".claude" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    (agents / "searcher.md").write_text(
        "---\nname: searcher\ndescription: " + "f" * 60 + "\ntools: Read\n---\n\nBody.\n",
        encoding="utf-8",
    )
    assert readme.check(mini_repo) == 1
    assert "searcher is in .claude/ and has no row" in capsys.readouterr().out


def test_a_repo_local_command_with_no_readme_row_is_caught(mini_repo, capsys):
    write_readme(mini_repo)
    commands = mini_repo / ".claude" / "commands"
    commands.mkdir(parents=True, exist_ok=True)
    (commands / "verify.md").write_text(
        "---\ndescription: " + "f" * 60 + "\n---\n\nBody.\n", encoding="utf-8"
    )
    assert readme.check(mini_repo) == 1
    assert "/verify is in .claude/ and has no row" in capsys.readouterr().out


def test_a_repo_local_agent_named_in_the_readme_passes(mini_repo, capsys):
    agents = mini_repo / ".claude" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    (agents / "searcher.md").write_text(
        "---\nname: searcher\ndescription: " + "f" * 60 + "\ntools: Read\n---\n\nBody.\n",
        encoding="utf-8",
    )
    write_readme(
        mini_repo,
        README + "\n\n| Local subagent | Role |\n| --- | --- |\n| `searcher` | Finds things |\n",
    )
    assert readme.check(mini_repo) == 0


def test_a_repo_local_agent_named_only_in_prose_fails(mini_repo, capsys):
    """A backticked name used to satisfy this check wherever it appeared, prose
    included, so a subagent could be discussed at length and still have no row anyone
    could point at — the same gap `SKILL_ROW_RE` never had for a skill."""
    agents = mini_repo / ".claude" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    (agents / "searcher.md").write_text(
        "---\nname: searcher\ndescription: " + "f" * 60 + "\ntools: Read\n---\n\nBody.\n",
        encoding="utf-8",
    )
    write_readme(mini_repo, README + "\n\nAlso `searcher`, which ships to nobody.\n")
    assert readme.check(mini_repo) == 1
    assert "searcher is in .claude/ and has no row" in capsys.readouterr().out


def test_a_matching_readme_passes(mini_repo, capsys):
    write_readme(mini_repo)
    assert readme.check(mini_repo) == 0
    assert "README is current" in capsys.readouterr().out


def test_on_disk_does_not_hide_a_plugin_skill_named_template(mini_repo):
    """`on_disk` calls `find_skills` scoped to one plugin's `skills/` directory, which
    is exactly the caller a `template/`-vs-`skills/` mixup used to hide a skill from —
    a plugin shipping `skills/template/` would be missing from this set entirely, and
    every check built on it would report the skill as never having existed."""
    write_skill(mini_repo, "engineering", "template")
    assert "template" in readme.on_disk(mini_repo)["engineering"]["skills"]


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


def test_a_plugin_subagent_named_only_in_prose_still_fails(mini_repo, capsys):
    """The row is gone and the name is still mentioned in passing — a backticked name
    appearing anywhere used to be read as "listed", so this prose survived the check
    that the missing row above is meant to catch."""
    text = README.replace("| `reader` | Things |\n", "") + "\nSee `reader` for the read path.\n"
    write_readme(mini_repo, text)
    assert readme.check(mini_repo) == 1
    assert "subagent reader ships with engineering and has no row" in capsys.readouterr().out


def test_a_contents_row_linked_to_its_section_passes(mini_repo, capsys):
    row = "| `engineering` | Things | 2 skills, 1 subagent |\n"
    linked = "| [`engineering`](#engineering) | Things | 2 skills, 1 subagent |\n"
    write_readme(mini_repo, README.replace(row, linked) + "\n### Engineering\n")
    assert readme.check(mini_repo) == 0


def test_a_contents_row_linked_to_another_section_fails(mini_repo, capsys):
    row = "| `engineering` | Things | 2 skills, 1 subagent |\n"
    linked = "| [`engineering`](#career) | Things | 2 skills, 1 subagent |\n"
    write_readme(mini_repo, README.replace(row, linked) + "\n### Engineering\n")
    assert readme.check(mini_repo) == 1
    assert "links engineering to #career; its section is #engineering" in capsys.readouterr().out


def test_a_contents_row_linked_to_a_missing_heading_fails(mini_repo, capsys):
    row = "| `engineering` | Things | 2 skills, 1 subagent |\n"
    linked = "| [`engineering`](#engineering) | Things | 2 skills, 1 subagent |\n"
    write_readme(mini_repo, README.replace(row, linked))
    assert readme.check(mini_repo) == 1
    assert "and no heading makes it" in capsys.readouterr().out


def test_a_linked_contents_row_still_has_its_counts_checked(mini_repo, capsys):
    row = "| `engineering` | Things | 2 skills, 1 subagent |\n"
    linked = "| [`engineering`](#engineering) | Things | 7 skills, 1 subagent |\n"
    write_readme(mini_repo, README.replace(row, linked) + "\n### Engineering\n")
    assert readme.check(mini_repo) == 1
    assert "says engineering has 7 skills, and it has 2" in capsys.readouterr().out


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


def test_a_plugin_over_the_default_also_reports_what_it_costs_in_tokens(mini_repo, capsys):
    # The character figure on its own reads as worse than it is: 8,000 characters is a
    # stand-in for 2,000 tokens that assumes four characters to the token, and this
    # library measures 4.63. A reader deciding whether to raise a ceiling needs the pair.
    budget.check(mini_repo, update=True)
    sizes = budget.measure(mini_repo)
    monkey = budget.RUNTIME_DEFAULT
    budget.RUNTIME_DEFAULT = 1
    try:
        assert budget.check(mini_repo) == 0
    finally:
        budget.RUNTIME_DEFAULT = monkey
    out = capsys.readouterr().out
    expected = sizes["engineering"] / budget.CHARS_PER_TOKEN
    assert f"about {expected:,.0f} tokens" in out
    assert "of a 200k window" in out


def test_the_recorded_ratio_stays_a_plausible_one():
    # A typo here would silently understate or overstate every token figure the report
    # prints. English prose through this tokenizer family does not leave this range.
    assert 4.0 < budget.CHARS_PER_TOKEN < 5.5
    assert budget.CONTEXT_WINDOW_TOKENS == 200_000


def test_the_regenerated_comment_explains_the_character_to_token_gap(mini_repo):
    # write() rebuilds the whole file, so a note added to listing-budget.json by hand is
    # erased by the next --update. The explanation has to live in the writer to survive.
    budget.check(mini_repo, update=True)
    data = json.loads((mini_repo / budget.BUDGET_FILE).read_text(encoding="utf-8"))
    assert f"{budget.CHARS_PER_TOKEN} characters per token" in data["_comment"]
    # Derived, not restated: re-measuring and changing the constant must move this too,
    # or the file goes on asserting a ratio the report has stopped using.
    tokens = budget.RUNTIME_DEFAULT / budget.CHARS_PER_TOKEN
    assert f"about {tokens:,.0f} tokens" in data["_comment"]


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


# --- the portable export --------------------------------------------------------------

portable = load_script("export_portable.py")


def test_a_reference_is_inlined_and_its_pointer_rewritten(mini_repo):
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    (skill / "references").mkdir()
    (skill / "references" / "depth.md").write_text(
        "# Going deeper\n\n## A sub-heading\n\nDetail.\n", encoding="utf-8"
    )
    source = skill / "SKILL.md"
    source.write_text(
        source.read_text(encoding="utf-8") + "\nRead `references/depth.md` when stuck.\n",
        encoding="utf-8",
    )
    name, _, document, unresolved = portable.render_skill(skill)
    assert name == "alpha"
    assert unresolved == []
    # The path is gone and the section it named is present, which is the whole job:
    # a reader with no filesystem can still follow the pointer.
    assert "references/depth.md" not in document
    assert 'the "Going deeper" section below' in document
    assert "### Going deeper" in document
    assert "##### A sub-heading" in document  # demoted so it nests


def test_a_pointer_to_a_file_that_is_gone_is_reported_not_swallowed(mini_repo):
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    source = skill / "SKILL.md"
    source.write_text(
        source.read_text(encoding="utf-8") + "\nRead `references/missing.md`.\n", encoding="utf-8"
    )
    _, _, document, unresolved = portable.render_skill(skill)
    assert unresolved == ["references/missing.md"]
    assert "references/missing.md" in document  # left as written, so the report matches


def test_a_path_in_a_worked_example_is_not_treated_as_a_pointer(mini_repo):
    # A reference file quoting the reader's own project layout is the false positive
    # that a whole-document scan produces, and it would fail every export.
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    (skill / "references").mkdir()
    (skill / "references" / "depth.md").write_text(
        "# Depth\n\nShip `assets/LICENSES.md` with the build.\n", encoding="utf-8"
    )
    source = skill / "SKILL.md"
    source.write_text(
        source.read_text(encoding="utf-8") + "\nRead `references/depth.md`.\n", encoding="utf-8"
    )
    _, _, _, unresolved = portable.render_skill(skill)
    assert unresolved == []


def test_a_nested_reference_is_inlined_and_its_pointer_rewritten(mini_repo):
    """The local pointer regex this export used to carry only matched a flat
    `references/<x>.md`, so a nested one was neither inlined nor reported: the pointer
    stayed in the document unresolved and `unresolved` stayed empty, which is exactly
    the silent failure the validator's own regex exists to catch."""
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    (skill / "references" / "deep").mkdir(parents=True)
    (skill / "references" / "deep" / "topic.md").write_text(
        "# Deep topic\n\nDetail.\n", encoding="utf-8"
    )
    source = skill / "SKILL.md"
    source.write_text(
        source.read_text(encoding="utf-8") + "\nRead `references/deep/topic.md` when stuck.\n",
        encoding="utf-8",
    )
    name, _, document, unresolved = portable.render_skill(skill)
    assert name == "alpha"
    assert unresolved == []
    assert "references/deep/topic.md" not in document
    assert 'the "Deep topic" section below' in document


def test_a_non_markdown_asset_is_inlined_and_its_pointer_rewritten(mini_repo):
    """`assets/*.md` was the only asset extension the local regex matched, so
    `assets/checklist.txt` was neither inlined nor reported — the same silent gap the
    nested-reference case above exercises for `references/`."""
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    (skill / "assets").mkdir()
    (skill / "assets" / "checklist.txt").write_text("- one\n- two\n", encoding="utf-8")
    source = skill / "SKILL.md"
    source.write_text(
        source.read_text(encoding="utf-8") + "\nFill in `assets/checklist.txt` first.\n",
        encoding="utf-8",
    )
    name, _, document, unresolved = portable.render_skill(skill)
    assert name == "alpha"
    assert unresolved == []
    assert "`assets/checklist.txt`" not in document  # the raw pointer is gone
    assert 'the "assets/checklist.txt" section below' in document
    assert "### assets/checklist.txt" in document
    assert "- one" in document and "- two" in document
    # A .txt asset is fenced as `text`, not the `markdown` every asset used to get
    # regardless of its own extension.
    assert "```text" in document
    assert "```markdown" not in document


def test_an_asset_language_is_read_from_its_extension(mini_repo):
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    (skill / "assets").mkdir()
    (skill / "assets" / "config.yaml").write_text("key: value\n", encoding="utf-8")
    (skill / "assets" / "unknown.xyz").write_text("opaque\n", encoding="utf-8")
    _, _, document, _ = portable.render_skill(skill)
    assert "```yaml" in document
    assert "```text" in document  # the fallback for an extension with no mapping


def test_a_script_section_is_titled_by_its_path_not_its_first_comment(mini_repo):
    """A script's title used to come from its first `# ` line — an ordinary shell
    comment, not a heading — so a script whose first line explained something unrelated
    became the section title. The relative path always tells the reader which file to
    create, which is the point of inlining a script at all."""
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    (skill / "scripts").mkdir()
    (skill / "scripts" / "bisect-probe.sh").write_text(
        "#!/bin/sh\n# Not a title, just an ordinary comment\necho ok\n", encoding="utf-8"
    )
    source = skill / "SKILL.md"
    source.write_text(
        source.read_text(encoding="utf-8") + "\nRun `scripts/bisect-probe.sh` to check.\n",
        encoding="utf-8",
    )
    _, _, document, unresolved = portable.render_skill(skill)
    assert unresolved == []
    assert "### scripts/bisect-probe.sh" in document
    assert "### Not a title, just an ordinary comment" not in document


def test_headings_inside_a_code_fence_are_left_alone():
    text = "# Title\n\n```bash\n# not a heading, a comment\nls\n```\n\n## Real\n"
    out = portable.demote(text, 2)
    assert "### Title" in out
    assert "# not a heading, a comment" in out
    assert "#### Real" in out


def test_the_document_has_exactly_one_top_level_heading(mini_repo):
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    _, _, document, _ = portable.render_skill(skill)
    assert [line for line in document.split("\n") if line.startswith("# ")].__len__() == 1


def test_an_asset_is_inlined_as_a_fenced_template(mini_repo):
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    (skill / "assets").mkdir()
    (skill / "assets" / "template.md").write_text("# Template\n\nFill this in.\n", encoding="utf-8")
    _, _, document, _ = portable.render_skill(skill)
    assert "```markdown" in document
    assert "Fill this in." in document


def test_export_writes_a_file_per_skill_a_bundle_per_plugin_and_an_index(mini_repo, tmp_path):
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    assert sorted(p.name for p in (out / "skills").glob("*.md")) == ["alpha.md", "beta.md"]
    assert (out / "plugins" / "engineering.md").is_file()
    index = (out / "index.md").read_text(encoding="utf-8")
    assert "- **alpha**" in index and "- **beta**" in index
    assert (out / "README.md").is_file()


def test_export_writes_license_and_notice_at_the_output_root(mini_repo, tmp_path):
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    assert (out / "LICENSE").read_text(encoding="utf-8") == (mini_repo / "LICENSE").read_text(
        encoding="utf-8"
    )
    assert (out / "NOTICE").read_text(encoding="utf-8") == (mini_repo / "NOTICE").read_text(
        encoding="utf-8"
    )


def test_export_fails_loudly_with_no_repository_license(mini_repo, tmp_path, capsys):
    (mini_repo / "LICENSE").unlink()
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 2
    assert "no LICENSE at the repository root" in capsys.readouterr().err
    assert not out.exists()


def test_export_does_not_hide_a_plugin_skill_named_template(mini_repo, tmp_path):
    """`export` walks `find_skills(plugin / "skills")` per plugin — the same narrowed
    `root` that used to make a `skills/template/` skill look like the repository's own
    template and drop it from the export, so `--check` reported the tree as clean while
    one fewer skill than actually shipped ever reached `dist/portable`."""
    write_skill(mini_repo, "engineering", "template")
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    assert (out / "skills" / "template.md").is_file()


def test_every_exported_file_carries_the_attribution_notice(mini_repo, tmp_path):
    # A flattened skill is the copy most likely to leave the repository, and MIT makes
    # keeping the notice a condition of every copy. Before this footer existed the
    # export shipped nothing a reader could trace back.
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    for path in [*(out / "skills").glob("*.md"), *(out / "plugins").glob("*.md")]:
        text = path.read_text(encoding="utf-8")
        assert portable.NOTICE in text, path.name
        assert text.rstrip().endswith(portable.NOTICE.rstrip()), f"{path.name} not last"
    assert "greenblacked/AI" in (out / "README.md").read_text(encoding="utf-8")


def test_check_reports_without_writing(mini_repo, tmp_path, capsys):
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out, check=True) == 0
    assert not out.exists()
    assert "export is clean" in capsys.readouterr().out


def test_check_fails_on_a_pointer_that_would_not_survive_the_export(mini_repo, tmp_path, capsys):
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    source = skill / "SKILL.md"
    source.write_text(
        source.read_text(encoding="utf-8") + "\nRead `references/missing.md`.\n", encoding="utf-8"
    )
    assert portable.export(mini_repo, tmp_path / "portable", check=True) == 1
    assert "still points at references/missing.md" in capsys.readouterr().out


def test_export_rewrites_the_output_directory(mini_repo, tmp_path):
    # The directory has to be a real previous export, not merely an existing one —
    # `_unsafe_to_remove` refuses to delete anything else, so the "stale" content here is
    # left over from a first, genuine run rather than hand-built to look like one.
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    (out / "stale.md").write_text("from an older run", encoding="utf-8")
    assert portable.export(mini_repo, out) == 0
    assert not (out / "stale.md").exists()


def test_export_reports_a_tree_with_no_plugins(tmp_path):
    assert portable.main([str(tmp_path)]) == 2


# --- the router --------------------------------------------------------------------


def test_first_sentence_trims_to_the_cap():
    # Short enough to survive whole: the cap is a ceiling, not a target length.
    assert portable.first_sentence("Do the thing. Then another.", 100) == "Do the thing."
    # Long enough to need trimming: cut inside the cap and marked as cut, rather than
    # silently reading as a complete, if oddly short, sentence.
    long_sentence = " ".join(["word"] * 20) + "."
    trimmed = portable.first_sentence(long_sentence, 20)
    assert len(trimmed) <= 20
    assert trimmed.endswith("…")


def test_first_sentence_hard_cuts_a_single_overlong_word():
    # A leading word longer than the cap has no space inside it to cut at; falling back
    # to a hard cut keeps this a short, honestly truncated line instead of an empty one.
    long_sentence = "x" * 200 + " thing."
    trimmed = portable.first_sentence(long_sentence, 20)
    assert len(trimmed) == 20
    assert trimmed.endswith("…")


def test_first_sentence_prefers_a_later_use_when_sentence():
    # agent-handoff, profiling, refactoring and other skills here put the sentence naming
    # when they apply after a first sentence that summarises the procedure instead — the
    # router line should name the situation, not the summary.
    description = (
        "Summarise the whole procedure in one dense opening line. Use when someone asks "
        "for exactly this. Further detail that never gets read here."
    )
    assert portable.first_sentence(description, 200) == ("Use when someone asks for exactly this.")
    # With no such sentence, the first one is exactly what ships.
    assert portable.first_sentence("Just one plain sentence.", 200) == "Just one plain sentence."


def test_first_sentence_cuts_at_a_word_boundary():
    description = "Handle the incoming webhook payload safely before anything else runs."
    trimmed = portable.first_sentence(description, 30)
    # Cut after a whole word ("webhook"), not mid-word ("webho…") — the untrimmed word
    # immediately before the ellipsis has to appear whole in the original sentence.
    assert trimmed == "Handle the incoming webhook…"
    assert trimmed[:-1].rsplit(" ", 1)[-1] in description.split()


def test_first_sentence_does_not_split_on_common_abbreviations():
    description = "Fix the root cause, e.g. a null pointer, not the symptom. Then verify."
    assert portable.first_sentence(description, 200) == (
        "Fix the root cause, e.g. a null pointer, not the symptom."
    )
    description = "Cover the common cases, etc. before the rare ones. Then ship."
    assert portable.first_sentence(description, 200) == (
        "Cover the common cases, etc. before the rare ones."
    )
    description = "Rotate the credential, i.e. the API key, before it expires. Then verify."
    assert portable.first_sentence(description, 200) == (
        "Rotate the credential, i.e. the API key, before it expires."
    )


@pytest.mark.parametrize(
    "opening",
    ["Use this skill whenever", "Use whenever", "Use for", "Use this when", "Trigger"],
)
def test_first_sentence_recognises_every_use_when_shape(opening):
    # Descriptions here phrase the "when it applies" sentence several ways; each has to
    # win over the summary sentence that comes first, not only the two literal openers
    # ("use when", "use this when") the router used to look for.
    description = f"Summarise the procedure first. {opening} the situation applies here."
    assert portable.first_sentence(description, 200) == f"{opening} the situation applies here."


def test_first_sentence_prefers_an_earlier_use_sentence_over_a_later_trigger_sentence():
    # learning-notes and health-coach both open with "Use this skill whenever..." and add
    # a later "Trigger ... casual phrasings" sentence; the router line should resolve to
    # the earlier, more specific sentence rather than the later, supplementary one.
    description = (
        "Use this skill whenever someone pastes an article to keep. Trigger on casual "
        'phrasings too, like "worth keeping?".'
    )
    assert portable.first_sentence(description, 200) == (
        "Use this skill whenever someone pastes an article to keep."
    )


def test_first_sentence_is_linear_in_the_length_of_an_unterminated_description():
    # No ".", "!" or "?" anywhere: the old lazy `.*?` scan tried every starting position
    # in turn and rescanned to the end of the text each time it found no terminator,
    # quadratic in the length of the text. This asserts only that the call returns a
    # sensibly trimmed result, not a time budget — a quadratic regression here is slow
    # enough that the test would hang rather than needing a clock to catch it.
    text = "word " * 20_000  # 100,000 characters
    assert len(text) == 100_000
    trimmed = portable.first_sentence(text, 40)
    assert len(trimmed) <= 40
    assert trimmed.endswith("…")


def test_export_writes_a_router_and_one_per_plugin(mini_repo, tmp_path):
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    assert (out / "router.md").is_file()
    # mini_repo carries exactly one plugin, named engineering.
    assert (out / "router-engineering.md").is_file()
    router = (out / "router.md").read_text(encoding="utf-8")
    assert "## engineering" in router
    assert "- [alpha](skills/alpha.md):" in router
    assert "- [beta](skills/beta.md):" in router
    per_plugin = (out / "router-engineering.md").read_text(encoding="utf-8")
    assert "- [alpha](skills/alpha.md):" in per_plugin
    assert "- [beta](skills/beta.md):" in per_plugin


def test_every_path_a_router_names_exists_in_the_export(mini_repo, tmp_path):
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    for router_path in [out / "router.md", out / "router-engineering.md"]:
        text = router_path.read_text(encoding="utf-8")
        paths = re.findall(r"\]\((skills/[\w.-]+\.md)\)", text)
        assert paths, router_path.name  # the pattern itself must find something to check
        for relative in paths:
            assert (out / relative).is_file(), f"{router_path.name} names {relative}"


def test_router_keeps_each_skill_trigger_and_single_link(mini_repo, tmp_path):
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    for skill in ("alpha", "beta"):
        description = portable.render_skill(
            mini_repo / "plugins" / "engineering" / "skills" / skill
        )[1]
        trigger = portable.first_sentence(description, portable.ROUTER_USE_WHEN_CAP)
        line = f"- [{skill}](skills/{skill}.md): {trigger}"
        for router in ("router.md", "router-engineering.md"):
            text = (out / router).read_text(encoding="utf-8")
            assert text.count(line) == 1


def test_router_over_budget_fails_without_touching_a_previous_export(
    mini_repo, tmp_path, monkeypatch, capsys
):
    # A budget smaller than the preamble alone makes every router fail, whatever the
    # skills measure — the point is only that the check fires and stops the export.
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    before = {path: path.read_bytes() for path in out.rglob("*") if path.is_file()}

    monkeypatch.setattr(portable, "ROUTER_BUDGET_BYTES", 10)
    assert portable.export(mini_repo, out) == 1
    message = capsys.readouterr().err
    assert "router.md is" in message
    assert "against a budget of 10" in message
    # The router budget is checked, from the rendered skills alone, before `out` is
    # touched at all — the same reason LICENSE/NOTICE are checked before shutil.rmtree,
    # rather than after a partial export already exists. A real previous export,
    # sentinel and all, survives an over-budget run completely unchanged.
    assert (out / portable.EXPORT_SENTINEL).is_file()
    after = {path: path.read_bytes() for path in out.rglob("*") if path.is_file()}
    assert after == before


def test_router_over_budget_fails_check_mode_too(mini_repo, tmp_path, monkeypatch):
    monkeypatch.setattr(portable, "ROUTER_BUDGET_BYTES", 10)
    assert portable.export(mini_repo, tmp_path / "portable", check=True) == 1


# --- the rmtree safety guard -------------------------------------------------------


def test_export_refuses_to_delete_the_repository_root(mini_repo, tmp_path, capsys):
    # `--out .` pointed at the repository root, or any ancestor of it, used to be handed
    # straight to shutil.rmtree.
    assert portable.export(mini_repo, mini_repo) == 2
    assert "refusing to delete" in capsys.readouterr().err


def test_export_refuses_to_delete_an_ancestor_of_the_repository(mini_repo, tmp_path, capsys):
    assert portable.export(mini_repo, mini_repo.parent) == 2
    assert "refusing to delete" in capsys.readouterr().err


def test_export_refuses_to_delete_the_home_directory(mini_repo, tmp_path, monkeypatch, capsys):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(portable.Path, "home", staticmethod(lambda: fake_home))
    assert portable.export(mini_repo, fake_home) == 2
    assert "refusing to delete" in capsys.readouterr().err


def test_export_refuses_to_delete_a_directory_that_is_not_a_previous_export(
    mini_repo, tmp_path, capsys
):
    # An existing directory with no marker of this script's own making is left alone
    # rather than guessed at — the whole tree it might be is not this export's to judge.
    out = tmp_path / "not-an-export"
    out.mkdir()
    (out / "notes.txt").write_text("someone else's files", encoding="utf-8")
    assert portable.export(mini_repo, out) == 2
    message = capsys.readouterr().err
    assert "refusing to delete" in message
    # The message has to say what to do about it, not just that it refused.
    assert "delete the directory yourself if you are sure" in message
    assert (out / "notes.txt").exists()


def test_export_deletes_a_directory_that_is_a_previous_export(mini_repo, tmp_path):
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    # A second run over its own prior output is exactly the case the guard has to allow.
    assert portable.export(mini_repo, out) == 0


def test_export_writes_a_sentinel_file(mini_repo, tmp_path):
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    assert (out / portable.EXPORT_SENTINEL).is_file()


def test_a_sentinel_alone_is_recognised_as_a_previous_export_even_if_the_readme_changed(
    mini_repo, tmp_path
):
    # The marker's whole point is to survive a prose edit to HOW_TO_USE: a directory
    # from an export whose README no longer matches the current text verbatim must
    # still be recognised, or every future export refuses to overwrite the last one
    # purely because the README was reworded in between.
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    (out / "README.md").write_text("some future, reworded README\n", encoding="utf-8")
    assert portable.export(mini_repo, out) == 0
    assert (out / "README.md").read_text(encoding="utf-8") == portable.HOW_TO_USE


# --- shell that ships or is printed ----------------------------------------------------

shell = load_script("check_shell.py")


def test_a_block_that_parses_is_accepted():
    assert shell.parses("set -Eeuo pipefail\nif [ -f x ]; then echo y; fi\n") is None


def test_an_unbalanced_quote_is_caught():
    assert shell.parses('echo "unterminated\n') is not None


def test_a_placeholder_is_documentation_not_a_defect():
    # Eleven of this repository's blocks "failed" before this substitution and every one
    # was a placeholder. A gate that fails on the documentation convention is all noise.
    assert shell.parses("git bisect start <known-bad-sha> <known-good-sha>\n") is None
    assert shell.parses("kubectl logs <pod> -c <container>\n") is None


def test_a_real_redirection_is_still_checked():
    # The placeholder pattern has to start with a letter, or it swallows redirections
    # and here-strings and the check stops seeing half the shell it was written for.
    assert shell.parses("cat <&-\ndone\n") is not None


def test_javascript_tagged_as_shell_is_caught():
    # The one real defect this found in the repository: a browser console snippet in a
    # ```bash fence, which an agent told to run every command it prints would try.
    source = "[...document.querySelectorAll('*')].filter(e => e.scrollWidth > 0)\n"
    assert shell.parses(source) is not None


def test_blocks_finds_each_fence_with_its_line_number():
    text = "intro\n\n```bash\necho one\n```\n\ntext\n\n```sh\necho two\n```\n"
    assert list(shell.blocks(text)) == [(4, "echo one"), (10, "echo two")]


def test_an_untagged_or_other_language_fence_is_left_alone():
    text = "```python\nnot shell at all(\n```\n\n```\nplain\n```\n"
    assert list(shell.blocks(text)) == []


def test_check_passes_on_a_tree_with_good_shell(tmp_path, capsys):
    (tmp_path / "plugins").mkdir()
    (tmp_path / "plugins" / "a.md").write_text("```bash\nset -Eeuo pipefail\nls\n```\n", "utf-8")
    assert shell.check(tmp_path) == 0
    assert "1 shell block(s) parsed" in capsys.readouterr().out


def test_check_fails_and_names_the_line(tmp_path, capsys):
    (tmp_path / "plugins").mkdir()
    (tmp_path / "plugins" / "a.md").write_text("intro\n\n```bash\nif true\n```\n", "utf-8")
    assert shell.check(tmp_path) == 1
    assert "file=plugins/a.md,line=4" in capsys.readouterr().out


def test_check_scans_root_level_markdown_too(tmp_path, capsys):
    # README.md, AGENTS.md and CONTRIBUTING.md live at the repository root, not inside
    # any of plugins/, docs/, scripts/, .claude/ or template/ — the five directories
    # SEARCH_DIRS names — so a broken fence in one of them used to ship unchecked.
    (tmp_path / "plugins").mkdir()
    (tmp_path / "README.md").write_text("intro\n\n```bash\nif true\n```\n", "utf-8")
    assert shell.check(tmp_path) == 1
    assert "file=README.md,line=4" in capsys.readouterr().out


def test_a_shipped_script_is_checked_too(tmp_path, capsys):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "broken.sh").write_text("#!/usr/bin/env bash\nif true\n", "utf-8")
    assert shell.check(tmp_path) == 1
    assert "is not valid shell" in capsys.readouterr().out


def test_an_empty_block_is_not_counted(tmp_path, capsys):
    (tmp_path / "plugins").mkdir()
    (tmp_path / "plugins" / "a.md").write_text("```bash\n\n```\n", "utf-8")
    assert shell.check(tmp_path) == 0
    assert "0 shell block(s) parsed" in capsys.readouterr().out


def test_main_accepts_a_root(tmp_path):
    (tmp_path / "plugins").mkdir()
    assert shell.main([str(tmp_path)]) == 0


# `bash -n` proves a block parses, not that it runs, and `.claude/rules/skills.md` asks
# for the second. This is the one mechanically checkable case: ripgrep's default engine
# has no lookaround at all, so a pattern using it is a parse error at the keyboard while
# the shell around it is perfectly valid. It shipped once, in pipeline-hardening, and was
# caught by a person running the command rather than by any gate.


@pytest.mark.parametrize(
    "command",
    [
        r"""rg -n 'uses:\s*[^@]+@(?!\w{40})' .github/workflows/*.yml""",  # the one that shipped
        "rg 'a(?=b)' .",
        "rg 'a(?<=b)' .",
        "rg 'a(?<!b)' .",
        "cat x | rg 'a(?!b)'",  # after a pipe
        "ripgrep 'a(?!b)' .",  # spelled out
        "if rg -q 'a(?!b)' .; then :; fi",  # the common conditional form
        "xargs rg 'a(?!b)'",
        "/usr/bin/rg 'a(?!b)' .",  # an absolute path
    ],
)
def test_lookaround_without_pcre2_is_caught(command):
    assert shell.rg_without_pcre2(command)


@pytest.mark.parametrize(
    "command",
    [
        "rg -P 'a(?!b)' .",
        "rg -nP 'a(?!b)' .",  # bundled into a short-flag run
        "rg --pcre2 'a(?!b)' .",
        "rg --auto-hybrid-regex 'a(?!b)' .",
        "grep -P 'a(?!b)' file",  # grep has lookaround without a flag
        "rg 'a(?i)b' .",  # an inline flag group, not lookaround
        "# rg 'a(?!b)' .",  # a comment is not a command anyone runs
        "rg --engine pcre2 'a(?!b)' .",  # the documented spelling
        "rg --engine=pcre2 'a(?!b)' .",
        "rg --engine auto 'a(?!b)' .",
        "rg -Pn 'a(?!b)' .",  # P need not be last in the bundle
        "rg -F '(?!' plugins/",  # a literal search for the defect is not the defect
        "rg --fixed-strings '(?!' .",
        "rg -nF '(?!' .",
        r"rg -n '^\s*(- )?uses:\s*\S+@' .",  # the anchored form that replaced it
    ],
)
def test_what_the_lookaround_check_leaves_alone(command):
    assert not shell.rg_without_pcre2(command)


def test_a_comment_ending_in_a_backslash_does_not_swallow_the_next_command():
    # bash does not continue a comment. Joining them anyway drops whatever follows,
    # which would make a stray trailing backslash switch the check off silently.
    assert shell.rg_without_pcre2("# see foo \\\nrg 'a(?!b)' .")


def test_a_continuation_line_is_one_command():
    # The flag that would make it legal is as likely to be on the second line as the
    # first, so the two have to be judged together.
    assert not shell.rg_without_pcre2("rg 'a(?!b)' \\\n  -P .")
    assert shell.rg_without_pcre2("rg 'a(?!b)' \\\n  --glob '*.md'")


def test_a_block_with_lookaround_fails_and_names_the_line(tmp_path, capsys):
    (tmp_path / "plugins").mkdir()
    (tmp_path / "plugins" / "a.md").write_text(
        "intro\n\n```bash\nls\nrg 'x(?!y)' .\n```\n", "utf-8"
    )
    assert shell.check(tmp_path) == 1
    out = capsys.readouterr().out
    assert "file=plugins/a.md,line=5" in out
    assert "lookaround needs -P" in out


def test_a_shipped_script_with_lookaround_is_caught_too(tmp_path, capsys):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "s.sh").write_text("#!/usr/bin/env bash\nrg 'x(?!y)' .\n", "utf-8")
    assert shell.check(tmp_path) == 1
    assert "lookaround needs -P" in capsys.readouterr().out


def test_a_nested_shorter_fence_does_not_close_a_longer_one():
    # A four-backtick block quoting a three-backtick example is one block. Closing on
    # the inner fence makes the rest of the block parse as prose, and the failure is
    # reported against the author rather than against the scanner.
    text = "````bash\nls\n```\nstill inside\n````\n"
    assert list(shell.blocks(text)) == [(2, "ls\n```\nstill inside")]


def test_an_unterminated_fence_is_checked_rather_than_skipped():
    # It runs to the end of the file. That is the safe direction for this check: the
    # worst case is a false positive somebody reads, where skipping would turn the gate
    # off for everything after the unclosed fence and say nothing.
    [(line, source)] = list(shell.blocks("```bash\nls\n"))
    assert line == 2
    assert source.strip() == "ls"


def test_demotion_leaves_a_comment_inside_a_nested_fence_alone():
    # The same rule, in the exporter: `# inner` is a shell comment, and rewriting it as
    # a heading corrupts a command the reader is meant to run.
    text = "# Title\n\n````markdown\n```bash\n# inner comment\n```\n````\n\n## After\n"
    out = portable.demote(text, 2)
    assert "# inner comment" in out
    assert "### inner comment" not in out
    assert "### Title" in out
    assert "#### After" in out


def test_demotion_handles_a_tilde_fence_and_clamps_at_six():
    assert "# comment" in portable.demote("~~~bash\n# comment\n~~~\n", 2)
    assert portable.demote("###### Deep\n", 2).strip() == "###### Deep"


def test_a_shipped_script_is_inlined_and_its_command_left_runnable(mini_repo):
    # The defect this was written for: `git bisect run ./scripts/probe.sh` reached a
    # reader with no such file. The script is now in the document — but the command
    # still has to say a path, because a command is not prose.
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    (skill / "scripts").mkdir()
    (skill / "scripts" / "probe.sh").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    source = skill / "SKILL.md"
    source.write_text(
        source.read_text(encoding="utf-8")
        + "\nHand it `scripts/probe.sh`.\n\n```bash\ngit bisect run ./scripts/probe.sh\n```\n",
        encoding="utf-8",
    )
    _, _, document, unresolved = portable.render_skill(skill)
    assert unresolved == []
    assert "git bisect run ./scripts/probe.sh" in document  # the command survives intact
    assert "```bash\n#!/usr/bin/env bash" in document  # the script is there to create
    assert "Hand it the " in document  # the prose pointer became a section name


def test_a_pointer_inside_a_reference_file_is_rewritten_too(mini_repo):
    # A reference that sends you to a sibling reference is as much a dangling pointer,
    # for a reader with no filesystem, as one in the body — and it is not in the body,
    # so the first version of this export never touched it.
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    (skill / "references").mkdir()
    (skill / "references" / "first.md").write_text(
        "# First\n\nGo on to `references/second.md` for the rest.\n", encoding="utf-8"
    )
    (skill / "references" / "second.md").write_text("# Second\n\nThe rest.\n", encoding="utf-8")
    source = skill / "SKILL.md"
    source.write_text(
        source.read_text(encoding="utf-8") + "\nStart at `references/first.md`.\n", encoding="utf-8"
    )
    _, _, document, _ = portable.render_skill(skill)
    assert "references/second.md" not in document
    assert 'the "Second" section below' in document


def test_a_path_inside_a_code_block_is_not_counted_as_a_pointer(mini_repo):
    # Otherwise a worked example showing the reader's own project layout becomes a
    # dangling pointer, and the export fails on a skill that is correct.
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    source = skill / "SKILL.md"
    source.write_text(
        source.read_text(encoding="utf-8") + "\n```text\nreferences/theirs.md\n```\n",
        encoding="utf-8",
    )
    _, _, document, unresolved = portable.render_skill(skill)
    assert unresolved == []
    assert "references/theirs.md" in document


def test_an_inlined_reference_does_not_repeat_its_own_title(mini_repo):
    skill = mini_repo / "plugins" / "engineering" / "skills" / "alpha"
    (skill / "references").mkdir()
    (skill / "references" / "depth.md").write_text("# Going deeper\n\nDetail.\n", encoding="utf-8")
    _, _, document, _ = portable.render_skill(skill)
    assert document.count("Going deeper") == 1


def test_a_prose_count_that_disagrees_with_the_tree_is_caught(mini_repo, capsys):
    # The defect this check was added for: the opening sentence said seven slash commands
    # while six shipped, and it survived several merges because the table and the badge
    # were right and nothing read the sentence.
    write_readme(mini_repo, README + "\nThis library has three skills, in one plugin.\n")
    assert readme.check(mini_repo) == 1
    assert "says three skills, and there are 2" in capsys.readouterr().out


def test_a_prose_count_written_in_digits_is_caught(mini_repo, capsys):
    write_readme(mini_repo, README + "\nAll 9 skills are listed above.\n")
    assert readme.check(mini_repo) == 1
    assert "says 9 skills, and there are 2" in capsys.readouterr().out


def test_a_correct_prose_count_passes(mini_repo, capsys):
    write_readme(mini_repo, README + "\nTwo skills and one subagent ship here.\n")
    assert readme.check(mini_repo) == 0


def test_ordinary_prose_about_skills_is_not_read_as_a_count(mini_repo, capsys):
    # The reason this check was left out once: a gate that fails on correct prose is one
    # people learn to override. A word before the noun is only a count when it is a
    # number, so "installed skills" and "the subagents" have to stay silent.
    write_readme(
        mini_repo,
        README + "\nThe installed skills load on demand, and the subagents do not.\n",
    )
    assert readme.check(mini_repo) == 0


def test_a_per_plugin_count_in_a_table_is_not_read_as_a_repository_total(mini_repo, capsys):
    # The contents row says "2 skills" for one plugin. Read as a repository total in a
    # tree with more plugins it would be wrong, so table rows are excluded by line.
    write_readme(mini_repo, README)
    assert readme.check(mini_repo) == 0
    assert "says 2 skills" not in capsys.readouterr().out


def test_a_count_inside_a_fenced_block_is_not_checked(mini_repo, capsys):
    # A fenced block is a transcript or an example, not a claim about this tree.
    write_readme(mini_repo, README + "\n```text\nFound 40 skills\n```\n")
    assert readme.check(mini_repo) == 0


# --- badges that state what CI enforces --------------------------------------------------

PYTHON_BADGE = (
    "[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11-3776ab)](pyproject.toml)\n"
)
COVERAGE_BADGE = (
    "[![Coverage](https://img.shields.io/badge/coverage-%E2%89%A595%25-22c55e)](pyproject.toml)\n"
)


def write_ci_matrix(root, versions):
    workflow = root / ".github" / "workflows"
    workflow.mkdir(parents=True, exist_ok=True)
    quoted = ", ".join(f"'{v}'" for v in versions)
    (workflow / "ci.yml").write_text(
        f"jobs:\n  test:\n    strategy:\n      matrix:\n        python-version: [{quoted}]\n",
        encoding="utf-8",
    )


def write_coverage_floor(root, floor):
    (root / "pyproject.toml").write_text(
        f"[tool.coverage.report]\nfail_under = {floor}\n", encoding="utf-8"
    )


def test_without_a_matrix_or_a_floor_neither_badge_is_required(mini_repo):
    # The fixture repository declares neither, and a badge for a guarantee the tree
    # does not make would be the stale-number problem in reverse.
    write_readme(mini_repo, README)
    assert readme.check(mini_repo) == 0


def test_a_python_badge_matching_the_matrix_passes(mini_repo):
    write_ci_matrix(mini_repo, ["3.10", "3.11"])
    write_readme(mini_repo, README.replace("\n| Plugin", PYTHON_BADGE + "\n| Plugin", 1))
    assert readme.check(mini_repo) == 0


def test_a_python_badge_that_disagrees_with_the_matrix_is_caught(mini_repo, capsys):
    # The matrix gained a version and the badge did not: the README now understates
    # the portability guarantee the four-interpreter run exists to make.
    write_ci_matrix(mini_repo, ["3.10", "3.11", "3.12"])
    write_readme(mini_repo, README.replace("\n| Plugin", PYTHON_BADGE + "\n| Plugin", 1))
    assert readme.check(mini_repo) == 1
    assert (
        "the python badge says 3.10, 3.11, and CI tests 3.10, 3.11, 3.12" in capsys.readouterr().out
    )


def test_a_missing_python_badge_is_caught_when_ci_has_a_matrix(mini_repo, capsys):
    write_ci_matrix(mini_repo, ["3.10"])
    write_readme(mini_repo, README)
    assert readme.check(mini_repo) == 1
    assert "no python badge" in capsys.readouterr().out


def test_a_coverage_badge_matching_the_floor_passes(mini_repo):
    write_coverage_floor(mini_repo, 95)
    write_readme(mini_repo, README.replace("\n| Plugin", COVERAGE_BADGE + "\n| Plugin", 1))
    assert readme.check(mini_repo) == 0


def test_a_coverage_badge_that_disagrees_with_the_floor_is_caught(mini_repo, capsys):
    # The badge states the floor, not a live figure, precisely so that this comparison
    # is possible: a floor is something the tree declares and a gate can read.
    write_coverage_floor(mini_repo, 90)
    write_readme(mini_repo, README.replace("\n| Plugin", COVERAGE_BADGE + "\n| Plugin", 1))
    assert readme.check(mini_repo) == 1
    assert (
        "the coverage badge says 95, and pyproject.toml fails below 90" in capsys.readouterr().out
    )


def test_a_missing_coverage_badge_is_caught_when_a_floor_is_declared(mini_repo, capsys):
    write_coverage_floor(mini_repo, 95)
    write_readme(mini_repo, README)
    assert readme.check(mini_repo) == 1
    assert "no badge stating it" in capsys.readouterr().out


def test_a_python_badge_with_no_matrix_behind_it_is_caught(mini_repo, capsys):
    # The reverse direction. Remove the matrix and the badge keeps advertising a
    # guarantee nothing enforces, which is the trigger-eval badge this check refused.
    write_readme(mini_repo, README.replace("\n| Plugin", PYTHON_BADGE + "\n| Plugin", 1))
    assert readme.check(mini_repo) == 1
    assert "no interpreter matrix to back it" in capsys.readouterr().out


def test_a_coverage_badge_with_no_floor_behind_it_is_caught(mini_repo, capsys):
    write_readme(mini_repo, README.replace("\n| Plugin", COVERAGE_BADGE + "\n| Plugin", 1))
    assert readme.check(mini_repo) == 1
    assert "pyproject.toml sets none" in capsys.readouterr().out


def test_a_double_quoted_matrix_is_read(mini_repo):
    # The workflow's quoting style is not the contract; a rewrite to double quotes must
    # not make the gate go blind.
    workflow = mini_repo / ".github" / "workflows"
    workflow.mkdir(parents=True, exist_ok=True)
    (workflow / "ci.yml").write_text(
        'jobs:\n  test:\n    strategy:\n      matrix:\n        python-version: ["3.10", "3.11"]\n',
        encoding="utf-8",
    )
    write_readme(mini_repo, README.replace("\n| Plugin", PYTHON_BADGE + "\n| Plugin", 1))
    assert readme.check(mini_repo) == 0


# --- the CI documentation -------------------------------------------------------------

WORKFLOW = """---
name: Demo
on: [push]

permissions: {}

jobs:
  build:
    name: build it
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: echo build
  gate:
    name: gate
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: echo gate
"""

CI_DOC = """# CI

The introduction names every workflow, and this one is `demo.yml`.

## `.github/workflows/demo.yml` — Demo

| Job | Check name | Failing means |
| --- | --- | --- |
| `build` | `build it` | It did not build. |
| `gate` | `gate` | Something above failed. |
"""


def write_ci(root, workflow=WORKFLOW, doc=CI_DOC, name="demo.yml"):
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / name).write_text(workflow, encoding="utf-8")
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "ci.md").write_text(doc, encoding="utf-8")
    return root


def test_a_documented_workflow_passes(tmp_path, capsys):
    write_ci(tmp_path)
    assert ci_docs.check(tmp_path) == 0
    assert "2 job(s) across 1 workflow(s)" in capsys.readouterr().out


def test_the_introduction_must_name_every_workflow(tmp_path, capsys):
    # The failure this exists for: the page opened with "Five workflows run it" while
    # seven existed, because the count was prose and nothing owned it. Naming each file
    # in the introduction and comparing the set to the tree leaves no number to drift.
    write_ci(tmp_path, doc=CI_DOC.replace("and this one is `demo.yml`", "and nothing else"))
    assert ci_docs.check(tmp_path) == 1
    assert "introduction does not name demo.yml" in capsys.readouterr().out


def test_the_introduction_may_not_name_a_workflow_that_is_gone(tmp_path, capsys):
    # The reverse direction: a workflow is removed and the introduction keeps naming it,
    # sending a reader after a file that is not there.
    write_ci(tmp_path, doc=CI_DOC.replace("this one is `demo.yml`", "this one is `ghost.yml`"))
    assert ci_docs.check(tmp_path) == 1
    assert "introduction names ghost.yml" in capsys.readouterr().out


def test_a_job_with_no_row_fails(tmp_path, capsys):
    # The failure this exists for: a job is added, the table is not, and the first
    # person to meet the red check has to reverse-engineer it out of YAML.
    write_ci(tmp_path, doc=CI_DOC.replace("| `gate` | `gate` | Something above failed. |\n", ""))
    assert ci_docs.check(tmp_path) == 1
    assert "job `gate` has no row" in capsys.readouterr().out


def test_a_row_for_a_job_that_is_gone_fails(tmp_path, capsys):
    # The other direction, and the one a reader pays for: they go looking for a check
    # that no longer runs.
    write_ci(tmp_path, doc=CI_DOC + "| `retired` | `retired` | Nothing; it is gone. |\n")
    assert ci_docs.check(tmp_path) == 1
    assert "has a row for `retired`" in capsys.readouterr().out


def test_an_undocumented_workflow_fails(tmp_path, capsys):
    write_ci(tmp_path)
    (tmp_path / ".github" / "workflows" / "extra.yml").write_text(WORKFLOW, encoding="utf-8")
    assert ci_docs.check(tmp_path) == 1
    assert "extra.yml has no section" in capsys.readouterr().out


def test_a_section_for_a_workflow_that_is_gone_fails(tmp_path, capsys):
    write_ci(tmp_path, doc=CI_DOC + "\n## `.github/workflows/ghost.yml` — Ghost\n")
    assert ci_docs.check(tmp_path) == 1
    assert "section for ghost.yml, which does not exist" in capsys.readouterr().out


def test_a_workflow_with_no_jobs_is_reported_not_skipped(tmp_path, capsys):
    # A parse that silently matches nothing would pass this file vacuously, which is
    # the shape of failure every check here is written against.
    write_ci(tmp_path, workflow="---\nname: Demo\non: [push]\npermissions: {}\n")
    assert ci_docs.check(tmp_path) == 1
    assert "found no job in this workflow" in capsys.readouterr().out


def test_a_later_table_in_the_same_section_is_not_read_as_job_rows(tmp_path, capsys):
    # `evals.yml` documents its dispatch inputs and its credentials in tables of the
    # same shape further down its section. Reading those as job rows would fail a
    # document that is correct, which is the gate people learn to override.
    doc = (
        CI_DOC
        + """
### Dispatch inputs

| Input | Default | What it does |
| --- | --- | --- |
| `skill` | `all` | Which skill to score. |
"""
    )
    write_ci(tmp_path, doc=doc)
    assert ci_docs.check(tmp_path) == 0


def test_prose_after_the_job_name_is_not_read_as_a_different_job(tmp_path, capsys):
    # `catalogue` has a second row labelled "(portable step)" documenting a step rather
    # than a job. Only the first backticked token is the job.
    doc = CI_DOC + "| `build` (portable step) | `build it` | The extra step failed. |\n"
    write_ci(tmp_path, doc=doc)
    assert ci_docs.check(tmp_path) == 0


def test_a_tree_with_no_ci_doc_is_reported(tmp_path, capsys):
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "demo.yml").write_text(WORKFLOW, encoding="utf-8")
    assert ci_docs.check(tmp_path) == 1


def test_a_tree_with_no_workflows_is_reported(tmp_path, capsys):
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    (docs / "ci.md").write_text(CI_DOC, encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    assert ci_docs.check(tmp_path) == 1


def test_a_key_below_the_jobs_block_does_not_end_it(tmp_path):
    # The walk ends the jobs block at the next top-level key, and a comment column at
    # column zero is not one. `jobs:` is last in every workflow here, but that is a
    # habit rather than a rule.
    workflow = WORKFLOW + "\n# a trailing comment at column zero\n"
    write_ci(tmp_path, workflow=workflow)
    assert ci_docs.check(tmp_path) == 0


def test_main_runs_the_check_over_a_root(tmp_path, capsys):
    write_ci(tmp_path)
    assert ci_docs.main([str(tmp_path)]) == 0


def test_this_repository_documents_every_job_it_runs(capsys):
    # The check pointed at something real, which is the test the validator's own suite
    # makes of every other gate here.
    assert ci_docs.check(REPO) == 0


def test_a_top_level_key_after_the_jobs_block_ends_the_walk(tmp_path, capsys):
    # Without the break, a two-space key belonging to a later top-level block reads as
    # a job, and the gate then demands a row for something that is not one.
    workflow = WORKFLOW + "\nconcurrency:\n  group:\n    name: demo\n"
    write_ci(tmp_path, workflow=workflow)
    assert ci_docs.check(tmp_path) == 0


def test_a_job_key_with_a_trailing_comment_is_still_a_job(tmp_path, capsys):
    # A walk that skipped it would leave that job undocumented and unchecked for a
    # timeout while still reporting a clean run, which is the vacuous pass every
    # check here is written against. The same allowance is in the shell walk that
    # `permissions-audit` runs.
    workflow = WORKFLOW.replace("  gate:\n", "  gate:  # the aggregate\n")
    write_ci(tmp_path, workflow=workflow)
    assert ci_docs.check(tmp_path) == 0
    assert "2 job(s)" in capsys.readouterr().out


def test_a_scanner_that_matches_no_fence_refuses_to_pass(tmp_path, capsys, monkeypatch):
    # The other way this file can report success without having looked. Its whole
    # reason for existing is that a command with an unbalanced quote reads fine and
    # fails in someone else's terminal; if the fence pattern stops matching, every
    # block goes unexamined and the only trace is a zero in a line nobody reads.
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    (docs / "page.md").write_text("# Page\n\n```bash\necho hello\n```\n", encoding="utf-8")
    assert shell.check(tmp_path) == 0
    monkeypatch.setattr(shell, "FENCE_OPEN_RE", re.compile(r"^NEVERMATCHES$"))
    assert shell.check(tmp_path) == 2
    assert "matched none of them" in capsys.readouterr().err


def test_a_tree_with_no_shell_at_all_still_passes(tmp_path):
    # The guard cross-checks against a second scan rather than asserting a count, so a
    # tree that legitimately contains no shell is not a failure.
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    (docs / "page.md").write_text("# Page\n\nProse only.\n", encoding="utf-8")
    assert shell.check(tmp_path) == 0


# --- what the budget costs, in skills --------------------------------------------


def test_a_plugin_inside_the_budget_mutes_nothing():
    entries = [("p", "a", 100), ("p", "b", 200)]
    assert budget.mute(entries, "p", budget=8000) == 0


def test_a_plugin_over_the_budget_mutes_the_overflow():
    # Six descriptions of 2,000 against a 8,000 budget: four fit, two go silent.
    entries = [("p", f"s{i}", 2000) for i in range(6)]
    assert budget.mute(entries, "p", budget=8000) == 2


def test_the_count_is_the_smallest_honest_one():
    # Packing shortest-first keeps the most, so the number reported is a lower bound
    # rather than the expected loss. Longest-first on the same data drops more, which
    # is why the docstring says "at least".
    entries = [("p", "a", 600), ("p", "b", 500), ("p", "c", 500)]
    assert budget.mute(entries, "p", budget=1000) == 1  # 500 + 500 fit, 600 does not
    used = kept = 0
    for n in sorted((n for _, _, n in entries), reverse=True):
        if used + n > 1000:
            break
        used += n
        kept += 1
    assert len(entries) - kept == 2  # longest-first drops two: strictly worse


def test_only_the_named_plugin_is_counted():
    entries = [("p", "a", 9000), ("q", "b", 100)]
    assert budget.mute(entries, "q", budget=8000) == 0


def test_this_repository_has_plugins_that_go_silent(capsys):
    # The measurement that prompted this: four plugins exceed the whole listing budget
    # on their own, so a reader installing one of them loses skills to silence.
    entries = budget.walk(REPO)
    silent = {p: budget.mute(entries, p) for p in {e[0] for e in entries}}
    assert sum(silent.values()) > 0, "expected at least one plugin over the budget"
    assert silent["coding"] >= 1


# --- the install advice against the listing it describes ---------------------------


CLAIM_SENTENCE = "Only `engineering` fits the default budget on its own.\n\n"


def readme_with(root, fraction: str):
    """Write the fraction verbatim.

    A float here formats as `1e-07` for small values, which the regex reads as `1` — so
    the string is the literal the README would contain. It also carries the
    fit-the-default-budget claim, true of the fixture's single small plugin, so that
    these tests exercise only the fraction check they are written for and not the claim
    check `check_listing_budget.py` now also runs against README.md.
    """
    (root / "README.md").write_text(
        f"# Mini\n\n{CLAIM_SENTENCE}"
        f'Raise it:\n\n```json\n{{ "skillListingBudgetFraction": {fraction} }}\n```\n',
        encoding="utf-8",
    )


def test_a_fraction_that_covers_the_listing_passes(mini_repo, capsys):
    budget.check(mini_repo, update=True)
    readme_with(mini_repo, "0.5")  # far more than a two-skill repo needs
    assert budget.check(mini_repo) == 0


def test_a_fraction_that_does_not_cover_the_listing_fails(mini_repo, capsys):
    # The defect this exists for: 0.04 was recommended while the listing needed 0.075,
    # so a reader who followed the advice still lost nearly half their descriptions and
    # had no way to know.
    budget.check(mini_repo, update=True)
    readme_with(mini_repo, "0.0000001")
    assert budget.check(mini_repo) == 1
    out = capsys.readouterr().out
    assert "skillListingBudgetFraction" in out
    assert "it needs at least" in out


def test_a_readme_that_stops_naming_the_fraction_fails(mini_repo, capsys):
    # Removing the setting would otherwise retire the check silently, which is the
    # failure every gate here is written against.
    budget.check(mini_repo, update=True)
    (mini_repo / "README.md").write_text("# Mini\n\nNo advice here.\n", encoding="utf-8")
    assert budget.check(mini_repo) == 1
    assert "no longer names skillListingBudgetFraction" in capsys.readouterr().out


def test_a_tree_with_no_readme_skips_the_advice_check(mini_repo, capsys):
    budget.check(mini_repo, update=True)
    (mini_repo / "README.md").unlink(missing_ok=True)
    assert budget.check(mini_repo) == 0
    out = capsys.readouterr().out
    assert "README.md: not present, fraction advice not checked" in out
    assert "README.md: not present, fit-the-default-budget claim not checked" in out


# The README was checked and `docs/using.md` was not, so when #34 corrected 0.04 in the
# README it stayed wrong in the page the README links to for detail. Checking one file
# and not its companion is how a corrected figure survives in the place a reader reaches
# second.


def using_md_with(root, fraction: str) -> None:
    doc = root / "docs"
    doc.mkdir(exist_ok=True)
    (doc / "using.md").write_text(
        f"# Using\n\n{CLAIM_SENTENCE}"
        f'Raise it:\n\n```json\n{{ "skillListingBudgetFraction": {fraction} }}\n```\n',
        encoding="utf-8",
    )


def test_a_stale_fraction_in_using_md_fails(mini_repo, capsys):
    budget.check(mini_repo, update=True)
    readme_with(mini_repo, "0.5")  # the README is fine; only the companion is stale
    using_md_with(mini_repo, "0.0000001")
    assert budget.check(mini_repo) == 1
    out = capsys.readouterr().out
    assert "docs/using.md" in out
    assert "it needs at least" in out
    assert "file=README.md" not in out  # the README was fine; only the companion failed


def test_using_md_that_stops_naming_the_fraction_fails(mini_repo, capsys):
    budget.check(mini_repo, update=True)
    readme_with(mini_repo, "0.5")
    using_md_with(mini_repo, "0.5")
    (mini_repo / "docs" / "using.md").write_text("# Using\n\nNo advice.\n", encoding="utf-8")
    assert budget.check(mini_repo) == 1
    assert "no longer names skillListingBudgetFraction" in capsys.readouterr().out


def test_a_tree_with_no_using_md_skips_that_file(mini_repo, capsys):
    # Every other repository using this script has a README and no docs/using.md; a
    # missing companion is not a defect, but the absence is a printed notice rather
    # than silence — a bare `continue` reads, from the output, exactly like a file
    # that was checked and found correct.
    budget.check(mini_repo, update=True)
    readme_with(mini_repo, "0.5")
    assert not (mini_repo / "docs" / "using.md").exists()
    assert budget.check(mini_repo) == 0
    out = capsys.readouterr().out
    assert "docs/using.md: not present, fraction advice not checked" in out
    assert "docs/using.md: not present, fit-the-default-budget claim not checked" in out


# --- the "which plugins fit" claim against the listing it describes -----------------

# README.md, docs/using.md and docs/writing-skills.md all say, in prose, which plugins
# fit the runtime's default budget installed alone. Nothing checked that claim against
# the measurement before this, when `delivery` measured 8,025 characters and `gamedev`
# 8,048 — a few dozen over the ~8,000 default — so a small rewording could have made the
# claim wrong in three places at once.


def test_a_claim_matching_the_measured_fit_passes(mini_repo):
    budget.check(mini_repo, update=True)
    readme_with(mini_repo, "0.5")  # readme_with's CLAIM_SENTENCE names `engineering`,
    assert budget.check(mini_repo) == 0  # which does fit this fixture's small listing


def test_a_claim_naming_a_plugin_that_is_over_the_default_fails(mini_repo, capsys):
    # The claim says `engineering` fits. Forcing the runtime default below what it
    # measures makes that false, and only the file making the wrong claim should fail.
    budget.check(mini_repo, update=True)
    readme_with(mini_repo, "0.5")
    monkey = budget.RUNTIME_DEFAULT
    budget.RUNTIME_DEFAULT = 1
    try:
        assert budget.check(mini_repo) == 1
    finally:
        budget.RUNTIME_DEFAULT = monkey
    out = capsys.readouterr().out
    assert "file=README.md" in out
    assert "says only engineering fit the default budget; measured, none do" in out


def test_a_claim_omitting_a_plugin_that_fits_fails(mini_repo, capsys):
    # The other direction: a claim that names no plugin at all while one measures under
    # the default is just as wrong as naming one that does not.
    budget.check(mini_repo, update=True)
    (mini_repo / "README.md").write_text(
        "# Mini\n\nNo plugin here fit the default budget on its own.\n\n"
        'Raise it:\n\n```json\n{ "skillListingBudgetFraction": 0.5 }\n```\n',
        encoding="utf-8",
    )
    assert budget.check(mini_repo) == 1
    out = capsys.readouterr().out
    assert "file=README.md" in out
    assert "says only none fit the default budget; measured, engineering do" in out


def test_a_readme_that_drops_the_fit_claim_sentence_fails(mini_repo, capsys):
    # Rewording the claim out of existence must not retire the check silently, the same
    # reasoning as a fraction file with no fraction left in it.
    budget.check(mini_repo, update=True)
    (mini_repo / "README.md").write_text(
        '# Mini\n\nRaise it:\n\n```json\n{ "skillListingBudgetFraction": 0.5 }\n```\n',
        encoding="utf-8",
    )
    assert budget.check(mini_repo) == 1
    out = capsys.readouterr().out
    assert "file=README.md" in out
    assert "no longer names which plugins fit the default budget" in out


def test_a_missing_claim_file_is_a_notice_not_a_failure(mini_repo, capsys):
    # docs/writing-skills.md is a claim file with no equivalent helper in this suite —
    # mini_repo never creates it — so it is the case that exercises the plain "absent"
    # path end to end rather than through a helper that happens to write it.
    budget.check(mini_repo, update=True)
    readme_with(mini_repo, "0.5")
    assert not (mini_repo / "docs" / "writing-skills.md").exists()
    assert budget.check(mini_repo) == 0
    out = capsys.readouterr().out
    assert "docs/writing-skills.md: not present, fit-the-default-budget claim not checked" in out


# --- the fraction advice regex, anchored to a whole-line JSON object ----------------

# `"skillListingBudgetFraction": <n>` unanchored would match a value quoted in prose as
# a counter-example, the same failure mode `check_readme.py`'s digit-count check guards
# against elsewhere in this file. Anchoring to `^\s*\{ ... \}\s*$` on its own line, and
# checking every match rather than only the first, is what these two exist for.


def test_an_inline_prose_mention_is_not_read_as_a_recommendation(mini_repo, capsys):
    budget.check(mini_repo, update=True)
    (mini_repo / "README.md").write_text(
        f"# Mini\n\n{CLAIM_SENTENCE}"
        'Do not just set `"skillListingBudgetFraction": 0.0000001` inline; use the block below.\n\n'
        '```json\n{ "skillListingBudgetFraction": 0.5 }\n```\n',
        encoding="utf-8",
    )
    assert budget.check(mini_repo) == 0


def test_a_second_insufficient_value_in_a_later_block_fails(mini_repo, capsys):
    budget.check(mini_repo, update=True)
    (mini_repo / "README.md").write_text(
        f"# Mini\n\n{CLAIM_SENTENCE}"
        'First:\n\n```json\n{ "skillListingBudgetFraction": 0.5 }\n```\n\n'
        'Or, less headroom:\n\n```json\n{ "skillListingBudgetFraction": 0.0000001 }\n```\n',
        encoding="utf-8",
    )
    assert budget.check(mini_repo) == 1
    out = capsys.readouterr().out
    assert "0.0000001" in out
    assert "it needs at least" in out


def test_claimed_fits_reads_singular_and_ignores_fit_inside_a_word():
    # The singular is the grammatical form the day only one plugin fits, and "benefit"
    # before the names used to cut the sentence short at the substring.
    assert budget.claimed_fits("Only `career` fits the default budget on its own.") == {"career"}
    assert budget.claimed_fits(
        "For the benefit of readers: only `career` and `personal` fit the default budget."
    ) == {"career", "personal"}


def test_portable_links_keep_source_identity_in_individual_and_bundle(mini_repo, tmp_path):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    refs = skill / "references"
    (refs / "deep").mkdir(parents=True)
    (refs / "a.md").write_text(
        "# Shared title\n\n## Contents\n\nA contents.\n\n"
        "[self](#contents) [sibling](./b.md#contents) "
        "[nested](deep/n.md#nested)\n\n"
        "## Topic\n\nFirst topic.\n\n## Topic-1\n\nNatural suffix.\n\n"
        "## Topic\n\nDuplicate topic.\n",
        encoding="utf-8",
    )
    (refs / "b.md").write_text(
        "# Shared title\n\n## Contents\n\nB contents.\n\n[title](a.md#shared-title) [root](a.md)\n",
        encoding="utf-8",
    )
    (refs / "deep/n.md").write_text(
        "# Nested title\n\n## Nested\n\nNested content.\n\n[up](../a.md#topic-2)\n",
        encoding="utf-8",
    )
    (refs / "odd(name).md").write_text("# Odd\n\n## Details\n\nParenthesis target.\n")
    source = skill / "SKILL.md"
    source.write_text(
        source.read_text() + "\n"
        '[body [nested] label](<references/a.md#contents> "keep title")\n'
        "[escaped \\] label](references/a.md#topic-1)\n"
        "[encoded](references/deep/n.md#%6Eested)\n"
        "[balanced](references/odd(name).md#details)\n"
        "[escaped destination](references/odd\\(name\\).md#details)\n"
        "Read `references/a.md#topic-2`.\n"
        "[references/a.md][target]\n"
        '[definition][target]\n[target]: references/b.md#contents "definition title"\n'
        '[external references/a.md](https://example.com/references/a.md "external")\n'
        "`[example](references/missing.md)`\n"
        "````markdown\n[example](references/missing.md)\n```\n"
        "# fenced heading\n````\n",
        encoding="utf-8",
    )
    # A second skill has identical heading names and filenames, so a bundle must keep
    # both source identities despite their final heading levels and concatenation.
    second = skill.parent / "beta"
    second.mkdir(exist_ok=True)
    (second / "SKILL.md").write_text(
        source.read_text().replace("name: alpha", "name: beta"), encoding="utf-8"
    )
    shutil.copytree(refs, second / "references")
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    individual = (out / "skills/alpha.md").read_text()
    bundle = (out / "plugins/engineering.md").read_text()
    expected = {
        "body [nested] label": "A contents.",
        "self": "A contents.",
        "sibling": "B contents.",
        "nested": "Nested content.",
        "escaped \\] label": "Natural suffix.",
        "encoded": "Nested content.",
        "up": "Duplicate topic.",
        "balanced": "Parenthesis target.",
        "escaped destination": "Parenthesis target.",
        "title": "A contents.",
        "root": "A contents.",
    }
    for document in (individual, bundle):
        anchors = re.findall(r'<a name="([^"]+)"></a>', document)
        assert len(anchors) == len(set(anchors))
        for label, content in expected.items():
            # Examine the actual output destination and its source content independently
            # of the implementation's source alias map.
            destination = re.search(re.escape("[" + label + "]") + r"\(<?#([^>\s)]+)", document)
            assert destination, label
            anchor = destination.group(1)
            assert anchor in anchors
            target = document.split(f'<a name="{anchor}"></a>', 1)[1]
            assert content in target.split('<a name="', 1)[0] or (
                label in {"title", "root"}
                and "Shared title" in target[:200]
                and content in target[:500]
            ), (label, target[:200])
        assert '"keep title"' in document
        assert re.search(r"\[references/a\.md\]\[portable-reference-[a-f0-9]+\]", document)
        assert 'Read the "Shared title" section below.' in document
        assert "section below#topic" not in document
        assert (
            '[external references/a.md](https://example.com/references/a.md "external")' in document
        )
        assert "`[example](references/missing.md)`" in document
        assert (
            "````markdown\n[example](references/missing.md)\n```\n# fenced heading\n````"
            in document
        )
        definition = re.search(
            r'^\[portable-reference-[a-f0-9]+\]: #([^ ]+) "definition title"$', document, re.M
        )
        assert definition and definition.group(1) in anchors
        assert (
            "B contents."
            in document.split(f'<a name="{definition.group(1)}"></a>', 1)[1].split('<a name="', 1)[
                0
            ]
        )
    assert set(re.findall(r'<a name="([^"]+)"></a>', individual)).issubset(
        re.findall(r'<a name="([^"]+)"></a>', bundle)
    )


@pytest.mark.parametrize("destination", ["missing.md", "a.md#missing", "../../outside.md"])
@pytest.mark.parametrize("current", ["SKILL.md", "references/a.md"])
def test_portable_missing_explicit_reference_links_fail_before_writes(
    mini_repo, tmp_path, capsys, destination, current
):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    refs = skill / "references"
    refs.mkdir()
    (refs / "a.md").write_text("# A\n\n## Existing\n\nContent.\n")
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    before = {path.relative_to(out): path.read_bytes() for path in out.rglob("*") if path.is_file()}
    if current == "SKILL.md" and destination == "a.md#missing":
        destination = "references/a.md#missing"
    source = skill / current
    source.write_text(source.read_text() + f"\n[broken]({destination})\n")
    for check in (False, True):
        assert portable.export(mini_repo, out, check=check) == 1
        assert f"{current}: {destination}" in capsys.readouterr().out
        assert before == {
            path.relative_to(out): path.read_bytes() for path in out.rglob("*") if path.is_file()
        }


def test_portable_symlink_escape_is_rejected_and_assets_get_safe_fences(mini_repo, tmp_path):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    assets = skill / "assets"
    assets.mkdir()
    (assets / "example.md").write_text("# Example\n```python\nprint(1)\n```\n")
    _, _, document, unresolved = portable.render_skill(skill)
    assert not unresolved
    assert "````markdown\n# Example\n```python\nprint(1)\n```\n````" in document
    outside = tmp_path / "outside.md"
    outside.write_text("Private outside content")
    (assets / "escape.md").symlink_to(outside)
    _, _, document, unresolved = portable.render_skill(skill)
    assert unresolved == ["assets/escape.md: symlink escapes skill root"]
    assert "Private outside content" not in document


def test_portable_reference_bindings_stay_local_to_every_source(mini_repo, tmp_path):
    expected = {}
    for skill_name in ("alpha", "beta"):
        skill = mini_repo / "plugins/engineering/skills" / skill_name
        refs = skill / "references"
        refs.mkdir()
        # This shortcut has a definition elsewhere, but no definition in SKILL.md.
        source = skill / "SKILL.md"
        source.write_text(source.read_text() + "\n[shared label]\n")
        for reference_name in ("one", "two"):
            sentinel = f"{skill_name}-{reference_name} ONLY sentinel"
            key = f"{skill_name}-{reference_name}"
            uri = f"https://example.com/{key}/references/example.md"
            expected[key] = (sentinel, uri)
            (refs / f"{reference_name}.md").write_text(
                f"# Same title\n\n## Target\n\n{sentinel}\n\n"
                f"[{key} full][ ShArEd\tLaBeL ]\n"
                "[shared label][]\n[SHARED  LABEL]\n"
                f"[{key} external][external]\n"
                f'[SHARED LABEL]: #target "{key} local title"\n'
                '[shared label]: https://wrong.example "duplicate loses"\n'
                f'[EXTERNAL]: {uri} "{key} external title"\n'
                "`[shared label] [code][external]`\n"
                "\\[shared label]\n[undefined]\n"
                "~~~markdown\n[shared label]\n[external]: https://fenced.example\n~~~\n",
                encoding="utf-8",
            )
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    for filename, owners in (
        ("skills/alpha.md", ("alpha",)),
        ("skills/beta.md", ("beta",)),
        ("plugins/engineering.md", ("alpha", "beta")),
    ):
        document = (out / filename).read_text()
        # Build the artifact's actual first-definition map independently of all
        # exporter helpers. This models the binding that a Markdown renderer uses.
        effective = {}
        definitions = []
        uses = []
        fenced = False
        for line in document.splitlines():
            if line.startswith("~~~"):
                fenced = not fenced
                continue
            if fenced or line.startswith("`") or line.startswith("\\"):
                continue
            definition = re.fullmatch(r'\[([^]]+)\]: (\S+) "([^"]+)"', line)
            if definition:
                identifier, destination, title = definition.groups()
                normalized = " ".join(identifier.split()).casefold()
                definitions.append((normalized, destination, title))
                effective.setdefault(normalized, (destination, title))
                continue
            uses.extend(re.findall(r"\[([^]]+)\]\[([^]]+)\]", line))
        assert len(definitions) == 6 * len(owners)
        assert len(effective) == 4 * len(owners)
        assert len(uses) == 8 * len(owners)
        seen_local = dict.fromkeys(
            (owner + "-" + ref for owner in owners for ref in ("one", "two")), 0
        )
        seen_external = dict.fromkeys(seen_local, 0)
        identifier_sources = {}
        for identifier, destination, title in definitions:
            assert identifier.startswith("portable-reference-")
            assert len(identifier) <= 999
            if title == "duplicate loses":
                assert destination == "https://wrong.example"
                assert effective[identifier][1] != title
                continue
            source_key, kind, _ = title.rsplit(" ", 2)
            assert source_key in expected and source_key.split("-")[0] in owners
            previous_owner = identifier_sources.setdefault(identifier, source_key)
            assert previous_owner == source_key
            sentinel, uri = expected[source_key]
            if kind == "local":
                assert destination.startswith("#")
                target = document.split(f'<a name="{destination[1:]}"></a>', 1)[1]
                assert sentinel in target.split('<a name="', 1)[0]
            else:
                assert kind == "external" and destination == uri
        for display, identifier in uses:
            destination, title = effective[" ".join(identifier.split()).casefold()]
            source_key, kind, _ = title.rsplit(" ", 2)
            sentinel, uri = expected[source_key]
            if kind == "local":
                assert display in {source_key + " full", "shared label", "SHARED  LABEL"}
                target = document.split(f'<a name="{destination[1:]}"></a>', 1)[1]
                assert sentinel in target.split('<a name="', 1)[0]
                seen_local[source_key] += 1
            else:
                assert display == source_key + " external" and destination == uri
                seen_external[source_key] += 1
        assert all(count == 3 for count in seen_local.values())
        assert all(count == 1 for count in seen_external.values())
        # No definition may accidentally activate a shortcut from a different source.
        assert "\n[shared label]\n" in document
        assert "\n[undefined]\n" in document
        assert "`[shared label] [code][external]`" in document
        assert "\\[shared label]" in document
        assert "~~~markdown\n[shared label]\n[external]: https://fenced.example\n~~~" in document


@pytest.mark.parametrize(
    "binding", ["[shared\nlabel]", "[visible][shared\nlabel]", "[shared\nlabel]: #target"]
)
def test_portable_unsupported_multiline_reference_binding_fails(mini_repo, tmp_path, binding):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    source = skill / "SKILL.md"
    source.write_text(
        source.read_text() + "\n## Target\n\n[shared label]: #target\n" + binding + "\n"
    )
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out, check=True) == 1
    assert portable.export(mini_repo, out) == 1
    assert not out.exists()


def test_portable_nested_image_references_keep_source_bindings(mini_repo, tmp_path):
    expected = {}
    protected = (
        "`[![badge][image]][target]`\n"
        '[code `![badge][image]`](https://example.com/code "![badge][image]")\n'
        "~~~markdown\n[![badge][image]][target]\n~~~\n"
    )
    for owner in ("alpha", "beta"):
        skill = mini_repo / "plugins/engineering/skills" / owner
        refs = skill / "references"
        refs.mkdir()
        for source in (skill / "SKILL.md", refs / "one.md", refs / "two.md"):
            key = owner + "-" + source.stem
            image = f"https://example.com/{key}.svg"
            target = f"https://example.com/{key}/details"
            expected[key] = (image, target)
            original = source.read_text() if source.exists() else "# Reference\n"
            source.write_text(
                original + f"\n{key}\n"
                "[![badge][image]][target]\n"
                "[![image][]][target]\n"
                "[![image]][target]\n"
                f'[![badge][image]]({target} "outer [image]")\n'
                f"[![image][]]({target})\n"
                f"[![image]]({target})\n\n"
                f'[image]: {image} "image title"\n'
                f'[target]: {target} "target title"\n\n' + protected
            )
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out, check=True) == 0
    assert portable.export(mini_repo, out) == 0
    for filename, owners in (
        ("skills/alpha.md", ("alpha",)),
        ("skills/beta.md", ("beta",)),
        ("plugins/engineering.md", ("alpha", "beta")),
    ):
        document = (out / filename).read_text()
        definitions = dict(
            re.findall(r'^\[([^]]+)\]: (\S+) "(?:image|target) title"$', document, re.M)
        )
        for key, (image, target) in expected.items():
            if key.split("-")[0] not in owners:
                continue
            section = document.split("\n" + key + "\n", 1)[1].split(protected, 1)[0]
            uses = re.findall(r"^\[!\[(badge|image)\]\[([^]]+)\]\](.*)$", section, re.M)
            assert len(uses) == 6
            for label, image_id, outer in uses:
                assert label in {"badge", "image"}
                assert definitions[image_id] == image
                if outer.startswith("["):
                    assert definitions[outer[1:-1]] == target
                else:
                    assert outer in {f'({target} "outer [image]")', f"({target})"}
        assert document.count(protected) == 3 * len(owners)


@pytest.mark.parametrize("context", ["body", "reference"])
@pytest.mark.parametrize("outer", ["inline", "reference", "standalone"])
@pytest.mark.parametrize("binding", ["inline", "full", "collapsed", "shortcut"])
@pytest.mark.parametrize(
    "destination", ["existing.svg", "missing.svg", "../../escape.svg", "#alpha"]
)
def test_portable_local_image_sources_fail_before_writes(
    mini_repo, tmp_path, capsys, context, outer, binding, destination
):
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    before = {p.relative_to(out): p.read_bytes() for p in out.rglob("*") if p.is_file()}
    skill = mini_repo / "plugins/engineering/skills/alpha"
    refs = skill / "references"
    refs.mkdir()
    source = skill / "SKILL.md" if context == "body" else refs / "one.md"
    (source.parent / "existing.svg").write_text("<svg></svg>\n")
    image = {
        "inline": f'![image](<{destination}> "image title")',
        "full": "![badge][image]",
        "collapsed": "![image][]",
        "shortcut": "![image]",
    }[binding]
    use = {
        "inline": f'[{image}](https://example.com "outer title")',
        "reference": f"[{image}][target]",
        "standalone": image,
    }[outer]
    original = source.read_text() if source.exists() else "# Reference\n"
    source.write_text(
        original
        + "\n"
        + use
        + "\n\n"
        + (f'[image]: <{destination}> "image title"\n' if binding != "inline" else "")
        + '[target]: https://example.com "target title"\n'
    )
    for check in (True, False):
        assert portable.export(mini_repo, out, check=check) == 1
        assert before == {p.relative_to(out): p.read_bytes() for p in out.rglob("*") if p.is_file()}
        assert "unsupported local image source: " + destination in capsys.readouterr().out


def test_portable_nested_inline_external_images_preserve_syntax(mini_repo, tmp_path):
    protected = (
        "`[![image](missing.svg)](https://example.com)`\n"
        '[code `![image](missing.svg)`](https://example.com "![image](missing.svg)")\n'
        "~~~markdown\n[![image](missing.svg)][target]\n~~~\n"
    )
    syntax = (
        '[![badge](<https://example.com/badge.svg> "image title")]'
        '(https://example.com "outer title")\n'
        '[![badge](//example.com/badge.svg "image title")][target]\n'
    )
    for owner in ("alpha", "beta"):
        skill = mini_repo / "plugins/engineering/skills" / owner
        refs = skill / "references"
        refs.mkdir()
        for source in (skill / "SKILL.md", refs / "one.md"):
            original = source.read_text() if source.exists() else "# Reference\n"
            source.write_text(
                original + "\n" + syntax + protected + "\n[target]: https://example.com\n"
            )
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out, check=True) == 0
    assert portable.export(mini_repo, out) == 0
    for filename, count in (
        ("skills/alpha.md", 2),
        ("skills/beta.md", 2),
        ("plugins/engineering.md", 4),
    ):
        document = (out / filename).read_text()
        assert document.count(syntax.splitlines()[0]) == count
        assert document.count('![badge](//example.com/badge.svg "image title")') == count
        assert document.count(protected) == count


def test_portable_escaped_image_marker_is_a_link(mini_repo, tmp_path):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    refs = skill / "references"
    refs.mkdir()
    (refs / "one.md").write_text("# Reference\nContent.\n")
    source = skill / "SKILL.md"
    source.write_text(source.read_text() + r"\![label](references/one.md)" + "\n")
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out, check=True) == 0
    assert portable.export(mini_repo, out) == 0
    for filename in ("skills/alpha.md", "plugins/engineering.md"):
        assert re.search(r"\\!\[label\]\(#portable-[^)]+\)", (out / filename).read_text())


@pytest.mark.parametrize("heading", ["[Guide][target]", "[Guide][]", "[Guide]"])
def test_portable_bound_heading_duplicate_targets(mini_repo, tmp_path, heading):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    refs = skill / "references"
    refs.mkdir()
    content = (
        f"## {heading}\n\nFIRST sentinel\n\n## Guide\n\nSECOND sentinel\n\n"
        "[first](#guide) [second](#guide-1)\n\n"
        "[target]: https://example.com/target\n[Guide]: https://example.com/guide\n"
    )
    source = skill / "SKILL.md"
    source.write_text(source.read_text() + "\n" + content)
    (refs / "one.md").write_text("# Reference\n\n" + content)
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    for filename in ("skills/alpha.md", "plugins/engineering.md"):
        document = (out / filename).read_text()
        for label, sentinel in (("first", "FIRST"), ("second", "SECOND")):
            targets = re.findall(rf"\[{label}\]\(#([^)]+)\)", document)
            assert len(targets) == 2
            for target in targets:
                section = document.split(f'<a name="{target}"></a>', 1)[1]
                section = section.split('<a name="', 1)[0]
                assert f"{sentinel} sentinel" in section


@pytest.mark.parametrize(
    "heading",
    [
        "[Guide](https://example.com/path(a)b)",
        '[Guide](https://example.com "a (b) c")',
    ],
)
def test_portable_balanced_inline_heading_duplicate_targets(mini_repo, tmp_path, heading):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    refs = skill / "references"
    refs.mkdir()
    content = (
        f"## {heading}\n\nFIRST sentinel\n\n## Guide\n\nSECOND sentinel\n\n"
        "[first](#guide) [second](#guide-1)\n\n"
        "[target]: https://example.com/target\n[Guide]: https://example.com/guide\n"
    )
    source = skill / "SKILL.md"
    source.write_text(source.read_text() + "\n" + content)
    (refs / "one.md").write_text("# Reference\n\n" + content)
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    for filename in ("skills/alpha.md", "plugins/engineering.md"):
        document = (out / filename).read_text()
        for label, sentinel in (("first", "FIRST"), ("second", "SECOND")):
            targets = re.findall(rf"\[{label}\]\(#([^)]+)\)", document)
            assert len(targets) == 2
            for target in targets:
                section = document.split(f'<a name="{target}"></a>', 1)[1]
                section = section.split('<a name="', 1)[0]
                assert f"{sentinel} sentinel" in section


@pytest.mark.parametrize(
    ("heading", "fragment"),
    [
        # GitHub keeps the visible text of an autolink and of a code span, and drops only
        # raw HTML tags; the last three pin that those are still dropped.
        ("See <https://example.com>", "see-httpsexamplecom"),
        ("Mail <me@example.com>", "mail-meexamplecom"),
        ("Use `<tag>`", "use-tag"),
        ("Use ``<tag>`c``", "use-tagc"),
        ("<b>Bold</b> word", "bold-word"),
        ('<span class="x">Span</span> text<br/>', "span-text"),
        ("Note <!-- hidden --> here", "note--here"),
    ],
)
def test_portable_heading_aliases_keep_visible_text_and_drop_only_html_tags(
    mini_repo, tmp_path, heading, fragment
):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    refs = skill / "references"
    refs.mkdir()
    content = f"## {heading}\n\nSENTINEL body\n\n[go](#{fragment})\n"
    source = skill / "SKILL.md"
    source.write_text(source.read_text() + "\n" + content)
    (refs / "one.md").write_text("# Reference\n\n" + content)
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out, check=True) == 0
    assert portable.export(mini_repo, out) == 0
    for filename in ("skills/alpha.md", "plugins/engineering.md"):
        document = (out / filename).read_text()
        targets = re.findall(r"\[go\]\(#([^)]+)\)", document)
        assert len(targets) == 2
        for target in targets:
            section = document.split(f'<a name="{target}"></a>', 1)[1]
            assert "SENTINEL body" in section.split('<a name="', 1)[0]


@pytest.mark.parametrize("run", ["`", "``", "```"])
def test_portable_unmatched_code_runs_continue_scanning(mini_repo, tmp_path, run):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    source = skill / "SKILL.md"
    source.write_text(
        source.read_text()
        + f"\nLiteral {run} before [target] and [local](#alpha).\n"
        + "\n[target]: https://example.com/target\n"
        + "\nClosed `` [target] ` [local](missing.md) `` stays protected.\n"
    )
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    for filename in ("skills/alpha.md", "plugins/engineering.md"):
        document = (out / filename).read_text()
        assert re.search(r"Literal `+ before \[target\]\[portable-reference-", document)
        assert re.search(r"\[local\]\(#portable-", document)
        assert "Closed `` [target] ` [local](missing.md) `` stays protected." in document


@pytest.mark.parametrize(
    "span",
    [
        "`` `[x](references/one.md)` ``",
        "``` ``[x](references/one.md)`` ```",
    ],
)
def test_portable_nested_backtick_spans_stay_inert_beside_real_pointers(mini_repo, tmp_path, span):
    # An inner shorter run is content, not a closing delimiter: only a run of the same
    # length closes the span, so the example must survive byte for byte while a real
    # pointer on the same line, outside any code, is still rewritten.
    skill = mini_repo / "plugins/engineering/skills/alpha"
    refs = skill / "references"
    refs.mkdir()
    (refs / "one.md").write_text("# Reference\n\nContent.\n")
    source = skill / "SKILL.md"
    source.write_text(
        source.read_text()
        + f"\nShow {span} then read references/one.md.\n"
        + "\nA \\* star before references/one.md.\n"
    )
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out, check=True) == 0
    assert portable.export(mini_repo, out) == 0
    for filename in ("skills/alpha.md", "plugins/engineering.md"):
        document = (out / filename).read_text()
        assert f'Show {span} then read the "Reference" section below.' in document
        assert 'A \\* star before the "Reference" section below.' in document


@pytest.mark.parametrize(
    "title", ["[Guide][target]", "![Guide][target]", "[Guide](https://example.com/title)"]
)
def test_portable_relocated_titles_rewrite_bindings(mini_repo, tmp_path, title):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    source = skill / "SKILL.md"
    header = source.read_text().split("---", 2)[:2]
    source.write_text(
        "---".join(header) + "---\n# " + title + "\n\n[target]: https://example.com/skill\n"
    )
    refs = skill / "references"
    refs.mkdir()
    (refs / "one.md").write_text("# " + title + "\n\n[target]: https://example.com/reference\n")
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    for filename in ("skills/alpha.md", "plugins/engineering.md"):
        document = (out / filename).read_text()
        headings = [line for line in document.splitlines() if re.match(r"^#{1,6} ", line)]
        assert len([line for line in headings if "Guide" in line]) == 2
        assert not any("[Guide][target]" in line for line in headings)
        if "[target]" in title:
            assert len(re.findall(r"Guide\]\[portable-reference-", "\n".join(headings))) == 2


@pytest.mark.parametrize("location", ["skill", "reference"])
@pytest.mark.parametrize(
    "title",
    ["![badge](missing.svg)", "[![badge](missing.svg)](https://example.com)", "![badge][image]"],
)
def test_portable_title_images_reject_before_writes(mini_repo, tmp_path, location, title):
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    before = {p.relative_to(out): p.read_bytes() for p in out.rglob("*") if p.is_file()}
    skill = mini_repo / "plugins/engineering/skills/alpha"
    if location == "skill":
        source = skill / "SKILL.md"
        source.write_text(
            source.read_text().replace("# alpha", "# " + title) + "\n[image]: SKILL.md\n"
        )
    else:
        refs = skill / "references"
        refs.mkdir()
        (refs / "one.md").write_text("# " + title + "\n\n[image]: ../SKILL.md\n")
    for check in (True, False):
        assert portable.export(mini_repo, out, check=check) == 1
        assert before == {p.relative_to(out): p.read_bytes() for p in out.rglob("*") if p.is_file()}


@pytest.mark.parametrize("binding", ["full", "collapsed", "shortcut"])
def test_portable_copied_titles_keep_owner_bindings(mini_repo, tmp_path, binding):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    refs = skill / "references"
    refs.mkdir()
    title = {"full": "[Guide][target]", "collapsed": "[Guide][]", "shortcut": "[Guide]"}[binding]
    key = "target" if binding == "full" else "Guide"
    source = skill / "SKILL.md"
    source.write_text(
        source.read_text()
        + f'\n[{key}]: https://example.com/caller "Caller title"\n'
        + "\nRead one references/one.md.\nRead two references/two.md.\n"
        + "\nFragment one `references/one.md#guide`.\n"
        + "Fragment two `references/two.md#guide`.\n"
        + "\n`[Guide][target]` stays code.\n\n```markdown\nreferences/one.md\n```\n"
    )
    for owner in ("one", "two"):
        (refs / f"{owner}.md").write_text(
            f'# {title}\n\n{owner} body.\n\n[{key}]: https://example.com/{owner} "{owner} title"\n'
        )
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out, check=True) == 0
    assert portable.export(mini_repo, out) == 0
    for filename in ("skills/alpha.md", "plugins/engineering.md"):
        document = (out / filename).read_text()
        definitions = dict(re.findall(r"^\[([^]]+)\]: (.+)$", document, re.M))
        for owner in ("one", "two"):
            for prefix in ("Read", "Fragment"):
                line = next(
                    line for line in document.splitlines() if line.startswith(f"{prefix} {owner} ")
                )
                match = re.search(r"\[Guide\]\[([^]]+)\]", line)
                assert match
                assert definitions[match[1]] == f'https://example.com/{owner} "{owner} title"'
                assert "`" not in line
        assert "`[Guide][target]` stays code." in document
        assert "```markdown\nreferences/one.md\n```" in document


def test_portable_copied_titles_resolve_local_sections_and_external_images(mini_repo, tmp_path):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    refs = skill / "references"
    refs.mkdir()
    source = skill / "SKILL.md"
    source.write_text(source.read_text() + "\nRead references/one.md.\n")
    title = (
        '[Section](two.md#details) ![badge](https://example.com/badge.svg "Badge title") [unknown]'
    )
    (refs / "one.md").write_text("# " + title + "\n\nOne body.\n")
    (refs / "two.md").write_text("# Two\n\n## Details\n\nTARGET sentinel\n")
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    for filename in ("skills/alpha.md", "plugins/engineering.md"):
        document = (out / filename).read_text()
        pointer = next(line for line in document.splitlines() if line.startswith("Read "))
        target = re.search(r"\[Section\]\(#([^)]+)\)", pointer)[1]
        section = document.split(f'<a name="{target}"></a>', 1)[1].split('<a name="', 1)[0]
        assert "TARGET sentinel" in section
        assert '![badge](https://example.com/badge.svg "Badge title") [unknown]' in pointer


def test_portable_title_bare_pointers_do_not_expand_recursively(mini_repo, tmp_path):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    refs = skill / "references"
    refs.mkdir()
    source = skill / "SKILL.md"
    source.write_text(
        source.read_text().replace("# alpha", "# Alpha references/one.md")
        + "\nRead references/one.md and references/two.md.\n"
        + "Read assets/example.txt and scripts/example.py.\n"
    )
    (refs / "one.md").write_text("# One references/one.md references/two.md\n\nOne body.\n")
    (refs / "two.md").write_text("# Two references/one.md\n\nTwo body.\n")
    for directory, filename, text in (
        ("assets", "example.txt", "Example asset\n"),
        ("scripts", "example.py", "print('example')\n"),
    ):
        (skill / directory).mkdir()
        (skill / directory / filename).write_text(text)
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    for filename in ("skills/alpha.md", "plugins/engineering.md"):
        document = (out / filename).read_text()
        assert len(document) < 10000
        assert re.search(r"^#{1,6} Alpha references/one.md$", document, re.M)
        assert 'the "One references/one.md references/two.md" section below' in document
        assert 'the "Two references/one.md" section below' in document
        assert 'the "assets/example.txt" section below' in document
        assert 'the "scripts/example.py" section below' in document
        assert re.search(r"^#{1,6} One references/one.md references/two.md$", document, re.M)
        assert re.search(r"^#{1,6} Two references/one.md$", document, re.M)


def test_portable_copied_title_local_image_rejects_before_writes(mini_repo, tmp_path):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    refs = skill / "references"
    refs.mkdir()
    source = skill / "SKILL.md"
    source.write_text(source.read_text() + "\nRead references/one.md.\n")
    reference = refs / "one.md"
    reference.write_text("# Guide\n\nReference body.\n")
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    before = {p.relative_to(out): p.read_bytes() for p in out.rglob("*") if p.is_file()}
    reference.write_text("# ![badge][image]\n\n[image]: ../SKILL.md\n")
    for check in (True, False):
        assert portable.export(mini_repo, out, check=check) == 1
        assert before == {p.relative_to(out): p.read_bytes() for p in out.rglob("*") if p.is_file()}


# Footnote labels are document-global in GitHub-flavoured Markdown, unlike reference
# labels, which only matter inside one file. Flattening several files into one document
# therefore lets two `[^note]` definitions collide, so the export namespaces them per
# source file — on the definition and on every use that file makes of it.
FOOTNOTE_LABEL = r"\[\^(portable-footnote-[a-f0-9]+)\]"


def _footnote_definitions(document: str) -> dict[str, str]:
    return dict(re.findall(rf"^{FOOTNOTE_LABEL}: (.*)$", document, re.M))


def test_portable_footnotes_are_not_turned_into_reference_links(mini_repo, tmp_path):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    refs = skill / "references"
    refs.mkdir()
    source = skill / "SKILL.md"
    source.write_text(
        source.read_text() + "\nRead references/one.md.\n\nBody claim.[^note] Another.[^2]\n\n"
        "[^note]: Body details, see [one](references/one.md).\n[^2]: Second body.\n"
    )
    (refs / "one.md").write_text(
        "# One\n\nReference claim.[^note]\n\n[^note]: Reference details.\n"
    )
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out, check=True) == 0
    assert portable.export(mini_repo, out) == 0
    for filename in ("skills/alpha.md", "plugins/engineering.md"):
        document = (out / filename).read_text()
        # A footnote renamed into a reference label stops being a footnote.
        assert "portable-reference-" not in document
        definitions = _footnote_definitions(document)
        assert len(definitions) == 3
        body_label = re.search(rf"Body claim\.{FOOTNOTE_LABEL}", document)[1]
        reference_label = re.search(rf"Reference claim\.{FOOTNOTE_LABEL}", document)[1]
        second_label = re.search(rf"Another\.{FOOTNOTE_LABEL}", document)[1]
        assert len({body_label, reference_label, second_label}) == 3
        assert definitions[reference_label] == "Reference details."
        assert definitions[second_label] == "Second body."
        # The text of a footnote is prose like any other: its link still resolves.
        assert definitions[body_label].startswith("Body details, see [one](#portable-")
        assert "references/one.md" not in definitions[body_label]


def test_portable_reference_link_beside_a_footnote_on_one_line(mini_repo, tmp_path):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    source = skill / "SKILL.md"
    source.write_text(
        source.read_text() + "\n[text][ref] and a claim.[^1]\n\n"
        "[ref]: https://example.com/ref\n[^1]: Footnote text.\n"
    )
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    document = (out / "skills/alpha.md").read_text()
    line = next(line for line in document.splitlines() if line.startswith("[text]"))
    assert re.fullmatch(
        rf"\[text\]\[portable-reference-[a-f0-9]+\] and a claim\.{FOOTNOTE_LABEL}", line
    )
    assert re.search(r"^\[portable-reference-[a-f0-9]+\]: https://example.com/ref$", document, re.M)
    assert list(_footnote_definitions(document).values()) == ["Footnote text."]


def test_portable_footnote_syntax_in_code_is_left_exactly_as_written(mini_repo, tmp_path):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    source = skill / "SKILL.md"
    fenced = "```markdown\nExample.[^1]\n\n[^1]: Example footnote.\n```\n"
    inline = "Write `[^1]` after a claim, or ``[^1]: text`` to define it.\n"
    source.write_text(source.read_text() + f"\n{fenced}\n{inline}\nReal.[^1]\n\n[^1]: Real.\n")
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    for filename in ("skills/alpha.md", "plugins/engineering.md"):
        document = (out / filename).read_text()
        assert fenced in document
        assert inline in document
        assert list(_footnote_definitions(document).values()) == ["Real."]


def test_portable_footnote_use_without_a_definition_in_its_own_file_is_left_alone(
    mini_repo, tmp_path
):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    refs = skill / "references"
    refs.mkdir()
    source = skill / "SKILL.md"
    source.write_text(source.read_text() + "\nRead references/one.md.\n\nOrphan.[^note]\n")
    (refs / "one.md").write_text("# One\n\nDefined.[^note]\n\n[^note]: Only here.\n")
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    document = (out / "skills/alpha.md").read_text()
    assert "Orphan.[^note]" in document  # not borrowed by another file's definition
    assert re.search(rf"Defined\.{FOOTNOTE_LABEL}", document)
    assert "[^note]:" not in document


def test_portable_footnote_labels_stay_distinct_across_files_and_skills(mini_repo, tmp_path):
    # Footnote labels match case-insensitively, as cmark-gfm does; that follows its source
    # and spec, and was not checked against GitHub's live renderer. The body uses the
    # upper-case spelling of a lower-case definition and the reference the reverse, so
    # that dropping the casefold on either the use lookup or the definition key fails.
    for skill_name in ("alpha", "beta"):
        skill = mini_repo / "plugins/engineering/skills" / skill_name
        refs = skill / "references"
        refs.mkdir(exist_ok=True)
        source = skill / "SKILL.md"
        source.write_text(
            source.read_text() + f"\nRead references/one.md.\n\n{skill_name} body.[^NOTE]\n\n"
            f"[^note]: {skill_name} body note.\n"
        )
        (refs / "one.md").write_text(
            f"# One\n\n{skill_name} reference.[^note]\n\n[^NOTE]: {skill_name} reference note.\n"
        )
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    for filename in ("skills/alpha.md", "plugins/engineering.md"):
        document = (out / filename).read_text()
        definitions = _footnote_definitions(document)
        assert len(definitions) == (2 if filename.startswith("skills") else 4)
        resolved = 0
        for skill_name in ("alpha", "beta"):
            for kind in ("body", "reference"):
                for match in re.finditer(rf"{skill_name} {kind}\.{FOOTNOTE_LABEL}", document):
                    assert definitions[match[1]] == f"{skill_name} {kind} note."
                    resolved += 1
        # Every use must have been rewritten, or the loop above proves nothing.
        assert resolved == len(definitions)
        assert "[^NOTE]" not in document and "[^note]" not in document
        # One document may define a label once; two definitions would silently drop one.
        assert len(re.findall(rf"^{FOOTNOTE_LABEL}:", document, re.M)) == len(definitions)


def test_portable_reference_frontmatter_is_stripped_before_flattening(mini_repo, tmp_path):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    refs = skill / "references"
    refs.mkdir()
    source = skill / "SKILL.md"
    source.write_text(source.read_text() + "\nRead references/one.md.\n")
    (refs / "one.md").write_text(
        "---\nname: one\ndescription: Reference metadata\n---\n# One\n\nBody text.\n"
    )
    # A block that never closes is not frontmatter, so it is content and is kept verbatim.
    (refs / "two.md").write_text("---\nname: two\n# Two\n\nOther text.\n")
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out, check=True) == 0
    assert portable.export(mini_repo, out) == 0
    for filename in ("skills/alpha.md", "plugins/engineering.md"):
        document = (out / filename).read_text()
        assert "Reference metadata" not in document
        assert "description:" not in document
        assert len(re.findall(r"^#{3,} One$", document, re.M)) == 1
        assert "Body text." in document
        assert "\n---\nname: two\n" in document


@pytest.mark.parametrize("anchor", ['<a id="sample">', '<a name="sample"></a>'])
def test_portable_custom_anchor_in_inline_code_is_accepted_but_real_one_is_not(
    mini_repo, tmp_path, anchor, capsys
):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    source = skill / "SKILL.md"
    original = source.read_text()
    source.write_text(original + f"\nWrite `{anchor}` or ``{anchor}`` to name a target.\n")
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out, check=True) == 0
    assert portable.export(mini_repo, out) == 0
    assert f"`{anchor}`" in (out / "skills/alpha.md").read_text()
    # An anchor outside code, and one beside an unclosed backtick, must still be refused.
    for prose in (f"\nWrite {anchor} here.\n", f"\nWrite `{anchor} here.\n", f"\n`x` {anchor}\n"):
        source.write_text(original + prose)
        for check in (True, False):
            assert portable.export(mini_repo, out, check=check) == 1
            assert "unsupported custom HTML anchor" in capsys.readouterr().out


def test_portable_footnote_like_title_without_a_definition_is_reported_not_a_crash(
    mini_repo, tmp_path, capsys
):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    refs = skill / "references"
    refs.mkdir()
    source = skill / "SKILL.md"
    source.write_text(source.read_text() + "\nRead references/one.md.\n")
    (refs / "one.md").write_text("# [^t]: Title\n\nBody.\n")
    out = tmp_path / "portable"
    # The title is read as a reference definition whose destination resolves nowhere.
    assert portable.export(mini_repo, out, check=True) == 1
    assert "::error::alpha still points at" in capsys.readouterr().out
    assert not out.exists()


def test_portable_footnote_label_followed_by_a_destination_stays_a_link(mini_repo, tmp_path):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    source = skill / "SKILL.md"
    source.write_text(
        source.read_text() + "\nSee [^x](https://example.com/a) and "
        "![^x](https://example.com/i.png) then a claim.[^x]\n\n[^x]: Note.\n"
    )
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    document = (out / "skills/alpha.md").read_text()
    line = next(line for line in document.splitlines() if line.startswith("See "))
    assert line.startswith("See [^x](https://example.com/a) and ![^x](https://example.com/i.png)")
    assert re.search(rf"then a claim\.{FOOTNOTE_LABEL}$", line)
    assert len(_footnote_definitions(document)) == 1


def test_portable_footnote_use_after_an_unbound_reference_label_is_scoped(mini_repo, tmp_path):
    skill = mini_repo / "plugins/engineering/skills/alpha"
    source = skill / "SKILL.md"
    source.write_text(source.read_text() + "\nSee [word][^x] here.\n\n[^x]: Note.\n")
    out = tmp_path / "portable"
    assert portable.export(mini_repo, out) == 0
    document = (out / "skills/alpha.md").read_text()
    assert re.search(rf"^See \[word\]{FOOTNOTE_LABEL} here\.$", document, re.M)
    assert len(_footnote_definitions(document)) == 1


def _export_alpha(mini_repo, tmp_path, addition, *, check=True):
    source = mini_repo / "plugins/engineering/skills/alpha/SKILL.md"
    source.write_text(source.read_text() + "\n" + addition)
    out = tmp_path / "portable"
    status = portable.export(mini_repo, out, check=check)
    return status, out


def test_portable_multiline_code_span_is_left_exactly_as_written(mini_repo, tmp_path):
    example = "Use `a [target] and\n[local](missing.md)` here, then [ref] outside.\n"
    status, out = _export_alpha(
        mini_repo,
        tmp_path,
        example + "\n[target]: https://example.com\n[ref]: https://example.com/r\n",
    )
    assert status == 0
    assert portable.export(mini_repo, out) == 0
    document = (out / "skills/alpha.md").read_text()
    # The span, spread over two lines, is untouched; the shortcut reference after it is scoped.
    assert re.search(
        r"Use `a \[target\] and\n\[local\]\(missing\.md\)` here, then "
        r"\[ref\]\[?portable-reference-[a-f0-9]+\]",
        document,
    )
    assert "[target][portable-reference-" not in document


def test_portable_code_span_does_not_cross_a_paragraph_boundary(mini_repo, tmp_path, capsys):
    # An unmatched backtick must not swallow a link in the next paragraph or heading.
    for addition in (
        "An open `tick\n\n[gone](missing.md) and `close`.\n",
        "A `tick\n- [gone](missing.md) `x`\n",
    ):
        status, _ = _export_alpha(mini_repo, tmp_path, addition)
        assert status == 1
        assert "missing.md" in capsys.readouterr().out
        source = mini_repo / "plugins/engineering/skills/alpha/SKILL.md"
        source.write_text(source.read_text().replace(addition, ""))


def test_portable_html_comment_is_inert_but_prose_around_it_is_not(mini_repo, tmp_path, capsys):
    refs = mini_repo / "plugins/engineering/skills/alpha/references"
    refs.mkdir()
    (refs / "one.md").write_text("# One\n\nBody.\n")
    addition = (
        "<!-- [hidden](missing.md)\n[more](gone.md)\n## Not a heading -->\n"
        "See [one](references/one.md) <!-- [x](missing.md) --> and [two](references/one.md).\n"
    )
    status, out = _export_alpha(mini_repo, tmp_path, addition)
    assert status == 0
    assert portable.export(mini_repo, out) == 0
    document = (out / "skills/alpha.md").read_text()
    assert "<!-- [hidden](missing.md)\n[more](gone.md)\n## Not a heading -->" in document
    assert "<!-- [x](missing.md) -->" in document
    line = next(line for line in document.splitlines() if line.startswith("See "))
    assert "references/one.md" not in line
    assert line.count("](#portable-") == 2
    assert "not-a-heading" not in document
    # The comment protects only what is inside it.
    status, _ = _export_alpha(mini_repo, tmp_path, "<!-- hidden --> [real](missing.md)\n")
    assert status == 1
    assert "missing.md" in capsys.readouterr().out


def test_portable_html_comment_hides_an_anchor_example_but_not_the_text_after_it(
    mini_repo, tmp_path, capsys
):
    status, _ = _export_alpha(mini_repo, tmp_path, '<!-- <a id="x"> -->\n')
    assert status == 0
    status, _ = _export_alpha(mini_repo, tmp_path, '<!-- note --> <a id="x">\n')
    assert status == 1
    assert "unsupported custom HTML anchor" in capsys.readouterr().out


@pytest.mark.parametrize("prefix", ["> ", ">> ", "- ", "1. ", "> - "])
def test_portable_fence_nested_in_a_container_is_code(mini_repo, tmp_path, prefix):
    pad = " " * len(prefix.replace(">", " "))
    addition = (
        f"{prefix}```markdown\n{pad}[x](missing.md) and [y][ref]\n{pad}## Not a heading\n"
        f"{pad}```\n\nAfter [one](#heading) the fence.\n\n## Heading\n"
    )
    if prefix.startswith(">"):
        addition = addition.replace(f"\n{pad}", f"\n{prefix}")
    status, out = _export_alpha(mini_repo, tmp_path, addition)
    assert status == 0
    assert portable.export(mini_repo, out) == 0
    document = (out / "skills/alpha.md").read_text()
    assert "[x](missing.md) and [y][ref]" in document
    assert "not-a-heading" not in document


def test_portable_container_fence_ends_at_its_closing_marker(mini_repo, tmp_path, capsys):
    status, _ = _export_alpha(mini_repo, tmp_path, "> ```\n> code\n> ```\n\n[gone](missing.md)\n")
    assert status == 1
    assert "missing.md" in capsys.readouterr().out


def test_portable_heading_slug_keeps_entities_literal_inside_code(mini_repo, tmp_path):
    addition = (
        "## Use `&copy;`\n\n## Fish &amp; chips\n\n"
        "See [code](#use-copy) and [prose](#fish--chips).\n"
    )
    status, out = _export_alpha(mini_repo, tmp_path, addition)
    assert status == 0
    assert portable.export(mini_repo, out) == 0
    document = (out / "skills/alpha.md").read_text()
    assert document.count("](#portable-") == 2
    assert "(#use-copy)" not in document


@pytest.mark.parametrize(
    "tag",
    [
        '<span data-name="x">hi</span>',
        '<a title="name=x">t</a>',
        "<a title='id=x'>t</a>",
        '<div aria-id="x" class="n">x</div>',
        '<img src="a.png" alt="name = x">',
    ],
)
def test_portable_attributes_that_only_contain_id_or_name_are_accepted(mini_repo, tmp_path, tag):
    status, out = _export_alpha(mini_repo, tmp_path, f"{tag}\n")
    assert status == 0
    assert portable.export(mini_repo, out) == 0
    assert tag in (out / "skills/alpha.md").read_text()


@pytest.mark.parametrize(
    "tag",
    [
        '<a id="x">',
        "<a name=x>",
        "<a href='#' ID = 'x'>",
        '<span class="c" name="x">',
        '<a title="n" id=x>',
    ],
)
def test_portable_exact_id_or_name_attributes_are_still_refused(mini_repo, tmp_path, tag, capsys):
    status, _ = _export_alpha(mini_repo, tmp_path, f"{tag}\n")
    assert status == 1
    assert "unsupported custom HTML anchor" in capsys.readouterr().out


@pytest.mark.parametrize(
    "inner",
    [
        "> ```\n> # not a heading\n> [x](missing.md)\n> ```",
        "- ```\n  [x](missing.md)\n  ```",
        "~~~\n[x](missing.md)\n~~~",
    ],
)
def test_portable_fence_marker_in_another_container_does_not_close_an_open_fence(
    mini_repo, tmp_path, inner
):
    # Inside a fence every line is content: only a marker in the opener's own container ends it.
    example = f"```markdown\n{inner}\n```\n"
    status, out = _export_alpha(mini_repo, tmp_path, example)
    assert status == 0
    assert portable.export(mini_repo, out) == 0
    assert example in (out / "skills/alpha.md").read_text()


@pytest.mark.parametrize(
    "addition",
    [
        "<!-- don't ` do this -->\n[link](missing.md) `x` here\n",
        "Use `a\nfoo <!-- b` then [link](missing.md)\nnext [link2](missing.md)\n",
    ],
)
def test_portable_comment_and_code_span_do_not_open_each_other(
    mini_repo, tmp_path, addition, capsys
):
    # The construct that starts first wins: a backtick in a comment is comment text, and
    # `<!--` in a code span is code. Reading them in separate passes hid real links.
    status, _ = _export_alpha(mini_repo, tmp_path, addition)
    assert status == 1
    assert "missing.md" in capsys.readouterr().out


def test_portable_adjacent_comments_are_both_inert(mini_repo, tmp_path):
    status, out = _export_alpha(mini_repo, tmp_path, "<!-- a --><!-- b [x](missing.md) -->\n")
    assert status == 0
    assert portable.export(mini_repo, out) == 0
    assert "<!-- a --><!-- b [x](missing.md) -->" in (out / "skills/alpha.md").read_text()


def test_portable_reference_definition_inside_a_comment_defines_nothing(mini_repo, tmp_path):
    addition = "See [tgt] here.\n\n<!--\n[tgt]: https://example.com\n-->\n"
    status, out = _export_alpha(mini_repo, tmp_path, addition)
    assert status == 0
    assert portable.export(mini_repo, out) == 0
    document = (out / "skills/alpha.md").read_text()
    assert "See [tgt] here." in document
    assert "portable-reference-" not in document
    assert "<!--\n[tgt]: https://example.com\n-->" in document


def test_portable_attribute_with_no_space_before_id_is_still_refused(mini_repo, tmp_path, capsys):
    status, _ = _export_alpha(mini_repo, tmp_path, '<a href="x"id="y">\n')
    assert status == 1
    assert "unsupported custom HTML anchor" in capsys.readouterr().out


@pytest.mark.parametrize(
    "addition",
    [
        "`[x](missing.md)\n> b`\n",
        "> `[x](missing.md)\n>\n> b`\n",
        "`[x](missing.md)\n---\nb`\n",
        "`[x](missing.md)\n***\nb`\n",
        "`[x](missing.md)\n<div>\nb`\n</div>\n",
        "Text <!-- oops [x](missing.md)\nmore [y](missing.md)\n",
        "> ```\n> code\n\n[x](missing.md)\n",
        "1. ```\ntext\n[x](missing.md)\n",
        "```[x](missing.md)`\n",
        "- <!-- note\n\n[x](missing.md)\n",
        "> <!-- note\n[x](missing.md)\n",
        "`a <!-- b -->\n\n[x](missing.md) `c`\n",
    ],
)
def test_portable_block_boundaries_end_what_they_would_otherwise_hide(
    mini_repo, tmp_path, addition, capsys
):
    # Each shape is one where a renderer ends the code span, comment or fence before the
    # link, so the link is real and a missing target has to fail the export.
    status, _ = _export_alpha(mini_repo, tmp_path, addition)
    assert status == 1
    assert "missing.md" in capsys.readouterr().out


def test_portable_anchor_after_a_blockquote_break_inside_backticks_is_still_refused(
    mini_repo, tmp_path, capsys
):
    status, _ = _export_alpha(mini_repo, tmp_path, '> `a\n>\n> <a id="x"> b\n')
    assert status == 1
    assert "unsupported custom HTML anchor" in capsys.readouterr().out


def test_portable_comment_that_begins_its_line_runs_to_its_close(mini_repo, tmp_path):
    # A line-initial comment is an HTML block: unclosed it hides the rest of its container.
    status, out = _export_alpha(mini_repo, tmp_path, "<!-- oops\n[x](missing.md)\n")
    assert status == 0
    assert portable.export(mini_repo, out) == 0
    assert "<!-- oops\n[x](missing.md)" in (out / "skills/alpha.md").read_text()
