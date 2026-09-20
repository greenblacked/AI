"""The checks on the workflows themselves.

Two failures with no symptom. A job left out of the aggregate fails while the required
check reports success, so the pull request merges and the only trace is a red job nobody
has to look at. And a version pinned in two places diverges the first time one of them is
bumped, after which the eval harness scores against a different CLI than the one that
validated the manifest — a difference that shows up as a moved score rather than as an
error.
"""

from __future__ import annotations

import re

from tests.conftest import REPO, load_script

workflows = load_script("check_workflows.py")


GATING = """---
name: Demo
on: [push]

permissions: {}

env:
  TOOL_VERSION: '1.2.3'

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: echo build
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: echo lint
  demo:
    if: always()
    needs:
      - build
      - lint
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: echo gate
"""

# No `if: always()` and no `needs:`, so it declares no aggregate at all.
UNGATED = """---
name: Loose
on: [schedule]

permissions: {}

jobs:
  solo:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: echo solo
"""


def write_workflows(root, **files):
    directory = root / ".github" / "workflows"
    directory.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (directory / f"{name}.yml").write_text(text, encoding="utf-8")
    return root


# --- the aggregate ---------------------------------------------------------------


def test_a_complete_aggregate_passes(tmp_path, capsys):
    write_workflows(tmp_path, demo=GATING)
    assert workflows.check(tmp_path) == 0
    assert "1 aggregate(s) name every job" in capsys.readouterr().out


def test_a_job_missing_from_the_aggregate_fails(tmp_path, capsys):
    # The failure this file exists for: the required check goes green while `lint` is
    # red, so nothing stops the merge.
    write_workflows(tmp_path, demo=GATING.replace("      - lint\n", ""))
    assert workflows.check(tmp_path) == 1
    out = capsys.readouterr().out
    assert "job `lint` is missing from `demo`'s needs" in out
    assert "would not fail the required check" in out


def test_the_aggregate_naming_a_job_that_is_gone_fails(tmp_path, capsys):
    write_workflows(tmp_path, demo=GATING.replace("      - lint\n", "      - retired\n"))
    assert workflows.check(tmp_path) == 1
    assert "needs `retired`, which is not a job" in capsys.readouterr().out


def test_a_workflow_with_no_aggregate_is_skipped_not_failed(tmp_path, capsys):
    # scheduled.yml and evals.yml gate nothing, so requiring an aggregate of them would
    # be inventing a rule rather than enforcing one.
    write_workflows(tmp_path, loose=UNGATED)
    assert workflows.check(tmp_path) == 0
    assert "0 aggregate(s)" in capsys.readouterr().out


def test_two_aggregates_in_one_workflow_are_reported_not_guessed_at(tmp_path, capsys):
    second = (
        GATING
        + """  extra:
    if: always()
    needs:
      - build
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: echo extra
"""
    )
    write_workflows(tmp_path, demo=second)
    assert workflows.check(tmp_path) == 1
    assert "more than one job looks like the aggregate" in capsys.readouterr().out


def test_an_inline_needs_list_is_read(tmp_path):
    # The block list is this repository's style, not the contract; a rewrite to the
    # inline form must not make the gate go blind.
    inline = GATING.replace(
        "    needs:\n      - build\n      - lint\n", "    needs: [build, lint]\n"
    )
    write_workflows(tmp_path, demo=inline)
    assert workflows.check(tmp_path) == 0


def test_a_single_unlisted_need_is_read(tmp_path, capsys):
    single = GATING.replace("    needs:\n      - build\n      - lint\n", "    needs: build\n")
    write_workflows(tmp_path, demo=single)
    assert workflows.check(tmp_path) == 1
    assert "job `lint` is missing" in capsys.readouterr().out


def test_a_needs_shape_that_cannot_be_read_fails_loudly(tmp_path, capsys):
    # Reading it as an empty list would drop every dependency and still pass the file,
    # which is the vacuous pass this whole script is written against.
    broken = GATING.replace("      - build\n", "      build: {}\n")
    write_workflows(tmp_path, demo=broken)
    assert workflows.check(tmp_path) == 1
    assert "could not read this `needs:`" in capsys.readouterr().out


