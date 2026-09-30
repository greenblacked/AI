"""Tests for `scripts/check_makefile.py`.

The check keeps the `Makefile` and the CI steps that wrap the same commands in step, and
keeps the Makefile parseable by the oldest `make` a contributor is likely to have.
"""

from __future__ import annotations

from pathlib import Path

from tests.conftest import REPO, load_script

makefile_check = load_script("check_makefile.py")

MAKEFILE = """\
PYTHON ?= python3
PIN := $(shell sed -En "s/^ *V: *[\\"']?([^\\"'\\#]+)[\\"']?.*/\\1/p" w.yml)

validate:
\tPYTHONPATH=src $(PYTHON) -m skillcheck . --strict

catalogue:
\t@$(PYTHON) scripts/check_one.py .

test:
\tPYTHONPATH=src pytest

coverage:
\tPYTHONPATH=src $(PYTHON) -m coverage run -m pytest
\t$(PYTHON) -m coverage report

package:
\t@PYTHONPATH=src $(PYTHON) scripts/package_skills.py

portable:
\t@PYTHONPATH=src $(PYTHON) scripts/export_portable.py .

attribution:
\t@$(PYTHON) scripts/check_attribution.py . --range origin/main..HEAD

naming:
\t@$(PYTHON) scripts/check_naming.py . --range origin/main..HEAD
"""

WORKFLOW = """\
name: CI
on: [push]
permissions: {}

jobs:
  validate-skills:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: PYTHONPATH=src python -m skillcheck . --strict
  catalogue:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: python scripts/check_one.py .
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: PYTHONPATH=src python -m pytest
      - run: PYTHONPATH=src python -m coverage run -m pytest
      - run: python -m coverage report
  package:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: PYTHONPATH=src python scripts/package_skills.py
      - run: python scripts/verify_archives.py .
      - run: PYTHONPATH=src python scripts/export_portable.py .
  attribution:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: PYTHONPATH=src python scripts/check_attribution.py . --range "origin/main..HEAD"
  naming:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: PYTHONPATH=src python scripts/check_naming.py . --range "origin/main..HEAD"
"""

CI_DOC = """# CI

It is the one checks that keep the repository's claims about itself true.
"""

AGENTS = """# AGENTS

and the one catalogue checks

`make catalogue` is the one checks on what the repository claims about itself.
"""


def write_mini(
    root: Path,
    *,
    makefile: str = MAKEFILE,
    workflow: str = WORKFLOW,
    doc: str = CI_DOC,
    agents: str = AGENTS,
) -> Path:
    (root / "Makefile").write_text(makefile, encoding="utf-8")
    (root / "AGENTS.md").write_text(agents, encoding="utf-8")
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "ci.yml").write_text(workflow, encoding="utf-8")
    (workflows / "w.yml").write_text("RUFF_VERSION: '0.16.9'\n", encoding="utf-8")
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "ci.md").write_text(doc, encoding="utf-8")
    return root


def test_the_repository_makefile_is_in_step_with_ci():
    assert makefile_check.check(REPO) == 0


def test_a_consistent_mini_repo_passes(tmp_path):
    write_mini(tmp_path)
    assert makefile_check.check(tmp_path) == 0


def test_an_unescaped_hash_in_a_call_is_reported():
    # The exact construct that broke on GNU Make 3.81: a `#` inside `$(shell …)`.
    text = 'PIN := $(shell sed -En "s/^ *V: *([^#]+).*/\\1/p" w.yml)\n'
    assert makefile_check.unescaped_hashes_in_call(text) == [1]


def test_an_escaped_hash_in_a_call_is_accepted():
    text = 'PIN := $(shell sed -En "s/^ *V: *([^\\#]+).*/\\1/p" w.yml)\n'
    assert makefile_check.unescaped_hashes_in_call(text) == []


def test_a_hash_in_a_comment_is_not_reported():
    text = "# a note about $(shell) with a # in the comment\n"
    assert makefile_check.unescaped_hashes_in_call(text) == []


def test_a_target_that_runs_a_script_its_job_does_not_fails(tmp_path, capsys):
    write_mini(tmp_path, makefile=MAKEFILE.replace("check_one.py", "check_two.py"))
    assert makefile_check.check(tmp_path) == 1
    assert "make catalogue" in capsys.readouterr().out


def test_a_catalogue_check_the_makefile_omits_fails(tmp_path, capsys):
    # The direction that matters: a check added to CI and not to `make catalogue`.
    workflow = WORKFLOW.replace(
        "- run: python scripts/check_one.py .",
        "- run: python scripts/check_one.py .\n      - run: python scripts/check_two.py .",
    )
    write_mini(tmp_path, workflow=workflow)
    assert makefile_check.check(tmp_path) == 1
    assert "make catalogue" in capsys.readouterr().out


