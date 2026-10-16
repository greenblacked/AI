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
NATIVE = "@anthropic-ai/claude-code-linux-x64"


def extract_claude(directory: Path, *, native_version: str = "1.2.3") -> Path:
    """Lay out what npm ci --ignore-scripts leaves behind for the Claude wrapper."""
    modules = directory / "node_modules" / "@anthropic-ai"
    placeholder = modules / "claude-code" / "bin" / "claude.exe"
    placeholder.parent.mkdir(parents=True)
    placeholder.write_bytes(b"placeholder")
    native = modules / "claude-code-linux-x64"
    native.mkdir()
    (native / "package.json").write_text(json.dumps({"version": native_version}), encoding="utf-8")
    (native / "claude").write_bytes(b"native binary")
    return placeholder


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
    if backend == "claude":
        lock["packages"][f"node_modules/{NATIVE}"] = {
            **dependency,
            "resolved": f"https://registry.npmjs.org/{NATIVE}/-/native.tgz",
            "optional": True,
        }
    (directory / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
    (directory / "package-lock.json").write_text(json.dumps(lock), encoding="utf-8")
    return directory


def make_bin(directory: Path, backend: str, *extra: str) -> None:
    bin_directory = directory / "node_modules" / ".bin"
    bin_directory.mkdir(parents=True, exist_ok=True)
    for name in (installer.BINARIES[backend], *extra):
        (bin_directory / name).write_text("", encoding="utf-8")


def ready_codex(tmp_path, monkeypatch):
    directory = write_client(tmp_path, "codex")
    files = {name: tmp_path / name.lower() for name in ("GITHUB_ENV", "GITHUB_PATH")}
    monkeypatch.setenv("CODEX_VERSION", "1.2.3")
    for name, path in files.items():
        monkeypatch.setenv(name, str(path))
    for key in installer.CREDENTIALS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(installer.shutil, "which", lambda name: f"/usr/bin/{name}")
    return directory, files


def test_a_locked_package_that_adds_another_command_is_refused(tmp_path, monkeypatch):
    directory, files = ready_codex(tmp_path, monkeypatch)
    monkeypatch.setattr(
        installer.subprocess, "run", lambda *args, **kwargs: make_bin(directory, "codex", "python")
    )

    with pytest.raises(ValueError, match="must hold only 'codex'"):
        installer.install(tmp_path, "codex")
    assert not files["GITHUB_PATH"].exists()


def test_a_missing_cli_command_is_refused(tmp_path, monkeypatch):
    ready_codex(tmp_path, monkeypatch)
    monkeypatch.setattr(installer.subprocess, "run", lambda *args, **kwargs: None)

    with pytest.raises(ValueError, match="must hold only 'codex', found \\[\\]"):
        installer.install(tmp_path, "codex")


@pytest.mark.parametrize("written", ["GITHUB_ENV", "GITHUB_PATH"])
def test_step_state_written_during_install_fails_and_is_emptied(tmp_path, monkeypatch, written):
    directory, files = ready_codex(tmp_path, monkeypatch)

    def npm_that_plants(*args, **kwargs):
        make_bin(directory, "codex")
        files[written].write_text("NODE_OPTIONS=--require=/tmp/planted.js\n", encoding="utf-8")

    monkeypatch.setattr(installer.subprocess, "run", npm_that_plants)

    with pytest.raises(ValueError, match="wrote to GITHUB_ENV or GITHUB_PATH"):
        installer.install(tmp_path, "codex")
    assert files[written].read_text(encoding="utf-8") == ""
    path_file = files["GITHUB_PATH"]
    assert not path_file.exists() or path_file.read_text(encoding="utf-8") == ""


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
    monkeypatch.setattr(installer, "claude_platform", lambda: "linux-x64")
    calls = []

    def fake_npm(*args, **kwargs):
        calls.append((args, kwargs))
        make_bin(directory, backend)
        if backend == "claude":
            extract_claude(directory)

    monkeypatch.setattr(installer.subprocess, "run", fake_npm)

    installer.install(tmp_path, backend)

    assert calls[0][0][0] == ["/usr/bin/npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"]
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
    monkeypatch.setenv("GITHUB_ENV", str(tmp_path / "github-env"))
    # Nothing is installed here, so there is no .bin directory to inspect.
    monkeypatch.setattr(installer, "check_cli_bin", lambda bin_directory, expected: None)
    for key in installer.CREDENTIALS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(installer.shutil, "which", lambda name: "/usr/bin/npm")
    monkeypatch.setattr(installer.subprocess, "run", lambda *args, **kwargs: None)
    placed = []
    monkeypatch.setattr(
        installer,
        "place_claude_binary",
        lambda directory, version, packages: placed.append(version),
    )

    for backend, (_, variable) in CLIENTS.items():
        match = re.search(rf"^  {variable}: '([^']+)'$", workflow, re.MULTILINE)
        assert match is not None
        monkeypatch.setenv(variable, match.group(1))
        # Each workflow step gets its own fresh GITHUB_PATH file.
        monkeypatch.setenv("GITHUB_PATH", str(tmp_path / f"github-path-{backend}"))
        installer.install(REPO, backend)
    assert len(placed) == 1


@pytest.mark.parametrize(
    "key", ["linux-x64", "linux-arm64", "linux-x64-musl", "darwin-x64", "darwin-arm64"]
)
def test_committed_claude_lock_pins_each_runner_platform_binary(key):
    lock = json.loads(
        (REPO / ".github" / "eval-clients" / "claude" / "package-lock.json").read_text(
            encoding="utf-8"
        )
    )
    packages = lock["packages"]
    version = packages["node_modules/@anthropic-ai/claude-code"]["version"]
    assert packages[f"node_modules/@anthropic-ai/claude-code-{key}"]["version"] == version


def test_claude_binary_replaces_the_placeholder_from_the_locked_native_package(
    tmp_path, monkeypatch
):
    directory = write_client(tmp_path, "claude")
    placeholder = extract_claude(directory)
    packages = json.loads((directory / "package-lock.json").read_text(encoding="utf-8"))["packages"]
    monkeypatch.setattr(installer, "claude_platform", lambda: "linux-x64")

    installer.place_claude_binary(directory, "1.2.3", packages)

    assert placeholder.read_bytes() == b"native binary"
    assert placeholder.stat().st_mode & 0o777 == 0o755
    assert sorted(path.name for path in placeholder.parent.iterdir()) == ["claude.exe"]


def test_claude_binary_refuses_a_native_package_that_is_not_in_the_lock(tmp_path, monkeypatch):
    directory = write_client(tmp_path, "claude")
    placeholder = extract_claude(directory)
    monkeypatch.setattr(installer, "claude_platform", lambda: "linux-x64")

    with pytest.raises(ValueError, match="lockfile does not pin"):
        installer.place_claude_binary(directory, "1.2.3", {})
    assert placeholder.read_bytes() == b"placeholder"


def test_claude_binary_refuses_an_extracted_version_that_differs_from_the_pin(
    tmp_path, monkeypatch
):
    directory = write_client(tmp_path, "claude")
    placeholder = extract_claude(directory, native_version="9.9.9")
    packages = json.loads((directory / "package-lock.json").read_text(encoding="utf-8"))["packages"]
    monkeypatch.setattr(installer, "claude_platform", lambda: "linux-x64")

    with pytest.raises(ValueError, match="is 9.9.9, expected 1.2.3"):
        installer.place_claude_binary(directory, "1.2.3", packages)
    assert placeholder.read_bytes() == b"placeholder"


def test_claude_binary_refuses_a_symlinked_native_binary(tmp_path, monkeypatch):
    directory = write_client(tmp_path, "claude")
    placeholder = extract_claude(directory)
    native = directory / "node_modules" / "@anthropic-ai" / "claude-code-linux-x64" / "claude"
    native.unlink()
    native.symlink_to(tmp_path / "elsewhere")
    packages = json.loads((directory / "package-lock.json").read_text(encoding="utf-8"))["packages"]
    monkeypatch.setattr(installer, "claude_platform", lambda: "linux-x64")

    with pytest.raises(ValueError, match="not a regular file"):
        installer.place_claude_binary(directory, "1.2.3", packages)
    assert placeholder.read_bytes() == b"placeholder"


def test_claude_binary_removes_the_staged_copy_when_copying_fails(tmp_path, monkeypatch):
    directory = write_client(tmp_path, "claude")
    placeholder = extract_claude(directory)
    packages = json.loads((directory / "package-lock.json").read_text(encoding="utf-8"))["packages"]
    monkeypatch.setattr(installer, "claude_platform", lambda: "linux-x64")
    monkeypatch.setattr(
        installer.shutil,
        "copyfileobj",
        lambda *args: (_ for _ in ()).throw(OSError("disk full")),
    )

    with pytest.raises(OSError, match="disk full"):
        installer.place_claude_binary(directory, "1.2.3", packages)
    assert sorted(path.name for path in placeholder.parent.iterdir()) == ["claude.exe"]
    assert placeholder.read_bytes() == b"placeholder"


@pytest.mark.parametrize(
    ("system", "machine", "libc", "expected"),
    [
        ("linux", "x86_64", "glibc", "linux-x64"),
        ("linux", "aarch64", "glibc", "linux-arm64"),
        ("linux", "x86_64", "", "linux-x64-musl"),
        ("darwin", "arm64", "", "darwin-arm64"),
    ],
)
def test_claude_platform_names_the_native_package(monkeypatch, system, machine, libc, expected):
    monkeypatch.setattr(installer.sys, "platform", system)
    monkeypatch.setattr(installer.platform, "machine", lambda: machine)
    monkeypatch.setattr(installer.platform, "libc_ver", lambda: (libc, ""))

    assert installer.claude_platform() == expected


@pytest.mark.parametrize(("system", "machine"), [("win32", "AMD64"), ("linux", "riscv64")])
def test_claude_platform_rejects_an_unsupported_runner(monkeypatch, system, machine):
    monkeypatch.setattr(installer.sys, "platform", system)
    monkeypatch.setattr(installer.platform, "machine", lambda: machine)

    with pytest.raises(ValueError, match="no Claude native binary"):
        installer.claude_platform()


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