def test_a_needs_key_with_an_unreadable_value_fails_loudly(tmp_path, capsys):
    broken = GATING.replace("    needs:\n      - build\n      - lint\n", "    needs: {a: b}\n")
    write_workflows(tmp_path, demo=broken)
    assert workflows.check(tmp_path) == 1
    assert "could not read this `needs:`" in capsys.readouterr().out


def test_a_workflow_with_no_jobs_is_reported_not_skipped(tmp_path, capsys):
    write_workflows(tmp_path, demo="---\nname: Demo\non: [push]\npermissions: {}\n")
    assert workflows.check(tmp_path) == 1
    assert "found no job in this workflow" in capsys.readouterr().out


def test_a_job_key_with_a_trailing_comment_is_still_a_job(tmp_path, capsys):
    commented = GATING.replace("  lint:\n", "  lint:  # the linter\n")
    write_workflows(tmp_path, demo=commented)
    assert workflows.check(tmp_path) == 0


def test_a_top_level_key_after_the_jobs_block_ends_the_walk(tmp_path):
    trailing = GATING + "\nconcurrency:\n  group:\n    name: demo\n"
    write_workflows(tmp_path, demo=trailing)
    assert workflows.check(tmp_path) == 0


# --- the pins --------------------------------------------------------------------


def test_a_pin_that_agrees_across_workflows_passes(tmp_path, capsys):
    write_workflows(
        tmp_path,
        demo=GATING,
        loose=UNGATED.replace(
            "permissions: {}\n", "permissions: {}\n\nenv:\n  TOOL_VERSION: '1.2.3'\n"
        ),
    )
    assert workflows.check(tmp_path) == 0
    assert "1 pin(s) agree" in capsys.readouterr().out


def test_a_pin_that_disagrees_across_workflows_fails(tmp_path, capsys):
    write_workflows(
        tmp_path,
        demo=GATING,
        loose=UNGATED.replace(
            "permissions: {}\n", "permissions: {}\n\nenv:\n  TOOL_VERSION: '9.9.9'\n"
        ),
    )
    assert workflows.check(tmp_path) == 1
    out = capsys.readouterr().out
    assert "TOOL_VERSION is pinned to more than one value" in out
    assert "1.2.3" in out and "9.9.9" in out


def test_a_pin_that_disagrees_within_one_workflow_fails(tmp_path, capsys):
    # The bug this check shipped with first: collecting pins into a mapping kept
    # whichever came last, so two values in one file collapsed into one and passed.
    twice = GATING.replace(
        "      - run: echo build\n",
        "      - run: echo build\n        env:\n          TOOL_VERSION: '9.9.9'\n",
    )
    write_workflows(tmp_path, demo=twice)
    assert workflows.check(tmp_path) == 1
    out = capsys.readouterr().out
    assert "TOOL_VERSION is pinned to more than one value" in out
    assert "1.2.3" in out and "9.9.9" in out


def test_a_step_level_pin_is_seen(tmp_path, capsys):
    # evals.yml set its backend versions in step-level blocks until they were hoisted,
    # so a check that only read the top of a file would have missed them entirely.
    stepped = UNGATED.replace(
        "      - run: echo solo\n",
        "      - run: echo solo\n        env:\n          TOOL_VERSION: '1.2.3'\n",
    )
    write_workflows(tmp_path, demo=GATING, loose=stepped)
    assert workflows.check(tmp_path) == 0
    assert "1 pin(s) agree" in capsys.readouterr().out


def test_a_digest_is_compared_like_any_other_pin(tmp_path, capsys):
    write_workflows(
        tmp_path,
        demo=GATING.replace("  TOOL_VERSION: '1.2.3'\n", "  TOOL_SHA256: 'aa'\n"),
        loose=UNGATED.replace(
            "permissions: {}\n", "permissions: {}\n\nenv:\n  TOOL_SHA256: 'bb'\n"
        ),
    )
    assert workflows.check(tmp_path) == 1
    assert "TOOL_SHA256 is pinned to more than one value" in capsys.readouterr().out


# --- the tree and the entry point --------------------------------------------------


def test_a_tree_with_no_workflows_is_reported(tmp_path, capsys):
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    assert workflows.check(tmp_path) == 1


