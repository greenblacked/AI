#!/usr/bin/env python3
"""Build a distributable ``.skill`` archive for every skill in the repository.

This exists as a CI job rather than a release step because it is the cheapest proof
that the repository is actually distributable: a skill that validates but cannot be
packaged is a skill nobody can install.

The archive contains a single top-level directory named after the skill, matching what
the Skills API expects on upload. ``evals/`` is excluded — it belongs beside a skill in
source control but not inside the artefact. ``LICENSE.txt`` and ``NOTICE.txt`` — copies
of this repository's own ``LICENSE`` and ``NOTICE`` — are added beside ``SKILL.md``, so
the MIT copyright notice travels with the skill once it is unzipped somewhere else.
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
# Archive member name -> file at the repository root it is a copy of. Named ".txt"
# because that is the per-skill licence file name the public skill repositories use,
# and it reads as plain text to someone who never sees this repository.
LICENSE_MEMBERS = {"LICENSE.txt": "LICENSE", "NOTICE.txt": "NOTICE"}


def _included(path: Path, skill: Path) -> bool:
    if path.is_symlink():
        # `is_file()` and `ZipFile.write` both follow links, so a symlink used to bake
        # whatever it pointed at - including content outside the repository - into the
        # artifact, while a symlinked *directory* contributed nothing at all. Neither
        # matches what the author sees in the tree.
        return False
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

    for part in skill.rglob("*"):
        if part.is_symlink():
            raise SystemExit(
                f"refusing to package {skill.name}: {part.relative_to(skill)} is a symlink. "
                "The archive would either inline what it points at or drop it silently, "
                "and neither matches the tree."
            )

    # A skill that already ships its own LICENSE.txt or NOTICE.txt has said something
    # deliberate there; silently replacing it with the repository's own copy would lose
    # that without anyone noticing until the archive was inspected.
    for member, source_name in LICENSE_MEMBERS.items():
        if (skill / member).exists():
            raise SystemExit(
                f"refusing to package {skill.name}: it already has a {member}, and "
                f"packaging would overwrite it with the repository's own {source_name}. "
                "Rename or remove the skill's own file."
            )

    # Checked before anything is written: a `ZipFile` opened in write mode truncates the
    # archive path immediately, so finding a missing LICENSE or NOTICE only once inside
    # the `with` block below left a valid-looking but incomplete `.skill` file in
    # `dist/` — every skill file present, the licence missing, and nothing about the
    # failed run visible from the archive itself.
    for source_name in LICENSE_MEMBERS.values():
        if not (repo_root / source_name).is_file():
            raise SystemExit(
                f"refusing to package {skill.name}: no {source_name} at the "
                f"repository root ({repo_root})"
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"{skill.name}.skill"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(skill.rglob("*")):
            if path.is_file() and _included(path, skill):
                bundle.write(path, path.relative_to(skill.parent))
        for member, source_name in LICENSE_MEMBERS.items():
            bundle.write(repo_root / source_name, f"{skill.name}/{member}")
    return archive


def main(repo_root: Path | None = None) -> int:
    repo_root = repo_root or Path(__file__).resolve().parent.parent
    output_dir = repo_root / "dist"
    skills = find_skills(repo_root)
    if not skills:
        print("no skills found", file=sys.stderr)
        return 2

    # A renamed or removed skill otherwise leaves its old archive behind, and CI
    # uploads it as though it were still shipped.
    for stale in output_dir.glob("*.skill"):
        stale.unlink()
    for skill in skills:
        archive = package(skill, output_dir, repo_root)
        size = archive.stat().st_size
        print(f"{archive.relative_to(repo_root)} ({size:,} bytes)")
    print(f"\npackaged {len(skills)} skill(s) into {output_dir.relative_to(repo_root)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