def test_a_stale_catalogue_count_word_fails(tmp_path, capsys):
    write_mini(tmp_path, doc=CI_DOC.replace("the one checks", "the seven checks"))
    assert makefile_check.check(tmp_path) == 1
    assert "says seven catalogue checks" in capsys.readouterr().out


def test_a_missing_target_is_reported(tmp_path, capsys):
    write_mini(
        tmp_path,
        makefile=MAKEFILE.replace(
            "\nvalidate:\n\tPYTHONPATH=src $(PYTHON) -m skillcheck . --strict\n", "\n"
        ),
    )
    assert makefile_check.check(tmp_path) == 1
    assert "no `validate` target" in capsys.readouterr().out


def test_main_runs_the_check_over_a_root(tmp_path):
    write_mini(tmp_path)
    assert makefile_check.main([str(tmp_path)]) == 0


def test_grouped_shell_regex_does_not_end_the_make_call(tmp_path, capsys):
    text = 'PIN := $(shell sed -En "s/(prefix)[^#]+/value/p" w.yml)\n'
    assert makefile_check.unescaped_hashes_in_call("\n" + text) == [2]
    assert makefile_check.unescaped_hashes_in_call(text.replace("#", r"\#")) == []
    write_mini(tmp_path, makefile=MAKEFILE + text)
    assert makefile_check.check(tmp_path) == 1
    assert "GNU Make 3.81" in capsys.readouterr().out


def test_nested_calls_and_braces_preserve_hash_line_numbers():
    text = "PIN := ${shell echo (group) # hash}\nNEXT := $(strip $(shell echo (x) # hash))\n"
    assert makefile_check.unescaped_hashes_in_call(text) == [1, 2]
    assert makefile_check.unescaped_hashes_in_call("# $(unterminated # comment\n") == []


def test_actual_make_pin_expansion_strips_comment_whitespace(tmp_path):
    import shutil
    import subprocess

    import pytest

    # Exercise the real extraction expressions, not a Python imitation of sed or Make.
    make = shutil.which("make")
    assert make is not None
    source = (REPO / "Makefile").read_text(encoding="utf-8")
    pins = "\n".join(line for line in source.splitlines() if "_PIN :=" in line)
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    for quote in ("", "'", '"'):
        for comment in ("", "   # pinned version"):
            (workflows / "security.yml").write_text(
                f"  RUFF_VERSION: {quote}0.16.9{quote}{comment}\n", encoding="utf-8"
            )
            (workflows / "ci.yml").write_text(
                f"  CODESPELL_VERSION: {quote}2.4.1{quote}{comment}\n"
                f"  ACTIONLINT_VERSION: {quote}1.7.12{quote}{comment}\n",
                encoding="utf-8",
            )
            makefile = tmp_path / "Makefile"
            makefile.write_text(
                pins + '\ncheck:\n\t@test "$(RUFF_PIN)" = "0.16.9"\n'
                '\t@test "$(CODESPELL_PIN)" = "2.4.1"\n'
                '\t@test "$(ACTIONLINT_PIN)" = "1.7.12"\n',
                encoding="utf-8",
            )
            result = subprocess.run(  # noqa: S603 - trusted repository Makefile extraction
                [make, "-C", str(tmp_path), "check"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode:
                pytest.fail(result.stdout + result.stderr)


def test_actionlint_strict_version_uses_first_line_and_rejects_missing(tmp_path):
    import os
    import shutil
    import subprocess

    make = shutil.which("make")
    sed = shutil.which("sed")
    assert make is not None and sed is not None
    source = (REPO / "Makefile").read_text(encoding="utf-8")
    start = source.index("\t@if command -v actionlint")
    end = source.index("\t@if command -v codespell", start)
    (tmp_path / "Makefile").write_text(
        "ACTIONLINT_PIN := 1.7.12\nLINT_STRICT := 1\nSHELL := /bin/bash\ncheck:\n"
        + source[start:end],
        encoding="utf-8",
    )
    binaries = tmp_path / "bin"
    binaries.mkdir()
    (binaries / "sed").symlink_to(sed)
    tool = binaries / "actionlint"
    for version, expected in (("1.7.12", 0), ("v1.7.12", 0), ("1.7.11", 2)):
        tool.write_text(
            '#!/bin/sh\nif [ "$1" = "--version" ]; then\n'
            f"printf '{version}\\ninstalled by building from source\\nbuilt with go1.25.0\\n'\n"
            "else exit 0; fi\n",
            encoding="utf-8",
        )
        tool.chmod(0o755)
        result = subprocess.run(  # noqa: S603 - trusted extracted recipe and test stub
            [make, "-C", str(tmp_path), "check"],
            env={**os.environ, "PATH": str(binaries)},
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == expected, result.stdout + result.stderr
    tool.unlink()
    result = subprocess.run(  # noqa: S603 - trusted extracted recipe
        [make, "-C", str(tmp_path), "check"],
        env={**os.environ, "PATH": str(binaries)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "actionlint not installed" in result.stdout
