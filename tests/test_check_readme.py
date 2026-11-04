"""The README's chapter shape: every plugin is a chapter with the same four sections.

The older catalogue checks (one row per skill, the badges, the prose counts) live in
`test_catalogue.py`, which also holds the fixture README these cases start from. What is
here is the part that makes the chapters consistent: a plugin cannot drop its project kit
section, list a subagent under another plugin, or claim a kit its `assets/` does not hold.
"""

from __future__ import annotations

import re

from tests.conftest import REPO, load_script
from tests.test_catalogue import README, _plugin_command, with_commands, write_readme

readme = load_script("check_readme.py")
portable = load_script("export_portable.py")

KIT_SECTION = """#### Project kit

| Skill | Rule | Hook | Template |
| --- | --- | --- | --- |
| `alpha` | `style` | `guard` | `runbook` |
"""


def write_kit(root, rule=True, hook=True, script=True, template=True, script_name="guard.sh"):
    assets = root / "plugins" / "engineering" / "skills" / "alpha" / "assets"
    for flag, folder, name in (
        (rule, "rules", "style.md"),
        (hook, "hooks", "guard.json"),
        (script, "hooks", script_name),
        (template, "templates", "runbook.md"),
    ):
        if flag:
            (assets / folder).mkdir(parents=True, exist_ok=True)
            (assets / folder / name).write_text("x\n", encoding="utf-8")


def with_kit(text=README, section=KIT_SECTION, kits=1):
    text = text.replace("#### Project kit\n\nNo kit yet.\n", section)
    return text.replace("2 skills, 1 subagent | 0 |", f"2 skills, 1 subagent | {kits} |")


def run(root, text, capsys):
    write_readme(root, text)
    code = readme.check(root)
    return code, capsys.readouterr().out


def test_the_fixture_with_no_kit_passes(mini_repo, capsys):
    assert run(mini_repo, README, capsys)[0] == 0


# --- chapters and their sections ------------------------------------------------------


def test_a_plugin_with_no_chapter_fails(mini_repo, capsys):
    code, out = run(mini_repo, README.replace("### Engineering", "### Other"), capsys)
    assert code == 1
    assert "engineering has no chapter" in out


def test_a_chapter_without_a_subagents_section_fails(mini_repo, capsys):
    text = README.replace(
        "#### Subagents\n\n| Subagent | Reads |\n| --- | --- |\n| `reader` | Things |\n", ""
    )
    code, out = run(mini_repo, text, capsys)
    assert code == 1
    assert "no '#### Subagents' section" in out


def test_a_chapter_without_a_project_kit_section_fails(mini_repo, capsys):
    code, out = run(mini_repo, README.replace("#### Project kit\n\nNo kit yet.\n", ""), capsys)
    assert code == 1
    assert "no '#### Project kit' section" in out


def test_sections_out_of_order_fail(mini_repo, capsys):
    text = README.replace("#### Project kit\n\nNo kit yet.\n", "")
    text = text.replace("#### Skills", "#### Project kit\n\nNo kit yet.\n\n#### Skills")
    code, out = run(mini_repo, text, capsys)
    assert code == 1
    assert "out of order" in out


def test_a_plugin_with_commands_needs_a_commands_section(mini_repo, capsys):
    _plugin_command(mini_repo)
    code, out = run(mini_repo, README, capsys)
    assert code == 1
    assert "no '#### Commands' section" in out


def test_a_commands_section_for_a_plugin_with_none_fails(mini_repo, capsys):
    code, out = run(mini_repo, with_commands("| `/sweep` | x |"), capsys)
    assert code == 1
    assert "ships no commands" in out


def test_commands_between_subagents_and_the_kit_pass(mini_repo, capsys):
    _plugin_command(mini_repo)
    text = with_commands("| `/sweep` | x |").replace(
        "2 skills, 1 subagent", "2 skills, 1 subagent, 1 command"
    )
    assert run(mini_repo, text, capsys)[0] == 0


# --- rows belong to their own plugin's chapter -----------------------------------------


def test_a_subagent_row_outside_its_chapter_fails(mini_repo, capsys):
    text = (
        README.replace("| `reader` | Things |\n", "")
        + "\n| Subagent | Reads |\n| --- | --- |\n| `reader` | x |\n"
    )
    code, out = run(mini_repo, text, capsys)
    assert code == 1
    assert "subagent reader ships with engineering and has no row" in out


