"""The checks on the workflows themselves.

Two failures with no symptom. A job left out of the aggregate fails while the required
check reports success, so the pull request merges and the only trace is a red job nobody
has to look at. And a version pinned in two places diverges the first time one of them is
bumped, after which the eval harness scores against a different CLI than the one that
validated the manifest — a difference that shows up as a moved score rather than as an
error.
"""

from __future__ import annotations

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
    # evals.yml sets its backend versions in step-level blocks rather than at workflow
    # level, so a check that only read the top of the file would miss them entirely.
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
    assert workflows.check(REPO) == 0


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
