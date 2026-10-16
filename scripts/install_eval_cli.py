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
# The one command each backend's lockfile may put on PATH. Every later step, the
# scoring step with the keys among them, resolves commands through this directory
# first, so a locked package that shipped a `python` or `git` would shadow it.
BINARIES = {"claude": "claude", "codex": "codex", "gemini": "gemini"}
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
    # Only the CLI package may put a command on PATH, and only its own. npm links every
    # locked package's `bin` into the same directory, so a dependency declaring the
    # same name could otherwise own the one entry the check below accepts.
    commands = {path: entry["bin"] for path, entry in packages.items() if path and entry.get("bin")}
    if commands != {f"node_modules/{package}": commands.get(f"node_modules/{package}")} or set(
        commands.get(f"node_modules/{package}") or {}
    ) != {BINARIES[backend]}:
        raise ValueError(f"only {package} may declare a command, and only {BINARIES[backend]!r}")
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
    bin_directory = directory / "node_modules" / ".bin"
    check_cli_bin(bin_directory, BINARIES[backend], directory / "node_modules" / package)
    refuse_step_state(github_path, os.environ.get("GITHUB_ENV"))
    with Path(github_path).open("a", encoding="utf-8") as output:
        output.write(str(bin_directory) + "\n")


def check_cli_bin(bin_directory: Path, expected: str, package_directory: Path) -> None:
    """Refuse to put anything but the backend's own command on later steps' PATH.

    The name alone is not enough: the one entry must also resolve to a file inside the
    selected CLI package, not to whichever locked package npm linked last.
    """
    found = (
        sorted(entry.name for entry in bin_directory.iterdir()) if bin_directory.is_dir() else []
    )
    if found != [expected]:
        raise ValueError(f"{bin_directory} must hold only {expected!r}, found {found}")
    target = (bin_directory / expected).resolve()
    if not target.is_file() or not target.is_relative_to(package_directory.resolve()):
        raise ValueError(f"{bin_directory / expected} must point inside {package_directory}")


def refuse_step_state(*paths: str | None) -> None:
    """Fail, with the files emptied, if anything wrote step state during the install.

    Nothing in this step writes GITHUB_ENV or GITHUB_PATH before the installer's own
    line, and no package code runs, so an entry is unexpected. The runner applies the
    files once the step ends, failed or not, so empty them before failing.
    """
    written = [
        Path(path) for path in paths if path and Path(path).is_file() and Path(path).stat().st_size
    ]
    if written:
        for path in written:
            path.write_text("", encoding="utf-8")
        raise ValueError("the install step wrote to GITHUB_ENV or GITHUB_PATH")


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