def test_a_chapter_listing_a_subagent_the_plugin_does_not_ship_fails(mini_repo, capsys):
    text = README.replace(
        "| `reader` | Things |\n", "| `reader` | Things |\n| `stranger` | Else |\n"
    )
    code, out = run(mini_repo, text, capsys)
    assert code == 1
    assert "lists subagent stranger, which engineering does not ship" in out


def test_none_yet_is_accepted_for_a_plugin_without_subagents(mini_repo, capsys):
    (mini_repo / "plugins" / "engineering" / "agents" / "reader.md").unlink()
    text = README.replace(
        "| Subagent | Reads |\n| --- | --- |\n| `reader` | Things |\n", "None yet.\n"
    )
    text = text.replace("2 skills, 1 subagent", "2 skills")
    assert run(mini_repo, text, capsys)[0] == 0


def test_a_plugin_without_subagents_must_say_so(mini_repo, capsys):
    (mini_repo / "plugins" / "engineering" / "agents" / "reader.md").unlink()
    text = README.replace("| Subagent | Reads |\n| --- | --- |\n| `reader` | Things |\n", "")
    code, out = run(mini_repo, text.replace("2 skills, 1 subagent", "2 skills"), capsys)
    assert code == 1
    assert "lacks the line 'None yet.'" in out


def test_none_yet_beside_a_shipped_subagent_fails(mini_repo, capsys):
    code, out = run(
        mini_repo, README.replace("#### Subagents\n", "#### Subagents\n\nNone yet.\n"), capsys
    )
    assert code == 1
    assert "says 'None yet.'" in out


def test_a_repo_agent_listed_in_a_plugin_chapter_fails(mini_repo, capsys):
    agents = mini_repo / ".claude" / "agents"
    agents.mkdir(parents=True)
    (agents / "searcher.md").write_text(
        "---\nname: searcher\ndescription: " + "f" * 60 + "\ntools: Read\n---\n\nBody.\n",
        encoding="utf-8",
    )
    text = README.replace(
        "| `reader` | Things |\n", "| `reader` | Things |\n| `searcher` | Finds |\n"
    )
    code, out = run(mini_repo, text, capsys)
    assert code == 1
    assert "searcher is in .claude/ and has no row" in out


def test_a_repo_agent_in_the_working_section_passes(mini_repo, capsys):
    agents = mini_repo / ".claude" / "agents"
    agents.mkdir(parents=True)
    (agents / "searcher.md").write_text(
        "---\nname: searcher\ndescription: " + "f" * 60 + "\ntools: Read\n---\n\nBody.\n",
        encoding="utf-8",
    )
    assert run(mini_repo, README + "\n| `searcher` | Finds |\n", capsys)[0] == 0


def test_repo_agents_with_no_working_section_fail(mini_repo, capsys):
    agents = mini_repo / ".claude" / "agents"
    agents.mkdir(parents=True)
    (agents / "searcher.md").write_text(
        "---\nname: searcher\ndescription: " + "f" * 60 + "\ntools: Read\n---\n\nBody.\n",
        encoding="utf-8",
    )
    text = (
        README.replace("## Working on this repository", "## Elsewhere")
        + "\n| `searcher` | Finds |\n"
    )
    code, out = run(mini_repo, text, capsys)
    assert code == 1
    assert "no '## Working on this repository' section" in out


# --- the project kit --------------------------------------------------------------------


def test_a_kit_table_matching_assets_passes(mini_repo, capsys):
    write_kit(mini_repo)
    assert run(mini_repo, with_kit(), capsys)[0] == 0


def test_no_kit_line_beside_kit_files_fails(mini_repo, capsys):
    write_kit(mini_repo)
    code, out = run(mini_repo, README.replace("| 0 |", "| 1 |"), capsys)
    assert code == 1
    assert "says 'No kit yet.' and skills ship kit files" in out


def test_a_kit_table_with_no_files_fails(mini_repo, capsys):
    code, out = run(mini_repo, with_kit(kits=0), capsys)
    assert code == 1
    assert "lists a kit and no skill ships kit files" in out


