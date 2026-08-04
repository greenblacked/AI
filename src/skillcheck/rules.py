"""The rules CI enforces on every skill in this repository.

Where a rule exists because a downstream system rejects the skill, the limit is
copied from that system rather than invented here: the closed key set, the 64/1024/500
character caps and the angle-bracket ban all come from the Agent Skills specification
and the reference validator shipped with the ``skill-creator`` skill. Rules that go
beyond those exist because a skill can satisfy the spec and still be broken — a
``references/`` pointer to a file nobody wrote loads nothing and fails silently, which
is the defect that motivated this validator in the first place.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .frontmatter import Frontmatter, FrontmatterError, parse

ALLOWED_KEYS = frozenset(
    {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
)

# Keys people reach for that the runtime will silently ignore. Naming them beats a
# generic "unexpected key", because the author's intent is obvious and the fix is one
# character.
NEAR_MISSES = {
    "allowed_tools": "allowed-tools",
    "allowedtools": "allowed-tools",
    "tools": "allowed-tools",
    "title": "name",
    "desc": "description",
    "summary": "description",
}

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NAME_MAX = 64
DESCRIPTION_MAX = 1024
COMPATIBILITY_MAX = 500

# How close to the description cap is close enough to be worth a warning. The cap is
# invisible until an edit crosses it, and crossing it makes the skill unloadable.
DESCRIPTION_HEADROOM = 50

SKILL_MD_MAX_LINES = 500
REFERENCE_MAX_LINES_WITHOUT_TOC = 300

BUNDLED_PATH_RE = re.compile(r"(?:references|scripts|assets)/[A-Za-z0-9_./-]*[A-Za-z0-9_-]")
TRIGGER_RE = re.compile(r"\buse (?:this skill |it )?(?:when|whenever|for|any time)\b", re.I)
SHOUTING_RE = re.compile(r"(?<![A-Za-z])(?:ALWAYS|NEVER)(?![A-Za-z])")
TOC_RE = re.compile(r"^#{1,3}\s+(?:table of contents|contents|in this file)\b", re.I | re.M)

ERROR = "error"
WARNING = "warning"


@dataclass(frozen=True)
class Finding:
    """One thing CI has to say about one file."""

    level: str
    path: Path
    line: int
    code: str
    message: str

    @property
    def failed(self) -> bool:
        return self.level == ERROR


def find_skills(root: Path) -> list[Path]:
    """Return every skill directory under ``root``, sorted by path.

    A skill directory is one that directly contains a ``SKILL.md``.
    """
    return sorted({path.parent for path in root.rglob("SKILL.md")})


def _line_of(text: str, needle: str) -> int:
    index = text.find(needle)
    if index < 0:
        return 1
    return text.count("\n", 0, index) + 1


def check_skill(directory: Path, repo_root: Path) -> list[Finding]:
    """Run every rule against one skill directory."""
    skill_md = directory / "SKILL.md"
    findings: list[Finding] = []

    def add(level: str, code: str, message: str, line: int = 1, path: Path | None = None) -> None:
        findings.append(
            Finding(
                level=level,
                path=(path or skill_md).relative_to(repo_root),
                line=line,
                code=code,
                message=message,
            )
        )

    nested = [path for path in directory.rglob("SKILL.md") if path != skill_md]
    for extra in nested:
        add(
            ERROR,
            "nested-skill",
            "a skill directory must contain exactly one SKILL.md; the API rejects "
            f"nested ones on upload (found {extra.relative_to(repo_root)})",
        )

    text = skill_md.read_text(encoding="utf-8")

    try:
        front: Frontmatter = parse(text)
    except FrontmatterError as error:
        add(ERROR, "frontmatter", error.message, error.line)
        return findings

    findings.extend(_check_keys(front, add))
    findings.extend(_check_name(front, directory, add))
    findings.extend(_check_description(front, add))
    findings.extend(_check_compatibility(front, add))

    body = "\n".join(text.split("\n")[front.end_line :])
    findings.extend(_check_bundled_paths(body, directory, repo_root, text, add))
    findings.extend(_check_scripts(directory, repo_root, add))
    findings.extend(_check_length(text, directory, repo_root, add))
    findings.extend(_check_tone(body, text, add))

    return findings


def _check_keys(front: Frontmatter, add) -> list[Finding]:
    for key in sorted(front.values):
        if key in ALLOWED_KEYS:
            continue
        suggestion = NEAR_MISSES.get(key.lower().replace("-", "_"))
        hint = f"; did you mean {suggestion!r}?" if suggestion else ""
        add(
            ERROR,
            "unknown-key",
            f"unexpected frontmatter key {key!r}{hint} — allowed keys are "
            + ", ".join(sorted(ALLOWED_KEYS)),
            front.line_of(key),
        )
    return []


def _check_name(front: Frontmatter, directory: Path, add) -> list[Finding]:
    name = front.get("name")
    line = front.line_of("name")
    if name is None:
        add(ERROR, "missing-name", "frontmatter has no 'name'")
        return []
    name = name.strip()
    if not name:
        add(ERROR, "empty-name", "'name' is present but empty", line)
        return []
    if not NAME_RE.match(name):
        add(
            ERROR,
            "bad-name",
            f"name {name!r} must be lowercase letters, digits and single hyphens "
            "(no leading, trailing or doubled hyphen)",
            line,
        )
    if len(name) > NAME_MAX:
        add(ERROR, "long-name", f"name is {len(name)} characters; the cap is {NAME_MAX}", line)
    if name != directory.name:
        add(
            ERROR,
            "name-mismatch",
            f"name {name!r} must equal the directory name {directory.name!r} — the "
            "specification requires it and the packaged artifact is named after the "
            "directory",
            line,
        )
    return []


def _check_description(front: Frontmatter, add) -> list[Finding]:
    description = front.get("description")
    line = front.line_of("description")
    if description is None:
        add(ERROR, "missing-description", "frontmatter has no 'description'")
        return []
    description = description.strip()
    if not description:
        add(ERROR, "empty-description", "'description' is present but empty", line)
        return []
    if "<" in description or ">" in description:
        add(
            ERROR,
            "angle-brackets",
            "description cannot contain '<' or '>' — they are rejected on upload",
            line,
        )
    length = len(description)
    if length > DESCRIPTION_MAX:
        add(
            ERROR,
            "long-description",
            f"description is {length} characters; the cap is {DESCRIPTION_MAX}",
            line,
        )
    elif length > DESCRIPTION_MAX - DESCRIPTION_HEADROOM:
        add(
            WARNING,
            "description-headroom",
            f"description is {length} of {DESCRIPTION_MAX} characters — one edit from breaking",
            line,
        )
    if not TRIGGER_RE.search(description):
        add(
            WARNING,
            "no-trigger",
            "description has no explicit 'use when/whenever…' clause; the description "
            "is the only thing that decides whether the skill fires",
            line,
        )
    return []


def _check_compatibility(front: Frontmatter, add) -> list[Finding]:
    value = front.get("compatibility")
    if value and len(value.strip()) > COMPATIBILITY_MAX:
        add(
            ERROR,
            "long-compatibility",
            f"compatibility is {len(value.strip())} characters; the cap is {COMPATIBILITY_MAX}",
            front.line_of("compatibility"),
        )
    return []


def _check_bundled_paths(body: str, directory: Path, repo_root: Path, text: str, add):
    """Every references/, scripts/ or assets/ path named in prose must exist.

    A dangling pointer is the worst kind of skill defect: nothing errors, the model
    simply never loads the depth the author thought it was loading.
    """
    seen: set[str] = set()
    for match in BUNDLED_PATH_RE.finditer(body):
        candidate = match.group(0).rstrip(".,;:")
        if candidate in seen:
            continue
        seen.add(candidate)
        tail = candidate.rsplit("/", 1)[-1]
        if "." not in tail:
            # A directory mentioned generically ("put helpers in scripts/") is prose,
            # not a pointer to a specific file.
            continue
        if not (directory / candidate).exists():
            add(
                ERROR,
                "dangling-reference",
                f"SKILL.md points at {candidate!r}, which does not exist",
                _line_of(text, candidate),
            )
    return []


def _check_scripts(directory: Path, repo_root: Path, add) -> list[Finding]:
    for script in sorted((directory / "scripts").glob("*.sh")):
        first = script.read_text(encoding="utf-8").split("\n", 1)[0]
        if not first.startswith("#!"):
            add(ERROR, "no-shebang", "shell script has no shebang line", 1, script)
        if not script.stat().st_mode & 0o111:
            add(ERROR, "not-executable", "shell script is not executable", 1, script)
    return []


def _check_length(text: str, directory: Path, repo_root: Path, add) -> list[Finding]:
    lines = len(text.split("\n"))
    if lines > SKILL_MD_MAX_LINES:
        add(
            WARNING,
            "long-skill",
            f"SKILL.md is {lines} lines; past ~{SKILL_MD_MAX_LINES} the body should "
            "push depth into references/ instead",
        )
    for reference in sorted((directory / "references").glob("*.md")):
        content = reference.read_text(encoding="utf-8")
        count = len(content.split("\n"))
        if count > REFERENCE_MAX_LINES_WITHOUT_TOC and not TOC_RE.search(content):
            add(
                WARNING,
                "no-toc",
                f"reference is {count} lines and has no table of contents",
                1,
                reference,
            )
    return []


def _check_tone(body: str, text: str, add) -> list[Finding]:
    for match in SHOUTING_RE.finditer(body):
        add(
            WARNING,
            "shouting",
            f"{match.group(0)} in capitals — explaining why a rule matters travels "
            "further than shouting it",
            _line_of(text, match.group(0)),
        )
        break
    return []


def check_marketplace(repo_root: Path) -> list[Finding]:
    """Cross-check the marketplace manifest against the skills on disk.

    A skill that exists but is not listed ships to nobody; a listing that points at a
    missing directory breaks installation for everybody.
    """
    manifest = repo_root / ".claude-plugin" / "marketplace.json"
    relative = Path(".claude-plugin/marketplace.json")
    if not manifest.exists():
        return [Finding(ERROR, relative, 1, "no-marketplace", "marketplace manifest is missing")]

    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [Finding(ERROR, relative, error.lineno, "bad-json", f"invalid JSON: {error.msg}")]

    findings: list[Finding] = []
    listed: set[Path] = set()
    for plugin in data.get("plugins", []):
        for entry in plugin.get("skills", []):
            path = (repo_root / entry).resolve()
            if not (path / "SKILL.md").exists():
                findings.append(
                    Finding(
                        ERROR,
                        relative,
                        1,
                        "missing-listed-skill",
                        f"plugin {plugin.get('name', '?')!r} lists {entry!r}, which has "
                        "no SKILL.md",
                    )
                )
            listed.add(path)

    for directory in find_skills(repo_root / "skills"):
        if directory.resolve() not in listed:
            findings.append(
                Finding(
                    ERROR,
                    directory.relative_to(repo_root) / "SKILL.md",
                    1,
                    "unlisted-skill",
                    "skill is not listed in any plugin in marketplace.json, so it "
                    "installs for nobody",
                )
            )
    return findings
