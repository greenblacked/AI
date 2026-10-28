#!/usr/bin/env python3
"""Fail when the Wrangler pin and the lockfile disagree.

``WRANGLER_VERSION`` in the workflows is the pin a person reads. ``deploy/package-lock.json``
is the pin npm checks, including the integrity of every tarball it installs. Neither is
worth having if the two can drift: a workflow that says 4.1 while the lockfile installs
4.2 is a pin that means two things, which is the failure ``scripts/check_workflows.py``
already refuses for two workflow files. This is the same check between a workflow and
the lockfile, which that one cannot see.

npm ci then checks each tarball against the integrity the lockfile recorded. This script
does not download anything.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

LOCK = Path("deploy") / "package-lock.json"
PACKAGE = Path("deploy") / "package.json"


def problems(root: Path, version: str) -> list[str]:
    """Every way ``version`` disagrees with ``deploy/``, as sentences."""
    package_path = root / PACKAGE
    lock_path = root / LOCK
    found: list[str] = []
    if not package_path.is_file() or not lock_path.is_file():
        return [f"missing {PACKAGE} or {LOCK}"]
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"deploy pin is not JSON: {error}"]
    declared = (
        package.get("dependencies", {}).get("wrangler") if isinstance(package, dict) else None
    )
    entry = (
        lock.get("packages", {}).get("node_modules/wrangler") if isinstance(lock, dict) else None
    )
    locked = entry.get("version") if isinstance(entry, dict) else None
    integrity = entry.get("integrity") if isinstance(entry, dict) else None
    if not isinstance(declared, str) or declared != version:
        found.append(f"{PACKAGE} depends on wrangler {declared!r}, not {version}")
    if not isinstance(locked, str) or locked != version:
        found.append(f"{LOCK} installs wrangler {locked!r}, not {version}")
    if not isinstance(integrity, str) or not integrity.startswith("sha512-"):
        found.append(f"{LOCK} has no sha512 integrity for wrangler")
    found.extend(_stale_overrides(package, lock))
    return found


def _exact(version: object) -> tuple[int, ...] | None:
    """``1.2.3`` as a tuple; ``None`` for a range, a tag or anything not plain."""
    if not isinstance(version, str):
        return None
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def _stale_overrides(package: object, lock: object) -> list[str]:
    """An override older than an exact version the lock's packages declare.

    An override is written for the Wrangler of the day. Once a bump brings a package
    that pins a newer version, the override silently forces the older one back onto
    the production deploy, so it has to go rather than stay.
    """
    overrides = package.get("overrides") if isinstance(package, dict) else None
    packages = lock.get("packages") if isinstance(lock, dict) else None
    if not isinstance(overrides, dict) or not isinstance(packages, dict):
        return []
    found = []
    for name, forced in overrides.items():
        pinned = _exact(forced)
        if pinned is None:
            continue
        for path, entry in packages.items():
            needs = entry.get("dependencies") if isinstance(entry, dict) else None
            declared = needs.get(name) if isinstance(needs, dict) else None
            wanted = _exact(declared)
            if wanted is not None and wanted > pinned:
                found.append(
                    f"{PACKAGE} overrides {name} to {forced}, older than the {declared} "
                    f"that {path} in {LOCK} declares; drop the override"
                )
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_wrangler_pin", description=__doc__.split("\n", 1)[0]
    )
    parser.add_argument("--version", default=os.environ.get("WRANGLER_VERSION", ""))
    parser.add_argument("root", nargs="?", default=".", type=Path, help="repository root")
    args = parser.parse_args(argv)
    if not args.version:
        print("WRANGLER_VERSION is not set", file=sys.stderr)
        return 1
    found = problems(args.root.resolve(), args.version)
    for item in found:
        print(f"::error::{item}", file=sys.stderr)
    if found:
        return 1
    print(f"wrangler {args.version} matches {PACKAGE} and {LOCK}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