def test_a_project_kit_with_neither_table_nor_line_fails(mini_repo, capsys):
    code, out = run(mini_repo, README.replace("No kit yet.\n", ""), capsys)
    assert code == 1
    assert "neither a table nor the line 'No kit yet.'" in out


def test_a_kit_file_missing_from_its_column_fails(mini_repo, capsys):
    write_kit(mini_repo)
    code, out = run(mini_repo, with_kit().replace("`runbook`", ""), capsys)
    assert code == 1
    assert "lists templates []" in out


def test_a_kit_column_naming_a_file_that_is_not_there_fails(mini_repo, capsys):
    write_kit(mini_repo, rule=False)
    code, out = run(mini_repo, with_kit(kits=0), capsys)
    assert code == 1
    assert "lists rules ['style'], and assets/rules holds []" in out


def test_a_skill_with_kit_files_and_no_row_fails(mini_repo, capsys):
    write_kit(mini_repo)
    text = with_kit(
        section=(
            "#### Project kit\n\n| Skill | Rule | Hook | Template |\n| --- | --- | --- | --- |\n"
        )
    )
    code, out = run(mini_repo, text, capsys)
    assert code == 1
    assert "alpha ships kit files in engineering and has no row" in out


def test_a_kit_row_for_a_skill_without_kit_files_fails(mini_repo, capsys):
    write_kit(mini_repo)
    text = with_kit().replace("| `alpha` |", "| `beta` | `x` | `y` | `z` |\n| `alpha` |")
    code, out = run(mini_repo, text, capsys)
    assert code == 1
    assert "row for beta, which ships no kit files" in out


# --- the kit count ---------------------------------------------------------------------


def test_the_contents_table_counts_a_complete_kit(mini_repo, capsys):
    write_kit(mini_repo)
    code, out = run(mini_repo, with_kit(kits=0), capsys)
    assert code == 1
    assert "says engineering has 0 project kits, and it has 1" in out


def test_a_kit_without_its_hook_script_is_not_complete(mini_repo, capsys):
    write_kit(mini_repo, script=False)
    assert run(mini_repo, with_kit(kits=0), capsys)[0] == 0


def test_a_hook_json_and_a_script_with_different_stems_is_not_complete(mini_repo, capsys):
    # guard.json beside check.sh: the same pair the validator's kit-hook refuses.
    write_kit(mini_repo, script_name="check.sh")
    assert run(mini_repo, with_kit(kits=0), capsys)[0] == 0


def test_a_kit_without_a_template_is_not_complete(mini_repo, capsys):
    write_kit(mini_repo, template=False)
    text = with_kit(kits=0).replace("`runbook`", "")
    assert run(mini_repo, text, capsys)[0] == 0


def test_a_contents_table_without_the_kit_column_fails(mini_repo, capsys):
    text = README.replace(" | 0 |\n", " |\n", 1)
    code, out = run(mini_repo, text, capsys)
    assert code == 1
    assert "no project kit count for engineering" in out


def test_prose_counting_project_kits_is_checked(mini_repo, capsys):
    write_kit(mini_repo)
    text = with_kit() + "\nThere are 3 project kits.\n"
    code, out = run(mini_repo, text, capsys)
    assert code == 1
    assert "says 3 project kits, and there are 1" in out


def test_prose_counting_project_kits_correctly_passes(mini_repo, capsys):
    write_kit(mini_repo)
    assert run(mini_repo, with_kit() + "\nOne project kit ships.\n", capsys)[0] == 0


# --- a chapter's skills table collapsed into <details> -------------------------------

ROWS = (
    "| Skill | What it does |\n| --- | --- |\n"
    "| [`alpha`](plugins/engineering/skills/alpha/SKILL.md) | First. |\n"
    "| [`beta`](plugins/engineering/skills/beta/SKILL.md) | Second. |\n"
)


def collapsed(summary):
    """The fixture README with the engineering skills table inside `<details>`."""
    return README.replace(ROWS, f"<details>\n<summary>{summary}</summary>\n\n{ROWS}\n</details>\n")


def test_a_skills_table_inside_details_still_counts(mini_repo, capsys):
    assert collapsed("engineering skills (2)") != README
    assert run(mini_repo, collapsed("engineering skills (2)"), capsys)[0] == 0


