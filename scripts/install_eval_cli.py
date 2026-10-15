#!/usr/bin/env python3
"""Install an integrity-locked eval CLI without exposing scoring credentials."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
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
    subprocess.run(  # noqa: S603 - fixed npm command, checked-in dependency directory
        [npm, "ci", "--no-audit", "--no-fund"],
        cwd=directory,
        check=True,
        env=npm_env,
        timeout=300,
    )
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