def test_main_runs_the_check_over_a_root(tmp_path):
    write_workflows(tmp_path, demo=GATING)
    assert workflows.main([str(tmp_path)]) == 0


def test_this_repository_is_consistent(capsys):
    # Asserting the count, not just the exit code. Nought aggregates also exits 0, so a
    # change that made the aggregate unrecognisable would leave `ci` and `security`
    # unchecked and this test green — which is how the `if:` pattern was too narrow for
    # a whole review cycle.
    assert workflows.check(REPO) == 0
    assert "2 aggregate(s) name every job" in capsys.readouterr().out


def test_a_comment_between_the_jobs_key_and_the_first_job_is_ignored(tmp_path):
    commented = GATING.replace("jobs:\n", "jobs:\n  # the build, then the gate\n")
    write_workflows(tmp_path, demo=commented)
    assert workflows.check(tmp_path) == 0


def test_a_blank_line_inside_a_needs_list_does_not_end_it(tmp_path):
    # A blank line is formatting, not the end of the list, and reading it as the end
    # would silently drop every entry after it.
    spaced = GATING.replace("      - build\n      - lint\n", "      - build\n\n      - lint\n")
    write_workflows(tmp_path, demo=spaced)
    assert workflows.check(tmp_path) == 0


# --- the pin freshness nag ---------------------------------------------------------

freshness = load_script("check_pin_freshness.py")

MAKEFILE = "MARKDOWNLINT_PIN := 0.23.2\n"
ACTION_TAG = (
    "      - uses: DavidAnson/markdownlint-cli2-action@"
    "21c1be1b93ad9ed58fa840aacc3f279cde2a72ff  # v24.2.0\n"
)
PINNED = (
    """---
name: CI
on: [push]

permissions: {}

env:
  RUFF_VERSION: '0.16.1'
  GITLEAKS_VERSION: '8.30.1'
  CLAUDE_CODE_VERSION: '2.1.221'

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
"""
    + ACTION_TAG
)


def answers(**overrides):
    """A fake fetcher: a table of URL to body, the shape the fake CLI uses."""
    table = {
        "https://pypi.org/pypi/ruff/json": '{"info": {"version": "0.16.1"}}',
        "https://api.github.com/repos/gitleaks/gitleaks/releases/latest": '{"tag_name": "v8.30.1"}',
        "https://registry.npmjs.org/@anthropic-ai/claude-code/latest": '{"version": "2.1.221"}',
        "https://raw.githubusercontent.com/DavidAnson/markdownlint-cli2-action/"
        "v24.2.0/package.json": '{"dependencies": {"markdownlint-cli2": "0.23.2"}}',
    }
    table.update(overrides)

    def get(url):
        if url not in table:
            raise KeyError(url)
        body = table[url]
        if isinstance(body, Exception):
            raise body
        return body

    return get


def write_pinned(root, workflow=PINNED, makefile=MAKEFILE):
    directory = root / ".github" / "workflows"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "ci.yml").write_text(workflow, encoding="utf-8")
    (root / "Makefile").write_text(makefile, encoding="utf-8")
    return root


def test_every_pin_current_passes(tmp_path, capsys):
    write_pinned(tmp_path)
    assert freshness.check(tmp_path, answers()) == 0
    assert "all 4 pin(s) are current" in capsys.readouterr().out


def test_a_pin_behind_upstream_is_reported(tmp_path, capsys):
    get = answers(**{"https://pypi.org/pypi/ruff/json": '{"info": {"version": "0.17.0"}}'})
    write_pinned(tmp_path)
    assert freshness.check(tmp_path, get) == 1
    out = capsys.readouterr().out
    assert "| `RUFF_VERSION` | 0.16.1 | 0.17.0 | **behind** |" in out


def test_a_github_tag_is_compared_without_its_v(tmp_path, capsys):
    # The releases API returns `v8.30.1` and the workflow pins `8.30.1`; comparing them
    # raw would report every GitHub-sourced tool as permanently behind.
    write_pinned(tmp_path)
    assert freshness.check(tmp_path, answers()) == 0
    assert "| `GITLEAKS_VERSION` | 8.30.1 | 8.30.1 | current |" in capsys.readouterr().out


