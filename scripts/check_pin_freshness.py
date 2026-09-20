#!/usr/bin/env python3
"""Report which pinned tool versions have fallen behind upstream.

Every tool CI installs or downloads is pinned, for the reason `security.yml` gives: a
tool that changes its rules between runs turns a green build into a statement about the
tool rather than about the repository. The cost of that is a set of numbers that nothing
moves. Dependabot does not help here — its `github-actions` ecosystem updates the `uses:`
references and reusable workflows, and it never looks inside an `env:` block — so the
eleven `*_VERSION` pins, the two `*_SHA256` digests beside them and `MARKDOWNLINT_PIN` in
the `Makefile` would sit where they are until somebody happened to wonder.

This is the nag that stops that. It reads each pin out of the workflows, asks the
registry the tool actually publishes to what the latest release is, and prints a table.

It is not a gate and must not become one. It needs the network and three third-party
registries to be up, and `scheduled.yml` exists precisely for checks with that shape: a
gate that fails because someone else's server was briefly down is a gate people learn to
override, and once they learn that, the gates that matter stop working too. Nothing
requires the workflow this runs in, so a non-zero exit is a red mark on a weekly run
rather than a blocked merge.

What it does not do is bump anything. Reading a version is cheap and safe; deciding to
adopt it is the judgement the pinning exists to preserve — a digest has to move with its
version, ruff 0.16 reformatted Markdown code blocks, and a pytest major can change
collection. The output tells you what is available; a person still decides.

A `*_VERSION` in a workflow with no entry in SOURCES is reported rather than ignored. The
table is written by hand and the workflows are not, so without that the table falls
quietly behind the thing it describes, which is the failure every check in this directory
is written against.

`*_SHA256` pins are not looked up. A digest follows its version, and the jobs that
download something check theirs against the artefact at the moment it matters and fail
before the binary runs, which is a stronger statement than anything available here.

Standard library only, like the checks it sits beside. The network call is injected
rather than reached for, so the tests exercise every path from a table instead of the
internet — the same shape as the fake CLI the eval harness is tested against.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

WORKFLOW_DIR = Path(".github") / "workflows"
MAKEFILE = Path("Makefile")
PIN_RE = re.compile(r"^\s*([A-Z][A-Z0-9_]*_VERSION):\s*'([^']*)'\s*(?:#.*)?$")
MARKDOWNLINT_PIN_RE = re.compile(r"^MARKDOWNLINT_PIN\s*:?=\s*(\S+)", re.M)
# `- uses: DavidAnson/markdownlint-cli2-action@<sha>  # v24.2.0`
MARKDOWNLINT_ACTION_RE = re.compile(r"markdownlint-cli2-action@[0-9a-f]{40}\s+#\s*(v\S+)")

# Where each pin's upstream lives. Written by hand, and checked against the workflows
# below so it cannot fall behind them.
SOURCES = {
    "RUFF_VERSION": ("pypi", "ruff"),
    "ZIZMOR_VERSION": ("pypi", "zizmor"),
    "CODESPELL_VERSION": ("pypi", "codespell"),
    "YAMLLINT_VERSION": ("pypi", "yamllint"),
    "PYTEST_VERSION": ("pypi", "pytest"),
    "COVERAGE_VERSION": ("pypi", "coverage"),
    "GITLEAKS_VERSION": ("github", "gitleaks/gitleaks"),
    "ACTIONLINT_VERSION": ("github", "rhysd/actionlint"),
    "CLAUDE_CODE_VERSION": ("npm", "@anthropic-ai/claude-code"),
    "CODEX_VERSION": ("npm", "@openai/codex"),
    "GEMINI_CLI_VERSION": ("npm", "@google/gemini-cli"),
}


def fetch(url: str) -> str:
    """GET a URL and return its body, with the job token when one is in the environment.

    Unauthenticated `api.github.com` allows sixty requests an hour per IP address, which
    a shared runner exhausts without this repository doing anything wrong. The token is
    optional so a local run works without one.
    """
    # S310 wants the scheme audited before a URL is opened, because `file:` and custom
    # schemes reach places a GET is not expected to. This is that audit: every URL built
    # here is a literal joined with a name out of SOURCES, and anything else is refused
    # before a request object exists.
    if not url.startswith("https://"):
        raise ValueError(f"refusing to fetch a non-https URL: {url}")
    # No cover below this line, and deliberately: these are the statements that make a
    # real request, and a test that exercised them would put the suite on the network.
    # Everything that decides anything takes the fetcher as an argument instead.
    request = urllib.request.Request(  # noqa: S310 - https enforced above  # pragma: no cover
        url, headers={"User-Agent": "check-pin-freshness"}
    )
    token = os.environ.get("GH_TOKEN", "")  # pragma: no cover
    if token and url.startswith("https://api.github.com/"):  # pragma: no cover
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310  # pragma: no cover
        return response.read().decode("utf-8")


def latest(registry: str, package: str, get) -> str:
    """The newest published version of one package, however its registry spells that."""
    if registry == "pypi":
        return json.loads(get(f"https://pypi.org/pypi/{package}/json"))["info"]["version"]
    if registry == "npm":
        return json.loads(get(f"https://registry.npmjs.org/{package}/latest"))["version"]
    if registry == "github":
        tag = json.loads(get(f"https://api.github.com/repos/{package}/releases/latest"))["tag_name"]
        return tag.lstrip("v")
    raise ValueError(f"no such registry: {registry}")


def pinned(root: Path) -> dict[str, list[str]]:
    """Every `*_VERSION` pin across the workflows, mapped to where it was found."""
    found: dict[str, list[str]] = {}
    for pattern in ("*.yml", "*.yaml"):
        for path in sorted((root / WORKFLOW_DIR).glob(pattern)):
            for line in path.read_text(encoding="utf-8").splitlines():
                match = PIN_RE.match(line)
                if match:
                    found.setdefault(match.group(1), []).append(match.group(2))
    return found


def markdownlint(root: Path, get) -> tuple[str, str] | None:
    """What the Makefile says markdownlint-cli2 is, against what the action ships.

    The action bundles the CLI, so the Makefile's copy of that version is a claim about
    somebody else's `package.json`. It cannot be checked offline, and it goes stale
    silently the first time Dependabot bumps the action.
    """
    makefile = root / MAKEFILE
    workflow = root / WORKFLOW_DIR / "ci.yml"
    if not makefile.is_file() or not workflow.is_file():
        return None
    pin = MARKDOWNLINT_PIN_RE.search(makefile.read_text(encoding="utf-8"))
    tag = MARKDOWNLINT_ACTION_RE.search(workflow.read_text(encoding="utf-8"))
    if not pin or not tag:
        return None
    url = (
        "https://raw.githubusercontent.com/DavidAnson/markdownlint-cli2-action/"
        f"{tag.group(1)}/package.json"
    )
    shipped = json.loads(get(url)).get("dependencies", {}).get("markdownlint-cli2", "")
    return pin.group(1), shipped


def check(root: Path, get=None) -> int:
    """Resolve `fetch` at call time rather than binding it as a default.

    A default argument is evaluated once, when the function is defined, so `get=fetch`
    cannot be replaced afterwards — a test that swapped the module's `fetch` would still
    reach the real registries, which is how the suite for this file first went to the
    network without meaning to. A suite that can accidentally make a request is a suite
    that fails when someone else's server does.
    """
    get = fetch if get is None else get
    rows: list[tuple[str, str, str, str]] = []
    problems = 0

    for name, values in sorted(pinned(root).items()):
        current = values[0]
        if name not in SOURCES:
            rows.append((name, current, "—", "no upstream registered"))
            problems += 1
            continue
        registry, package = SOURCES[name]
        try:
            newest = latest(registry, package, get)
        except (urllib.error.URLError, OSError, ValueError, KeyError, json.JSONDecodeError) as err:
            rows.append((name, current, "?", f"could not ask {registry}: {err}"))
            problems += 1
            continue
        if newest == current:
            rows.append((name, current, newest, "current"))
        else:
            rows.append((name, current, newest, "**behind**"))
            problems += 1

    try:
        pair = markdownlint(root, get)
    except (urllib.error.URLError, OSError, ValueError, KeyError, json.JSONDecodeError) as err:
        pair = None
        rows.append(("MARKDOWNLINT_PIN", "?", "?", f"could not ask the action: {err}"))
        problems += 1
    if pair is not None:
        recorded, shipped = pair
        state = "current" if recorded == shipped else "**does not match the action**"
        rows.append(("MARKDOWNLINT_PIN", recorded, shipped, state))
        if recorded != shipped:
            problems += 1

    print("| Pin | Pinned | Upstream | State |")
    print("| --- | --- | --- | --- |")
    for name, current, newest, state in rows:
        print(f"| `{name}` | {current} | {newest} | {state} |")
    print()
    if problems:
        print(
            f"{problems} of {len(rows)} pin(s) need a look. Bumping one is a decision, "
            f"not a formality: a digest has to move with its version, and a tool that "
            f"changes its rules is why these are pinned at all."
        )
        return 1
    print(f"all {len(rows)} pin(s) are current")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_pin_freshness", description=__doc__.split("\n", 1)[0]
    )
    parser.add_argument("root", nargs="?", default=".", type=Path, help="repository root")
    args = parser.parse_args(argv)
    return check(args.root.resolve())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
