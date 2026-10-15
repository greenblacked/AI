#!/usr/bin/env python3
"""Install an integrity-locked eval CLI without exposing scoring credentials."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CLIENTS = {
    "claude": ("@anthropic-ai/claude-code", "CLAUDE_CODE_VERSION"),
    "codex": ("@openai/codex", "CODEX_VERSION"),
    "gemini": ("@google/gemini-cli", "GEMINI_CLI_VERSION"),
}
CREDENTIALS = (
    "CLAUDE_CODE_OAUTH_TOKEN",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
)
CLAUDE_MACHINES = {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64", "arm64": "arm64"}


def claude_platform() -> str:
    machine = CLAUDE_MACHINES.get(platform.machine().lower())
    if machine is None or sys.platform not in ("linux", "darwin"):
        raise ValueError(f"no Claude native binary for {sys.platform} {platform.machine()}")
    if sys.platform == "linux" and platform.libc_ver()[0] != "glibc":
        return f"linux-{machine}-musl"
    return f"{sys.platform}-{machine}"


def place_claude_binary(directory: Path, version: str, packages: dict) -> None:
    """Do what the package's own postinstall would, without running its code.

    The wrapper ships a placeholder at bin/claude.exe and a postinstall that copies
    the platform's native binary over it. Lifecycle scripts are disabled, so this
    copies the binary from the integrity-locked platform package instead.
    """
    modules = directory / "node_modules" / "@anthropic-ai"
    native = modules / f"claude-code-{claude_platform()}"
    if packages.get(f"node_modules/@anthropic-ai/{native.name}", {}).get("version") != version:
        raise ValueError(f"the lockfile does not pin {native.name}@{version}")
    metadata = json.loads((native / "package.json").read_text(encoding="utf-8"))
    if metadata.get("version") != version:
        raise ValueError(f"{native.name} is {metadata.get('version')}, expected {version}")
    source = native / "claude"
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"{source} is not a regular file")
    target = modules / "claude-code" / "bin" / "claude.exe"
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as staged:
        staged_path = Path(staged.name)
        try:
            with source.open("rb") as binary:
                shutil.copyfileobj(binary, staged)
        except BaseException:
            staged_path.unlink()
            raise
    staged_path.chmod(0o755)
    staged_path.replace(target)


def install(root: Path, backend: str) -> None:
    if any(os.environ.get(name) for name in CREDENTIALS):
        raise ValueError("CLI installation must run without scoring credentials")
    package, variable = CLIENTS[backend]
    version = os.environ.get(variable)
    if not version:
        raise ValueError(f"{variable} is not set")
    directory = root / ".github" / "eval-clients" / backend
    manifest = json.loads((directory / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((directory / "package-lock.json").read_text(encoding="utf-8"))
    packages = lock["packages"]
    github_path = os.environ.get("GITHUB_PATH")
    expected = {package: version}
    if not github_path:
        raise ValueError("GITHUB_PATH is not set")
    if (
        manifest.get("dependencies") != expected
        or "scripts" in manifest
        or packages[""].get("dependencies") != expected
        or packages[f"node_modules/{package}"].get("version") != version
    ):
        raise ValueError(
            f"{backend} manifest and lockfile must match {variable}={version} "
            "and define no lifecycle scripts"
        )
    for path, entry in packages.items():
        if not path:
            continue
        if (
            not entry.get("version")
            or not entry.get("resolved", "").startswith("https://registry.npmjs.org/")
            or not entry.get("integrity", "").startswith("sha512-")
        ):
            raise ValueError(f"{path} must have a registry version and sha512 integrity")
    npm = shutil.which("npm")
    if npm is None:
        raise ValueError("npm is not installed")
    npm_env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GITHUB_", "RUNNER_", "ACTIONS_"))
    }
    # npm ci checks every tarball against the committed lockfile before extracting it.
    # Lifecycle scripts stay off: they would run as the same user, on the same
    # filesystem, as the later step that holds model credentials, so a script in any
    # locked package could alter what that step executes.
    subprocess.run(  # noqa: S603 - fixed npm command, checked-in dependency directory
        [npm, "ci", "--ignore-scripts", "--no-audit", "--no-fund"],
        cwd=directory,
        check=True,
        env=npm_env,
        timeout=300,
    )
    if backend == "claude":
        place_claude_binary(directory, version, packages)
    with Path(github_path).open("a", encoding="utf-8") as output:
        output.write(str(directory / "node_modules" / ".bin") + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", choices=CLIENTS)
    args = parser.parse_args(argv)
    try:
        install(Path(__file__).resolve().parent.parent, args.backend)
    except (
        ValueError,
        KeyError,
        OSError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as error:
        print(f"::error::eval CLI installation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