def test_a_pin_with_no_registry_registered_is_reported(tmp_path, capsys):
    # The table is written by hand and the workflows are not, so a new pin with no
    # entry would otherwise be skipped and the table would fall quietly behind.
    extra = PINNED.replace("  RUFF_VERSION:", "  NOVEL_VERSION: '1.0.0'\n  RUFF_VERSION:")
    write_pinned(tmp_path, workflow=extra)
    assert freshness.check(tmp_path, answers()) == 1
    assert "no upstream registered" in capsys.readouterr().out


def test_a_registry_that_cannot_be_reached_is_reported_not_raised(tmp_path, capsys):
    # The whole point of running weekly and gating nothing: a registry being down is
    # a line in the table, not a traceback and not a blocked merge.
    get = answers(**{"https://pypi.org/pypi/ruff/json": OSError("connection reset")})
    write_pinned(tmp_path)
    assert freshness.check(tmp_path, get) == 1
    assert "could not ask pypi" in capsys.readouterr().out


def test_a_markdownlint_pin_that_does_not_match_the_action_is_reported(tmp_path, capsys):
    # The Makefile's copy is a claim about somebody else's package.json, and it goes
    # stale silently the first time Dependabot bumps the action.
    write_pinned(tmp_path, makefile="MARKDOWNLINT_PIN := 0.20.0\n")
    assert freshness.check(tmp_path, answers()) == 1
    assert "does not match the action" in capsys.readouterr().out


def test_a_markdownlint_lookup_that_fails_is_reported(tmp_path, capsys):
    url = (
        "https://raw.githubusercontent.com/DavidAnson/markdownlint-cli2-action/v24.2.0/package.json"
    )
    write_pinned(tmp_path)
    assert freshness.check(tmp_path, answers(**{url: OSError("no route")})) == 1
    assert "could not ask the action" in capsys.readouterr().out


def test_no_markdownlint_pin_at_all_is_not_a_finding(tmp_path, capsys):
    # A tree without that pin has nothing to disagree with.
    write_pinned(tmp_path, makefile="PYTHON ?= python3\n")
    assert freshness.check(tmp_path, answers()) == 0
    assert "MARKDOWNLINT_PIN" not in capsys.readouterr().out


def test_a_tree_with_no_makefile_skips_the_markdownlint_check(tmp_path):
    directory = tmp_path / ".github" / "workflows"
    directory.mkdir(parents=True)
    (directory / "ci.yml").write_text(PINNED, encoding="utf-8")
    assert freshness.check(tmp_path, answers()) == 0


def test_fetch_refuses_a_url_that_is_not_https():
    # The audit S310 asks for, and the reason the suppression beside it is honest.
    try:
        freshness.fetch("file:///etc/passwd")
    except ValueError as error:
        assert "non-https" in str(error)
    else:  # pragma: no cover
        raise AssertionError("fetch accepted a file: URL")


def test_an_unknown_registry_is_a_programming_error():
    try:
        freshness.latest("carrier-pigeon", "ruff", answers())
    except ValueError as error:
        assert "no such registry" in str(error)
    else:  # pragma: no cover
        raise AssertionError("latest accepted an unknown registry")


def test_main_runs_the_freshness_check_over_a_root(tmp_path, monkeypatch):
    write_pinned(tmp_path)
    monkeypatch.setattr(freshness, "fetch", answers())
    assert freshness.main([str(tmp_path)]) == 0


def test_every_pin_in_this_repository_has_a_registry(capsys):
    # Offline half of the freshness check: the table must cover what the workflows
    # actually pin, which is the part that would otherwise rot.
    unregistered = sorted(set(freshness.pinned(REPO)) - set(freshness.SOURCES))
    assert unregistered == []


# --- the two holes review found ----------------------------------------------------


def test_an_aggregate_wrapped_in_an_expression_is_still_an_aggregate(tmp_path, capsys):
    # `if: ${{ always() }}` is the same job. Matching the whole value exactly made it
    # invisible, the workflow read as gating nothing, and an incomplete needs: passed.
    wrapped = GATING.replace("    if: always()\n", "    if: ${{ always() }}\n")
    write_workflows(tmp_path, demo=wrapped.replace("      - lint\n", ""))
    assert workflows.check(tmp_path) == 1
    assert "job `lint` is missing" in capsys.readouterr().out


