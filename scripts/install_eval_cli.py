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
# The one install step allowed to run: the claude-code wrapper's own postinstall,
# which copies the native binary over a placeholder. It runs from the pinned package
# whose binary receives the scoring key anyway; nothing from a dependency runs.
OWN_SETUP = {"claude": "install.cjs"}
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
    # --ignore-scripts keeps every lifecycle script in the tree from running: hiding the
    # GITHUB_* variables does not hide the runner's file-command directory, so a script
    # could still find GITHUB_ENV and steer the scoring step that holds the key.
    subprocess.run(  # noqa: S603 - fixed npm command, checked-in dependency directory
        [npm, "ci", "--ignore-scripts", "--no-audit", "--no-fund"],
        cwd=directory,
        check=True,
        env=npm_env,
        timeout=300,
    )
    setup = OWN_SETUP.get(backend)
    if setup:
        node = shutil.which("node")
        if node is None:
            raise ValueError("node is not installed")
        subprocess.run(  # noqa: S603 - fixed file inside the integrity-checked package
            [node, setup],
            cwd=directory / "node_modules" / package,
            check=True,
            env=npm_env,
            timeout=120,
        )
    refuse_step_state(github_path, os.environ.get("GITHUB_ENV"))
    with Path(github_path).open("a", encoding="utf-8") as output:
        output.write(str(directory / "node_modules" / ".bin") + "\n")


def refuse_step_state(*paths: str | None) -> None:
    """Fail, with the files emptied, if install code wrote any step state.

    The runner gives each step fresh files and applies them once the step ends, failed
    or not, so an entry here can only have come from install code. Emptying them first
    keeps it out of the steps that still run after a failure.
    """
    written = [
        Path(path) for path in paths if path and Path(path).exists() and Path(path).stat().st_size
    ]
    if written:
        for path in written:
            path.write_text("", encoding="utf-8")
        raise ValueError("install code wrote to GITHUB_ENV or GITHUB_PATH")


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
