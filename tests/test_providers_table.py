"""The README's table of AI tools, rendered from providers.json and checked against it.

Every row is a claim about someone else's product. The gate exists so that the table
cannot drift from the data it was rendered from, the data cannot carry a row nobody can
re-verify, and a row nobody has re-verified in a while says so without turning CI red.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from tests.conftest import REPO, load_script

providers = load_script("providers_table.py")

TODAY = date(2026, 9, 23)


def row(**overrides):
    base = {
        "provider": "Acme",
        "tool": "Acme CLI",
        "agents_md": "Yes",
        "skills": "No",
        "use": "Append a bundle to `AGENTS.md`",
        "sources": ["https://acme.test/docs"],
        "verified": "2026-09-01",
    }
    base.update(overrides)
    return base


def setup(tmp_path, tools=None, readme=None, stale_after_days=180, raw=None):
    data = {"stale_after_days": stale_after_days, "tools": tools or [row()]}
    (tmp_path / providers.PROVIDERS_FILE).write_text(
        raw if raw is not None else json.dumps(data), encoding="utf-8"
    )
    if readme is None:
        readme = f"# Title\n\nLead-in.\n\n{providers.START}\n{providers.END}\n\n## Next\n"
    (tmp_path / providers.README).write_text(readme, encoding="utf-8")
    return tmp_path


def run(root, *args):
    return providers.main([str(root), "--today", TODAY.isoformat(), *args])


def errors(out):
    return [line for line in out.splitlines() if line.startswith("::error")]


# --- rendering and the check -------------------------------------------------------


def test_the_check_passes_after_write_and_the_block_is_what_render_produces(tmp_path, capsys):
    root = setup(tmp_path)
    assert run(root, "--write") == 0
    assert run(root) == 0
    assert "providers table is current: 1 tool(s)" in capsys.readouterr().out
    text = (root / "README.md").read_text(encoding="utf-8")
    assert text.startswith("# Title\n\nLead-in.\n\n<!-- providers-table:start -->\n")
    assert text.endswith("<!-- providers-table:end -->\n\n## Next\n")
    assert providers.NOTE in text
    assert "--write ." in providers.NOTE
    assert (
        "| Acme | Acme CLI | Yes | No | Append a bundle to `AGENTS.md` | "
        "[2026-09-01](https://acme.test/docs) |"
    ) in text
    assert (
        "| Provider | Tool | Reads `AGENTS.md` | Loads skills | How to use this library | Checked |"
    ) in text


def test_additional_sources_render_as_numbered_links(tmp_path):
    root = setup(
        tmp_path,
        tools=[row(sources=["https://a.test/1", "https://a.test/2", "https://a.test/3"])],
    )
    assert run(root, "--write") == 0
    text = (root / "README.md").read_text(encoding="utf-8")
    assert (
        "[2026-09-01](https://a.test/1), [2](https://a.test/2), [3](https://a.test/3) |"
    ) in text


def test_a_readme_block_that_differs_fails_and_names_the_fix(tmp_path, capsys):
    root = setup(tmp_path)
    assert run(root, "--write") == 0
    readme = root / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace("| Yes |", "| Hand-edited |"),
        encoding="utf-8",
    )
    capsys.readouterr()
    assert run(root) == 1
    out = capsys.readouterr().out
    assert errors(out) == [
        "::error file=README.md::the providers table in README.md does not match "
        "providers.json; run `python scripts/providers_table.py --write .` (or `make "
        "providers`) and commit the result"
    ]


def test_an_empty_block_fails_until_written(tmp_path, capsys):
    # The shape of a freshly added pair of markers, and of a data edit nobody rendered.
    root = setup(tmp_path)
    assert run(root) == 1
    assert "does not match providers.json" in capsys.readouterr().out


@pytest.mark.parametrize(
    "body",
    [
        "# Title\n\nNo markers here.\n",
        f"# Title\n\n{providers.START}\n",
        f"# Title\n\n{providers.END}\n",
        f"{providers.START}\n{providers.END}\n{providers.START}\n{providers.END}\n",
    ],
    ids=["none", "no-end", "no-start", "twice"],
)
def test_missing_or_repeated_markers_fail_in_both_modes(tmp_path, capsys, body):
    root = setup(tmp_path, readme=body)
    assert run(root) == 1
    assert run(root, "--write") == 1
    out = capsys.readouterr().out
    assert "::error file=README.md::expected one <!-- providers-table:start -->" in out
    # --write must not guess where the table belongs.
    assert (root / "README.md").read_text(encoding="utf-8") == body


def test_markers_in_the_wrong_order_fail(tmp_path, capsys):
    root = setup(tmp_path, readme=f"{providers.END}\n{providers.START}\n")
    assert run(root) == 1
    assert "marker comes before" in capsys.readouterr().out


def test_write_is_idempotent(tmp_path, capsys):
    root = setup(tmp_path)
    assert run(root, "--write") == 0
    first = (root / "README.md").read_text(encoding="utf-8")
    assert run(root, "--write") == 0
    assert (root / "README.md").read_text(encoding="utf-8") == first
    assert "already current" in capsys.readouterr().out


def test_rows_sort_by_provider_then_tool_ignoring_case(tmp_path):
    tools = [
        row(provider="Zeta", tool="B"),
        row(provider="acme", tool="Zed"),
        row(provider="Acme", tool="alpha"),
        row(provider="Beta", tool="A"),
    ]
    root = setup(tmp_path, tools=tools)
    assert run(root, "--write") == 0
    text = (root / "README.md").read_text(encoding="utf-8")
    order = [
        line.split(" | ")[:2]
        for line in text.splitlines()
        if line.startswith("| ") and "---" not in line and "Provider" not in line
    ]
    assert order == [["| Acme", "alpha"], ["| acme", "Zed"], ["| Beta", "A"], ["| Zeta", "B"]]


# --- validation --------------------------------------------------------------------


def check_problem(tmp_path, capsys, expected, **kwargs):
    root = setup(tmp_path, **kwargs)
    before = (root / "README.md").read_text(encoding="utf-8")
    assert run(root, "--write") == 1
    out = capsys.readouterr().out
    assert any(line.startswith("::error file=providers.json::") for line in errors(out))
    assert expected in out, out
    # A data problem is reported before anything is written.
    assert (root / "README.md").read_text(encoding="utf-8") == before


@pytest.mark.parametrize("key", sorted(providers.ROW_KEYS))
def test_a_missing_key_fails(tmp_path, capsys, key):
    broken = row()
    del broken[key]
    check_problem(tmp_path, capsys, f"is missing {key!r}", tools=[broken])


def test_an_http_source_fails(tmp_path, capsys):
    check_problem(
        tmp_path,
        capsys,
        "tools[0] (Acme Acme CLI) source 'http://acme.test/docs' is not an https URL",
        tools=[row(sources=["http://acme.test/docs"])],
    )


@pytest.mark.parametrize("url", ["https://acme.test/a b", "https://acme.test/(x)"])
def test_a_source_that_would_break_the_link_fails(tmp_path, capsys, url):
    check_problem(tmp_path, capsys, "which would break the link", tools=[row(sources=[url])])


def test_a_source_that_is_not_a_string_fails(tmp_path, capsys):
    check_problem(tmp_path, capsys, "source 7 is not a string", tools=[row(sources=[7])])


@pytest.mark.parametrize("sources", [[], "https://acme.test/docs"])
def test_empty_or_non_list_sources_fail(tmp_path, capsys, sources):
    check_problem(
        tmp_path,
        capsys,
        "'sources' must be a non-empty list of https URLs",
        tools=[row(sources=sources)],
    )


@pytest.mark.parametrize(
    "value", ["2026-13-01", "23/09/2026", "20260923", "2026-09-23\n", 20260923]
)
def test_a_bad_date_fails(tmp_path, capsys, value):
    check_problem(
        tmp_path,
        capsys,
        f"'verified' must be a date in YYYY-MM-DD form, got {value!r}",
        tools=[row(verified=value)],
    )


@pytest.mark.parametrize("value", ["Yes | No", "Yes\nNo", "Yes\rNo"])
def test_a_pipe_or_line_break_in_a_cell_fails(tmp_path, capsys, value):
    check_problem(
        tmp_path,
        capsys,
        "'skills' contains a '|' or a line break, which would break the Markdown table",
        tools=[row(skills=value)],
    )


@pytest.mark.parametrize("value", ["", "   ", None, 3])
def test_an_empty_or_non_string_cell_fails(tmp_path, capsys, value):
    check_problem(tmp_path, capsys, "'use' must be a non-empty string", tools=[row(use=value)])


def test_an_unknown_row_key_fails(tmp_path, capsys):
    check_problem(tmp_path, capsys, "has unknown key 'source'", tools=[row(source=[])])


def test_a_duplicate_row_fails(tmp_path, capsys):
    check_problem(
        tmp_path, capsys, "duplicates an earlier row for Acme Acme CLI", tools=[row(), row()]
    )


def test_a_row_that_is_not_an_object_fails(tmp_path, capsys):
    check_problem(tmp_path, capsys, "tools[1] must be an object", tools=[row(), "Acme"])


def test_a_row_without_names_is_labelled_by_position(tmp_path, capsys):
    check_problem(
        tmp_path, capsys, "tools[0] is missing 'provider'", tools=[{"verified": "2026-09-01"}]
    )


@pytest.mark.parametrize("value", [0, -1, True, "180", None])
def test_stale_after_days_must_be_a_positive_integer(tmp_path, capsys, value):
    check_problem(
        tmp_path,
        capsys,
        "'stale_after_days' must be a positive whole number of days",
        stale_after_days=value,
    )


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("[]", "must be an object with 'stale_after_days' and 'tools'"),
        ('{"stale_after_days": 180, "tools": []}', "'tools' must be a non-empty list"),
        ('{"stale_after_days": 180}', "'tools' must be a non-empty list"),
        (
            '{"stale_after_days": 180, "tools": [], "notes": 1}',
            "unknown top-level key 'notes'",
        ),
        ("{not json", "providers.json is not valid JSON"),
    ],
)
def test_a_malformed_file_fails(tmp_path, capsys, raw, expected):
    check_problem(tmp_path, capsys, expected, raw=raw)


def test_a_missing_providers_file_fails(tmp_path, capsys):
    (tmp_path / "README.md").write_text(f"{providers.START}\n{providers.END}\n")
    assert run(tmp_path) == 1
    assert "::error file=providers.json::providers.json is missing" in capsys.readouterr().out


def test_a_missing_readme_fails(tmp_path, capsys):
    root = setup(tmp_path)
    (root / "README.md").unlink()
    assert run(root) == 1
    assert "::error file=README.md::README.md is missing" in capsys.readouterr().out


# --- staleness ---------------------------------------------------------------------


def test_a_stale_row_warns_and_still_passes(tmp_path, capsys):
    tools = [row(verified="2026-01-01"), row(tool="Fresh", verified="2026-09-01")]
    root = setup(tmp_path, tools=tools)
    assert run(root, "--write") == 0
    capsys.readouterr()
    assert run(root) == 0
    out = capsys.readouterr().out
    warnings = [line for line in out.splitlines() if line.startswith("::warning")]
    assert warnings == [
        "::warning file=providers.json::Acme Acme CLI last checked 2026-01-01, 265 days "
        "ago; re-verify against its sources and update the date"
    ]
    assert not errors(out)


def test_a_row_exactly_at_the_limit_is_not_stale(tmp_path, capsys):
    root = setup(tmp_path, tools=[row(verified="2026-09-13")], stale_after_days=10)
    assert run(root, "--write") == 0
    assert "::warning" not in capsys.readouterr().out
    root = setup(tmp_path, tools=[row(verified="2026-09-12")], stale_after_days=10)
    assert run(root, "--write") == 0
    assert "11 days ago" in capsys.readouterr().out


def test_today_defaults_to_the_real_date(tmp_path, capsys):
    root = setup(tmp_path, tools=[row(verified="2000-01-01")])
    assert providers.main([str(root), "--write"]) == 0
    assert "last checked 2000-01-01" in capsys.readouterr().out


# --- the repository itself ---------------------------------------------------------


def test_the_committed_readme_matches_the_committed_providers_file(capsys):
    assert providers.main([str(REPO)]) == 0
    assert "providers table is current" in capsys.readouterr().out


def test_today_comes_from_the_flag_not_the_clock(tmp_path, capsys):
    # Every other test passes the real date, so ignoring --today survived them all.
    root = setup(tmp_path, stale_after_days=1)
    assert providers.main([str(root), "--write", "--today", "2026-09-03"]) == 0
    assert "last checked 2026-09-01, 2 days ago" in capsys.readouterr().out