def test_an_aggregate_with_a_compound_condition_is_still_an_aggregate(tmp_path, capsys):
    compound = GATING.replace("    if: always()\n", "    if: always() && !cancelled()\n")
    write_workflows(tmp_path, demo=compound.replace("      - lint\n", ""))
    assert workflows.check(tmp_path) == 1
    assert "job `lint` is missing" in capsys.readouterr().out


def test_a_double_quoted_pin_is_compared(tmp_path, capsys):
    # Nothing forces single quotes — .yamllint extends default, where quoted-strings is
    # off — so a pin re-typed in double quotes must not drop out of the comparison.
    other = UNGATED.replace(
        "permissions: {}\n", 'permissions: {}\n\nenv:\n  TOOL_VERSION: "9.9.9"\n'
    )
    write_workflows(tmp_path, demo=GATING, loose=other)
    assert workflows.check(tmp_path) == 1
    assert "TOOL_VERSION is pinned to more than one value" in capsys.readouterr().out


def test_a_bare_pin_is_compared(tmp_path, capsys):
    other = UNGATED.replace("permissions: {}\n", "permissions: {}\n\nenv:\n  TOOL_VERSION: 9.9.9\n")
    write_workflows(tmp_path, demo=GATING, loose=other)
    assert workflows.check(tmp_path) == 1
    assert "TOOL_VERSION is pinned to more than one value" in capsys.readouterr().out


def test_a_pin_written_as_a_block_scalar_is_reported_not_misread(tmp_path, capsys):
    # Reading `>-` as the version string would record a value that is not one and
    # compare it against upstream for ever.
    folded = GATING.replace("  TOOL_VERSION: '1.2.3'\n", "  TOOL_VERSION: >-\n    1.2.3\n")
    write_workflows(tmp_path, demo=folded)
    assert workflows.check(tmp_path) == 1
    assert "could not read the value of `TOOL_VERSION`" in capsys.readouterr().out


def test_a_double_quoted_pin_is_read_by_the_freshness_check(tmp_path, capsys):
    write_pinned(tmp_path, workflow=PINNED.replace("'0.16.1'", '"0.16.1"'))
    assert freshness.check(tmp_path, answers()) == 0
    assert "| `RUFF_VERSION` | 0.16.1 | 0.16.1 | current |" in capsys.readouterr().out


def test_a_body_of_the_wrong_json_shape_is_a_row_not_a_traceback(tmp_path, capsys):
    # A list where an object was expected raises TypeError, which the narrow except
    # tuple missed. The raise happened mid-loop, so the table was never printed at all
    # and a job whose only output is a report produced a stack trace.
    get = answers(**{"https://pypi.org/pypi/ruff/json": "[]"})
    write_pinned(tmp_path)
    assert freshness.check(tmp_path, get) == 1
    out = capsys.readouterr().out
    assert "could not ask pypi" in out
    assert "| Pin | Pinned | Upstream | State |" in out


def test_the_token_goes_to_github_and_nowhere_else(monkeypatch):
    # A regression that sent GH_TOKEN to npm or PyPI would hand a repository-scoped
    # credential to a third party, and the pragma on the send used to hide this branch.
    monkeypatch.setenv("GH_TOKEN", "secret-value")
    github = freshness.build_request("https://api.github.com/repos/a/b/releases/latest")
    assert github.get_header("Authorization") == "Bearer secret-value"
    for elsewhere in (
        "https://pypi.org/pypi/ruff/json",
        "https://registry.npmjs.org/@openai/codex/latest",
        "https://raw.githubusercontent.com/a/b/v1/package.json",
    ):
        assert freshness.build_request(elsewhere).get_header("Authorization") is None


def test_no_token_in_the_environment_sends_no_header(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    request = freshness.build_request("https://api.github.com/repos/a/b/releases/latest")
    assert request.get_header("Authorization") is None


def test_blinding_only_the_pin_value_pattern_still_fails(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(workflows, "PIN_RE", re.compile(r"^NEVERMATCHES$"))
    write_workflows(tmp_path, demo=GATING)
    assert workflows.check(tmp_path) == 1
    assert "could not read the value of" in capsys.readouterr().out