def test_a_skill_row_inside_details_is_still_required(mini_repo, capsys):
    text = collapsed("engineering skills (2)").replace(
        "| [`beta`](plugins/engineering/skills/beta/SKILL.md) | Second. |\n", ""
    )
    code, out = run(mini_repo, text, capsys)
    assert code == 1
    assert "beta is in the repository and has no row" in out


def test_a_summary_count_that_disagrees_with_the_plugin_fails(mini_repo, capsys):
    code, out = run(mini_repo, collapsed("engineering skills (3)"), capsys)
    assert code == 1
    assert "the engineering Skills summary says 3, and the plugin ships 2 skills" in out


def test_a_summary_without_a_count_is_not_checked(mini_repo, capsys):
    assert run(mini_repo, collapsed("Every engineering skill"), capsys)[0] == 0


def test_a_summary_count_written_as_a_prose_count_is_still_read_as_one(mini_repo, capsys):
    # The parenthesised form is the one this check owns. "2 skills" is a sentence like any
    # other and is compared with the repository total, so it cannot be used to sidestep
    # either check.
    code, out = run(mini_repo, collapsed("all 7 skills"), capsys)
    assert code == 1
    assert "says 7 skills, and there are 2" in out


def test_a_plugins_parent_heading_may_replace_skills(mini_repo, capsys):
    text = README.replace("\n## Skills\n", "\n## Plugins\n").replace("(#skills)", "(#plugins)")
    assert run(mini_repo, text, capsys)[0] == 0


# --- anchors in the README that other files link to -----------------------------------

# Renaming a README heading breaks every link to its old slug and nothing notices: the
# page still opens, only at the top. The portable export once kept pointing at
# `#chatgpt-grok-codex-and-everything-else` after the section became "Other tools".
README_LINK = re.compile(
    r"github\.com/greenblacked/AI(?:/blob/[\w.-]+/README\.md)?#([\w-]+)"
    r"|\]\(((?:\.\./|\./)*)README\.md#([\w-]+)\)"
)
# History may name a slug that no longer exists, and tests build fixture links on purpose.
UNCHECKED = {"CHANGELOG.md"}


def readme_slugs(text):
    """Every anchor GitHub gives the README: heading slugs, repeats numbered, plus ids."""
    slugs, seen, fenced = set(), {}, False
    for line in text.splitlines():
        if re.match(r"\s*(```|~~~)", line):
            fenced = not fenced
        elif not fenced and (heading := re.match(r"#{1,6}\s+(.*?)\s*#*\s*$", line)):
            slug = portable.source_slug(heading.group(1))
            count = seen.get(slug, 0)
            seen[slug] = count + 1
            slugs.add(slug if count == 0 else f"{slug}-{count}")
    slugs.update(re.findall(r'<a\s+(?:id|name)="([^"]+)"', text))
    return slugs


def readme_anchor_links():
    """(path, anchor) for each link to the repository README found outside tests/."""
    roots = [REPO / "scripts", REPO / "src", REPO / "docs", REPO / "plugins", REPO / ".claude"]
    files = [*REPO.glob("*.md")] + [f for root in roots for f in root.rglob("*") if f.is_file()]
    found = []
    for path in files:
        if path.name in UNCHECKED or path.suffix not in {".md", ".py", ".json"}:
            continue
        for match in README_LINK.finditer(path.read_text(encoding="utf-8")):
            if match.group(1):
                found.append((path, match.group(1)))
            elif (path.parent / match.group(2) / "README.md").resolve() == REPO / "README.md":
                found.append((path, match.group(3)))
    return found


def test_the_slug_rule_numbers_repeated_headings_and_skips_fenced_text():
    slugs = readme_slugs('# A b\n\n```\n# Not one\n```\n\n## A b\n\n<a id="top"></a>\n')
    assert slugs == {"a-b", "a-b-1", "top"}


def test_every_link_into_the_readme_lands_on_a_heading_it_has():
    slugs = readme_slugs((REPO / "README.md").read_text(encoding="utf-8"))
    links = readme_anchor_links()
    assert any(path.name == "export_portable.py" for path, _ in links)
    assert any(path.name == "using.md" for path, _ in links)
    broken = sorted(f"{p.relative_to(REPO)}#{a}" for p, a in links if a not in slugs)
    assert not broken, f"README has no heading for: {broken}"
