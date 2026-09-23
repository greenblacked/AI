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
    write_readme(mini_repo, README + "\n\nAlso `searcher`, which ships to nobody.\n")
    assert readme.check(mini_repo) == 0


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
    out = tmp_path / "portable"
    out.mkdir()
    (out / "stale.md").write_text("from an older run", encoding="utf-8")
    assert portable.export(mini_repo, out) == 0
    assert not (out / "stale.md").exists()


def test_export_reports_a_tree_with_no_plugins(tmp_path):
    assert portable.main([str(tmp_path)]) == 2


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


CLAIM_SENTENCE = "Only `engineering` fit the default budget on its own.\n\n"


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
# the measurement until now, which is how `delivery` at 8,025 characters and `gamedev`
# at 8,048 — a few dozen characters over the ~8,000 default — could silently be a
# character or two from making the claim wrong in three places at once.


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

# `"skillListingBudgetFraction": 0.04` unanchored would match a value quoted in prose as
# a counter-example, the same failure mode `check_readme.py`'s digit-count check guards
# against elsewhere in this file. Anchoring to `^\s*\{ ... \}\s*$` on its own line, and
# checking every match rather than only the first, is what these two exist for.


def test_an_inline_prose_mention_is_not_read_as_a_recommendation(mini_repo, capsys):
    budget.check(mini_repo, update=True)
    (mini_repo / "README.md").write_text(
        f"# Mini\n\n{CLAIM_SENTENCE}"
        'Do not just set `"skillListingBudgetFraction": 0.04` inline; use the block below.\n\n'
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
