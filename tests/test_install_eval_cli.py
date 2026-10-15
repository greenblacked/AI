"""Credential-free installation of integrity-locked evaluation CLIs."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from tests.conftest import REPO, load_script

installer = load_script("install_eval_cli.py")

CLIENTS = {
    "claude": ("@anthropic-ai/claude-code", "CLAUDE_CODE_VERSION"),
    "codex": ("@openai/codex", "CODEX_VERSION"),
    "gemini": ("@google/gemini-cli", "GEMINI_CLI_VERSION"),
}


def write_client(root: Path, backend: str, *, valid_integrity: bool = True) -> Path:
    package, variable = CLIENTS[backend]
    version = "1.2.3"
    directory = root / ".github" / "eval-clients" / backend
    directory.mkdir(parents=True)
    dependency = {
        "version": version,
        "resolved": f"https://registry.npmjs.org/{package}/-/{backend}.tgz",
    }
    if valid_integrity:
        dependency["integrity"] = "sha512-fixture"
    manifest = {"dependencies": {package: version}}
    lock = {
        "packages": {
            "": {"dependencies": {package: version}},
            f"node_modules/{package}": dependency,
        }
    }
    (directory / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
    (directory / "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")
    return directory


@pytest.mark.parametrize("backend", CLIENTS)
def test_install_uses_checked_lock_without_credentials_and_exports_cli_path(
    tmp_path, monkeypatch, backend
):
    directory = write_client(tmp_path, backend)
    _, variable = CLIENTS[backend]
    output = tmp_path / "github-path"
    monkeypatch.setenv(variable, "1.2.3")
    monkeypatch.setenv("GITHUB_PATH", str(output))
    monkeypatch.setenv("GITHUB_ENV", str(tmp_path / "github-env"))
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "github-output"))
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path / "runner-temp"))
    monkeypatch.setenv("ACTIONS_RUNTIME_TOKEN", "fixture")
    for key in installer.CREDENTIALS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(installer.shutil, "which", lambda name: f"/usr/bin/{name}")
    calls = []
    monkeypatch.setattr(
        installer.subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs))
    )

    installer.install(tmp_path, backend)

    assert calls[0][0][0] == ["/usr/bin/npm", "ci", "--no-audit", "--no-fund"]
    assert calls[0][1]["cwd"] == directory
    assert calls[0][1]["timeout"] == 300
    assert "PATH" in calls[0][1]["env"]
    assert not any(key.startswith(("GITHUB_", "RUNNER_", "ACTIONS_")) for key in calls[0][1]["env"])
    assert output.read_text(encoding="utf-8") == str(directory / "node_modules" / ".bin") + "\n"
    assert len(calls) == 1


def test_install_refuses_scoring_credentials_before_running_npm(tmp_path, monkeypatch):
    write_client(tmp_path, "claude")
    monkeypatch.setenv("CLAUDE_CODE_VERSION", "1.2.3")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "fixture")
    monkeypatch.setattr(installer.subprocess, "run", lambda *args, **kwargs: pytest.fail("npm ran"))
    with pytest.raises(ValueError, match="without scoring credentials"):
        installer.install(tmp_path, "claude")


def test_install_rejects_a_lock_without_sha512_integrity_before_running_npm(tmp_path, monkeypatch):
    write_client(tmp_path, "gemini", valid_integrity=False)
    monkeypatch.setenv("GEMINI_CLI_VERSION", "1.2.3")
    monkeypatch.setenv("GITHUB_PATH", str(tmp_path / "github-path"))
    monkeypatch.setattr(installer.shutil, "which", lambda name: "/usr/bin/npm")
    monkeypatch.setattr(
        installer.subprocess,
        "run",
        lambda *args, **kwargs: pytest.fail("npm ran with an unverified lock entry"),
    )

    with pytest.raises(ValueError, match="sha512 integrity"):
        installer.install(tmp_path, "gemini")


def test_install_rejects_a_manifest_and_lock_version_mismatch(tmp_path, monkeypatch):
    write_client(tmp_path, "codex")
    monkeypatch.setenv("CODEX_VERSION", "9.9.9")
    monkeypatch.setenv("GITHUB_PATH", str(tmp_path / "github-path"))

    with pytest.raises(ValueError, match="must match CODEX_VERSION=9.9.9"):
        installer.install(tmp_path, "codex")


def test_install_rejects_lifecycle_scripts_before_running_npm(tmp_path, monkeypatch):
    directory = write_client(tmp_path, "claude")
    manifest = json.loads((directory / "package.json").read_text(encoding="utf-8"))
    manifest["scripts"] = {"postinstall": "node malicious.js"}
    (directory / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setenv("CLAUDE_CODE_VERSION", "1.2.3")
    monkeypatch.setenv("GITHUB_PATH", str(tmp_path / "github-path"))
    monkeypatch.setattr(installer.subprocess, "run", lambda *args, **kwargs: pytest.fail("npm ran"))

    with pytest.raises(ValueError, match="define no lifecycle scripts"):
        installer.install(tmp_path, "claude")


def test_install_requires_github_path_before_running_npm(tmp_path, monkeypatch):
    write_client(tmp_path, "claude")
    monkeypatch.setenv("CLAUDE_CODE_VERSION", "1.2.3")
    monkeypatch.delenv("GITHUB_PATH", raising=False)
    monkeypatch.setattr(installer.subprocess, "run", lambda *args, **kwargs: pytest.fail("npm ran"))

    with pytest.raises(ValueError, match="GITHUB_PATH is not set"):
        installer.install(tmp_path, "claude")


def test_committed_cli_locks_match_the_workflow_pins(tmp_path, monkeypatch):
    workflow = (REPO / ".github" / "workflows" / "evals.yml").read_text(encoding="utf-8")
    monkeypatch.setenv("GITHUB_PATH", str(tmp_path / "github-path"))
    for key in installer.CREDENTIALS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(installer.shutil, "which", lambda name: "/usr/bin/npm")
    monkeypatch.setattr(installer.subprocess, "run", lambda *args, **kwargs: None)

    for backend, (_, variable) in CLIENTS.items():
        match = re.search(rf"^  {variable}: '([^']+)'$", workflow, re.MULTILINE)
        assert match is not None
        monkeypatch.setenv(variable, match.group(1))
        installer.install(REPO, backend)


def test_install_propagates_package_manager_failure(tmp_path, monkeypatch):
    write_client(tmp_path, "codex")
    monkeypatch.setenv("CODEX_VERSION", "1.2.3")
    monkeypatch.setenv("GITHUB_PATH", str(tmp_path / "github-path"))
    monkeypatch.setattr(installer.shutil, "which", lambda name: "/usr/bin/npm")
    monkeypatch.setattr(
        installer.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.CalledProcessError(1, "npm ci")),
    )

    with pytest.raises(subprocess.CalledProcessError):
        installer.install(tmp_path, "codex")


def test_main_reports_an_install_timeout_as_a_failure(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("CODEX_VERSION", "0.160.1")
    monkeypatch.setenv("GITHUB_PATH", str(tmp_path / "github-path"))
    for key in installer.CREDENTIALS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(installer.shutil, "which", lambda name: "/usr/bin/npm")
    monkeypatch.setattr(
        installer.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            subprocess.TimeoutExpired("npm ci", timeout=300)
        ),
    )

    assert installer.main(["codex"]) == 1
    assert "eval CLI installation failed" in capsys.readouterr().err
