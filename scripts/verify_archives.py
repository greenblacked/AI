#!/usr/bin/env python3
"""Verify every `.skill` archive in `dist/` actually holds a loadable skill.

Building an archive without error only proves a zip was written. What the Skills API
upload route needs is a `SKILL.md` at the archive root whose `name` matches the archive
file name, and a broken layout would ship green here and fail at install, for someone
else, later.

`ci.yml`'s `package` job runs `package_skills.py` and then this, on every push and pull
request. `release.yml` runs the same two scripts again before attaching the archives to
a GitHub Release, so the two paths that ship an archive share one check rather than two
that can drift against each other.

Standard library only, like the packager it verifies.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from skillcheck.frontmatter import parse  # noqa: E402

DIST = Path("dist")


def verify(root: Path) -> int:
    archives = sorted((root / DIST).glob("*.skill"))
    if not archives:
        print(f"::error::no archives in {DIST}")
        return 1

    for archive in archives:
        stem = archive.stem
        with zipfile.ZipFile(archive) as bundle:
            bad = bundle.testzip()
            if bad is not None:
                print(f"::error file={archive}::corrupt member {bad}")
                return 1
            member = f"{stem}/SKILL.md"
            if member not in bundle.namelist():
                print(f"::error file={archive}::no {member} in the archive")
                return 1
            values = parse(bundle.read(member).decode("utf-8")).values
        if values.get("name") != stem:
            print(f"::error file={archive}::declares name {values.get('name')!r}")
            return 1

    print(f"{len(archives)} archive(s) verified")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="verify_archives", description=__doc__.split("\n", 1)[0])
    parser.add_argument("root", nargs="?", default=".", type=Path, help="repository root")
    args = parser.parse_args(argv)
    return verify(args.root.resolve())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
