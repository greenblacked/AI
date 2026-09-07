"""Shared fixtures.

Two things most of the script tests need: a small but complete repository on disk, and
a stand-in for the `claude` CLI that answers from a table instead of a model. Neither
belongs in the tests that use them, because each is a hundred lines of setup that would
otherwise be copied five times and drift.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def load_script(name: str):
    """Import a file under scripts/ as a module, since scripts/ is not a package."""
    path = REPO / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    return module


def eval_set(
    name: str, positives: int = 8, negatives: int = 8, expected: str | None = None
) -> list:
    """Queries carry the target's name because the validator refuses a positive that
    two targets share, and the fake CLI answers by exact query text."""
    cases = [{"query": f"{name} positive {i}", "should_trigger": True} for i in range(positives)]
    for i in range(negatives):
        case = {"query": f"{name} negative {i}", "should_trigger": False}
        if expected and i % 2 == 0:
            case["expected"] = expected
        cases.append(case)
    return cases


def write_skill(root: Path, plugin: str, name: str, *, evals=None, description=None) -> Path:
    directory = root / "plugins" / plugin / "skills" / name
    directory.mkdir(parents=True, exist_ok=True)
    description = description or (
        f"Do the {name} thing. Use this skill whenever the user asks for {name}. "
        "Not for anything else."
    )
    (directory / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n\nBody.\n",
        encoding="utf-8",
    )
    if evals is not None:
        (directory / "evals").mkdir(exist_ok=True)
        (directory / "evals" / "trigger-eval.json").write_text(json.dumps(evals), encoding="utf-8")
    return directory


def write_agent(root: Path, plugin: str, name: str, *, evals=None) -> Path:
    directory = root / "plugins" / plugin / "agents"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.md"
    path.write_text(
        f"---\nname: {name}\ndescription: Read a large {name} input and return the short "
        f"answer. Use when someone hands over a {name} artefact.\ntools: Read\n---\n\nBody.\n",
        encoding="utf-8",
    )
    if evals is not None:
        (directory / "evals").mkdir(exist_ok=True)
        (directory / "evals" / f"{name}.json").write_text(json.dumps(evals), encoding="utf-8")
    return path


@pytest.fixture
def mini_repo(tmp_path: Path) -> Path:
    """One plugin, two skills, one subagent, all valid, all with eval sets."""
    root = tmp_path / "repo"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps(
            {
                "name": "mini",
                "owner": {"name": "Test"},
                "plugins": [{"name": "engineering", "source": "./plugins/engineering"}],
            }
        ),
        encoding="utf-8",
    )
    (root / "plugins" / "engineering" / ".claude-plugin").mkdir(parents=True)
    (root / "plugins" / "engineering" / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "engineering", "description": "test"}), encoding="utf-8"
    )
    write_skill(root, "engineering", "alpha", evals=eval_set("alpha", expected="beta"))
    write_skill(root, "engineering", "beta", evals=eval_set("beta"))
    write_agent(root, "engineering", "reader", evals=eval_set("reader", expected="alpha"))
    # The scripts locate `src/` relative to the repository root they are given.
    shutil.copytree(REPO / "src", root / "src")
    return root


FAKE_CLI = '''#!/usr/bin/env python3
"""A stand-in for any model CLI that answers from a table.

The prompt is whichever argument carries the harness's "User message:" marker, so the
same script serves as `claude -p PROMPT`, `codex exec PROMPT` or a custom command.
FAKE_ANSWERS is JSON mapping a query to an answer, or to a list of answers that are
cycled across calls (to simulate a split vote). Anything unlisted answers NONE.
FAKE_MODE selects a failure: "fail" exits 1, "empty" prints nothing, "hang" never
answers, "fenced" wraps the answer in a code fence. FAKE_ARGV_FILE, if set, receives
the argv so a test can see what the harness passed.
"""
import json, os, sys, hashlib, pathlib, time

if os.environ.get("FAKE_ARGV_FILE"):
    pathlib.Path(os.environ["FAKE_ARGV_FILE"]).write_text(json.dumps(sys.argv[1:]))
mode = os.environ.get("FAKE_MODE", "")
if mode == "fail":
    print("simulated failure", file=sys.stderr)
    sys.exit(1)
if mode == "empty":
    sys.exit(0)
if mode == "hang":
    time.sleep(30)

prompt = next((a for a in sys.argv[1:] if "User message:" in a), sys.argv[-1])
query = prompt.split("User message:\\n", 1)[1].split("\\n\\nReply", 1)[0].strip()
answers = json.loads(os.environ.get("FAKE_ANSWERS", "{}"))
answer = answers.get(query, "NONE")
if isinstance(answer, list):
    counter = pathlib.Path(os.environ["FAKE_COUNTER_DIR"]) / hashlib.md5(query.encode()).hexdigest()
    n = int(counter.read_text()) if counter.exists() else 0
    counter.write_text(str(n + 1))
    answer = answer[n % len(answer)]
# Real output has a preamble sometimes; the harness takes the last non-empty line.
print("thinking...")
if mode == "fenced":
    print("```")
    print(answer)
    print("```")
else:
    print(answer)
'''


@pytest.fixture
def fake_cli(tmp_path: Path, monkeypatch):
    """Install a fake model CLI under any name, first on PATH.

    Returns an installer: `configure = fake_cli("codex")`. The configure function it
    returns sets the answer table and the failure mode, and every fake installed in one
    test shares the same table, because the harness asks one client per run.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    counters = tmp_path / "counters"
    counters.mkdir()
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("FAKE_COUNTER_DIR", str(counters))
    monkeypatch.delenv("FAKE_MODE", raising=False)
    monkeypatch.delenv("FAKE_ARGV_FILE", raising=False)

    def configure(answers: dict | None = None, mode: str = ""):
        monkeypatch.setenv("FAKE_ANSWERS", json.dumps(answers or {}))
        if mode:
            monkeypatch.setenv("FAKE_MODE", mode)
        else:
            monkeypatch.delenv("FAKE_MODE", raising=False)
        for stale in counters.iterdir():
            stale.unlink()

    def install(name: str):
        script = bin_dir / name
        script.write_text(FAKE_CLI, encoding="utf-8")
        script.chmod(script.stat().st_mode | stat.S_IXUSR)
        configure()
        return configure

    return install


@pytest.fixture
def fake_claude(fake_cli):
    """A fake `claude` first on PATH, the harness's default backend."""
    return fake_cli("claude")
