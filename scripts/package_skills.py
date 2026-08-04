#!/usr/bin/env python3
"""Build a distributable ``.skill`` archive for every skill in the repository.

This exists as a CI job rather than a release step because it is the cheapest proof
that the repository is actually distributable: a skill that validates but cannot be
packaged is a skill nobody can install.

The archive contains a single top-level directory named after the skill, matching what
the Skills API expects on upload. ``evals/`` is excluded — it belongs beside a skill in
source control but not inside the artefact.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from skillcheck.rules import check_skill, find_skills  # noqa: E402

EXCLUDED_DIRS = {"__pycache__", "node_modules", ".git"}
ROOT_EXCLUDED_DIRS = {"evals"}
EXCLUDED_NAMES = {".DS_Store"}


def _included(path: Path, skill: Path) -> bool:
    relative = path.relative_to(skill)
    if path.name in EXCLUDED_NAMES or path.suffix == ".pyc":
        return False
    if EXCLUDED_DIRS & set(relative.parts):
        return False
    return not (relative.parts and relative.parts[0] in ROOT_EXCLUDED_DIRS)


def package(skill: Path, output_dir: Path, repo_root: Path) -> Path:
    findings = [item for item in check_skill(skill, repo_root) if item.failed]
    if findings:
        raise SystemExit(
            f"refusing to package {skill.name}: it does not validate\n"
            + "\n".join(f"  {f.path}:{f.line} [{f.code}] {f.message}" for f in findings)
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"{skill.name}.skill"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(skill.rglob("*")):
            if path.is_file() and _included(path, skill):
                bundle.write(path, path.relative_to(skill.parent))
    return archive


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    output_dir = repo_root / "dist"
    skills = find_skills(repo_root / "skills")
    if not skills:
        print("no skills found", file=sys.stderr)
        return 2
    for skill in skills:
        archive = package(skill, output_dir, repo_root)
        size = archive.stat().st_size
        print(f"{archive.relative_to(repo_root)} ({size:,} bytes)")
    print(f"\npackaged {len(skills)} skill(s) into {output_dir.relative_to(repo_root)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
