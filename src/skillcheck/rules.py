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
# Keys Claude Code accepts in a SKILL.md that the upload route rejects with a hard
# error. This repository keeps the portable six on purpose, and `when_to_use` is the
# one a contributor here will reach for first, because it is exactly the trigger-phrase
# surface the descriptions are written to carry.
CLAUDE_CODE_ONLY_KEYS = frozenset(
    {
        "when_to_use",
        "argument-hint",
        "arguments",
        "disable-model-invocation",
        "user-invocable",
        "disallowed-tools",
        "model",
        "effort",
        "context",
        "agent",
        "background",
        "hooks",
        "paths",
        "shell",
    }
)

NEAR_MISSES = {
    "allowed_tools": "allowed-tools",
    "allowedtools": "allowed-tools",
    "tools": "allowed-tools",
    "title": "name",
    "desc": "description",
    "summary": "description",
}

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# The upload route rejects a name containing either vendor word, so a skill named for
# the tool it targets passes locally and fails at the boundary — the same class as the
# length caps below.
RESERVED_NAME_WORDS = ("anthropic", "claude")
NAME_MAX = 64
DESCRIPTION_MAX = 1024
COMPATIBILITY_MAX = 500

# How close to the description cap is close enough to be worth a warning. The cap is
# invisible until an edit crosses it, and crossing it makes the skill unloadable.
DESCRIPTION_HEADROOM = 50

SKILL_MD_MAX_LINES = 500
REFERENCE_MAX_LINES_WITHOUT_TOC = 100

# The lookbehind is what keeps this from matching inside a longer path. Without it,
# a URL such as https://example.com/assets/logo.png, or a mention of another
# project's `their-repo/references/x.md`, was reported as a dangling pointer into
# this skill's own bundle - a false positive that blocks legitimate prose.
BUNDLED_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])(?:\./)?(?:references|scripts|assets)/[A-Za-z0-9_./-]*[A-Za-z0-9_-]"
)
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


def find_plugins(repo_root: Path) -> list[Path]:
    """Return every plugin directory, sorted by name.

    A plugin is a directory under ``plugins/`` with its own ``.claude-plugin/plugin.json``.
    Each owns its ``skills/`` and ``agents/``, which is what stops a repository-root
    component being shipped once per installed plugin.
    """
    return sorted(
        path.parent.parent for path in (repo_root / "plugins").glob("*/.claude-plugin/plugin.json")
    )


def find_skills(root: Path) -> list[Path]:
    """Return every skill directory under ``root``, sorted by path.

    A skill directory is one that directly contains a ``SKILL.md``. ``template/`` is
    excluded: it is a starting point to copy, not a skill that ships.
    """
    return sorted(
        {
            path.parent
            for path in root.rglob("SKILL.md")
            if "template" not in path.relative_to(root).parts
        }
    )


def _line_of(text: str, needle: str) -> int:
    index = text.find(needle)
    if index < 0:
        return 1
    return text.count("\n", 0, index) + 1


def check_skill(
    directory: Path, repo_root: Path, known: frozenset[str] | None = None
) -> list[Finding]:
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

    try:
        text = skill_md.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        # One mis-encoded file used to abort validation for every other skill, which in
        # CI reads as "the validator is broken" rather than "this file is".
        add(ERROR, "not-utf8", f"file is not valid UTF-8: {error}")
        return findings

    try:
        front: Frontmatter = parse(text)
    except FrontmatterError as error:
        add(ERROR, "frontmatter", error.message, error.line)
        return findings

    findings.extend(_check_keys(front, add))
    findings.extend(_check_name(front, directory, add))
    findings.extend(_check_description(front, add))
    findings.extend(_check_compatibility(front, add))

    body_lines = text.split("\n")[front.end_line :]
    body = "\n".join(body_lines)
    findings.extend(_check_bundled_paths(body_lines, front.end_line + 1, directory, add))
    findings.extend(_check_scripts(directory, repo_root, add))
    findings.extend(_check_length(text, directory, repo_root, add))
    findings.extend(_check_tone(body, text, add))
    findings.extend(check_evals(directory, repo_root, known))

    return findings


def _check_keys(front: Frontmatter, add) -> list[Finding]:
    for key in sorted(front.values):
        if key in ALLOWED_KEYS:
            continue
        if key in CLAUDE_CODE_ONLY_KEYS:
            add(
                ERROR,
                "unknown-key",
                f"{key!r} is a Claude Code key that the Skills API upload route rejects "
                "with a hard error; this repository keeps the six portable keys so every "
                "skill packages and uploads"
                + (" — put trigger phrasings in 'description'" if key == "when_to_use" else ""),
                front.line_of(key),
            )
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
    for word in RESERVED_NAME_WORDS:
        if word in name:
            add(
                ERROR,
                "reserved-name",
                f"name {name!r} contains the reserved word {word!r}; the upload route "
                "rejects it, so name the skill after the job rather than the tool",
                line,
            )
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


FENCE_RE = re.compile(r"^(`{3,}|~{3,})")


def _mask_fenced_blocks(lines: list[str]) -> list[str]:
    """Blank out fenced code blocks, keeping the line count so line numbers survive.

    A path inside a fence is almost always an illustration — a directory tree showing
    how some other project is laid out, or a command run against the user's repository —
    not a pointer this skill expects the model to follow. Treating those as dangling
    pointers made it impossible to document a layout without failing the build, which is
    a poor trade for a check whose whole purpose is to catch pointers written in prose.

    Only *closed* fences are masked. An unterminated fence would otherwise swallow the
    rest of the file and silently switch the check off for everything after it, which is
    the failure mode this validator exists to prevent rather than to have. The closing
    fence must use the same character and be at least as long as the opening one, so a
    four-backtick block containing a three-backtick example stays a single block.
    """
    spans: list[tuple[int, int]] = []
    opened: tuple[int, str] | None = None
    for number, line in enumerate(lines):
        match = FENCE_RE.match(line.lstrip())
        if match is None:
            continue
        marker = match.group(1)
        if opened is None:
            opened = (number, marker)
            continue
        start_line, opening = opened
        if marker[0] == opening[0] and len(marker) >= len(opening):
            spans.append((start_line, number))
            opened = None

    masked = list(lines)
    for start_line, end_line in spans:
        for number in range(start_line, end_line + 1):
            masked[number] = ""
    return masked


def _check_bundled_paths(
    body_lines: list[str], first_line: int, directory: Path, add, label: str = "SKILL.md"
):
    """Every references/, scripts/ or assets/ path named in prose must exist.

    A dangling pointer is the worst kind of skill defect: nothing errors, the model
    simply never loads the depth the author thought it was loading. Commands are
    checked the same way, which is why the file named in the message is a parameter.
    """
    seen: set[str] = set()
    for offset, line in enumerate(_mask_fenced_blocks(body_lines)):
        for match in BUNDLED_PATH_RE.finditer(line):
            candidate = match.group(0).rstrip(".,;:")
            if candidate in seen:
                continue
            seen.add(candidate)
            tail = candidate.rsplit("/", 1)[-1]
            if "." not in tail:
                # A directory mentioned generically ("put helpers in scripts/") is
                # prose, not a pointer to a specific file.
                continue
            if not (directory / candidate).exists():
                add(
                    ERROR,
                    "dangling-reference",
                    f"{label} points at {candidate!r}, which does not exist",
                    first_line + offset,
                )
    return []


def _check_scripts(directory: Path, repo_root: Path, add) -> list[Finding]:
    for script in sorted((directory / "scripts").rglob("*.sh")):
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
    for reference in sorted((directory / "references").rglob("*.md")):
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
    """Cross-check the marketplace manifest against the plugins on disk.

    Each plugin now owns its own directory and discovers its own ``skills/`` and
    ``agents/``, so the manifest lists plugins rather than individual skills. What still
    has to hold is that every listed plugin is real, and that nothing on disk is stranded
    outside a plugin — a skill nobody ships is a skill nobody can install.
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

    def malformed(message: str) -> list[Finding]:
        return [Finding(ERROR, relative, 1, "bad-marketplace-shape", message)]

    if not isinstance(data, dict):
        return malformed(f"manifest must be a JSON object, found {type(data).__name__}")
    entries = data.get("plugins", [])
    if not isinstance(entries, list):
        return malformed(f"'plugins' must be a list, found {type(entries).__name__}")

    listed: set[Path] = set()
    for index, plugin in enumerate(entries):
        if not isinstance(plugin, dict):
            findings.extend(
                malformed(f"plugins[{index}] must be an object, found {type(plugin).__name__}")
            )
            continue
        label = plugin.get("name", f"plugins[{index}]")
        source = plugin.get("source")
        if not isinstance(source, str):
            findings.extend(malformed(f"{label!r} has no string 'source'"))
            continue
        directory = (repo_root / source).resolve()
        listed.add(directory)
        if not (directory / ".claude-plugin" / "plugin.json").is_file():
            findings.append(
                Finding(
                    ERROR,
                    relative,
                    1,
                    "missing-listed-plugin",
                    f"plugin {label!r} points at {source!r}, which has no "
                    ".claude-plugin/plugin.json",
                )
            )

    for plugin in find_plugins(repo_root):
        if plugin.resolve() not in listed:
            findings.append(
                Finding(
                    ERROR,
                    plugin.relative_to(repo_root) / ".claude-plugin" / "plugin.json",
                    1,
                    "unlisted-plugin",
                    "plugin is not listed in marketplace.json, so it installs for nobody",
                )
            )

    owned_skills = {d.resolve() for p in find_plugins(repo_root) for d in find_skills(p / "skills")}
    for directory in find_skills(repo_root):
        if directory.resolve() not in owned_skills:
            findings.append(
                Finding(
                    ERROR,
                    directory.relative_to(repo_root) / "SKILL.md",
                    1,
                    "unowned-skill",
                    "skill is not inside any plugin's skills/ directory, so no plugin ships it",
                )
            )

    owned_agents = {a.resolve() for p in find_plugins(repo_root) for a in find_agents(p / "agents")}
    for agent in find_agents(repo_root / "agents"):
        if agent.resolve() not in owned_agents:
            findings.append(
                Finding(
                    ERROR,
                    agent.relative_to(repo_root),
                    1,
                    "unowned-agent",
                    "subagent is not inside any plugin's agents/ directory",
                )
            )
    return findings


# Subagent frontmatter is a different contract from a skill's: `tools` is meaningful
# here and would be rejected in a SKILL.md, while `allowed-tools` is the reverse. They
# are validated separately for that reason rather than sharing one key set.
# What a plugin-shipped subagent may carry. Unlike a skill there is no upload route
# forcing this closed, so it is the documented set rather than a house restriction.
AGENT_ALLOWED_KEYS = frozenset(
    {
        "name",
        "description",
        "tools",
        "disallowedTools",
        "model",
        "effort",
        "maxTurns",
        "skills",
        "memory",
        "background",
        "isolation",
        "color",
        "initialPrompt",
    }
)
# Accepted in a project-level agent, refused in one a plugin ships — a plugin must not
# be able to register hooks, attach MCP servers or change the permission mode on
# whoever installs it.
AGENT_UNSUPPORTED_IN_PLUGINS = frozenset({"hooks", "mcpServers", "permissionMode"})


# A directory-level readme is documentation, not a subagent, and there is no
# frontmatter it could carry that would satisfy the contract below.
AGENT_NON_DEFINITIONS = frozenset({"README.md", "readme.md"})


def find_agents(root: Path) -> list[Path]:
    """Return every subagent definition under ``root``, sorted by path."""
    return sorted(p for p in root.glob("*.md") if p.name not in AGENT_NON_DEFINITIONS)


def check_agent(path: Path, repo_root: Path) -> list[Finding]:
    """Validate one subagent definition.

    Nothing else in the pipeline reads these files, so a misspelled key or a name that
    disagrees with the filename fails the same silent way a dangling skill reference
    does: delegation simply never happens, and no error is raised anywhere.
    """
    findings: list[Finding] = []
    relative = path.relative_to(repo_root)

    def add(level: str, code: str, message: str, line: int = 1) -> None:
        findings.append(Finding(level, relative, line, code, message))

    try:
        front = parse(path.read_text(encoding="utf-8"))
    except FrontmatterError as error:
        add(ERROR, "frontmatter", error.message, error.line)
        return findings

    for key in sorted(front.values):
        if key in AGENT_UNSUPPORTED_IN_PLUGINS:
            add(
                ERROR,
                "unknown-key",
                f"{key!r} is not supported in a plugin-shipped subagent: a plugin must "
                "not register hooks, attach MCP servers or set the permission mode for "
                "whoever installs it",
                front.line_of(key),
            )
            continue
        if key not in AGENT_ALLOWED_KEYS:
            add(
                ERROR,
                "unknown-key",
                f"unexpected subagent frontmatter key {key!r} — allowed keys are "
                + ", ".join(sorted(AGENT_ALLOWED_KEYS)),
                front.line_of(key),
            )

    name = (front.get("name") or "").strip()
    if not name:
        add(ERROR, "missing-name", "subagent frontmatter has no usable 'name'")
    else:
        if not NAME_RE.match(name) or len(name) > NAME_MAX:
            add(
                ERROR,
                "bad-name",
                f"name {name!r} must be lowercase letters, digits and single hyphens, "
                f"at most {NAME_MAX} characters",
                front.line_of("name"),
            )
        if name != path.stem:
            add(
                ERROR,
                "name-mismatch",
                f"name {name!r} must equal the filename {path.stem!r}",
                front.line_of("name"),
            )

    description = (front.get("description") or "").strip()
    line = front.line_of("description")
    if not description:
        add(ERROR, "missing-description", "subagent frontmatter has no usable 'description'")
    else:
        if "<" in description or ">" in description:
            add(ERROR, "angle-brackets", "description cannot contain '<' or '>'", line)
        if len(description) > DESCRIPTION_MAX:
            add(
                ERROR,
                "long-description",
                f"description is {len(description)} characters; the cap is {DESCRIPTION_MAX}",
                line,
            )

    tools = front.get("tools")
    if tools is not None:
        entries = [item.strip() for item in tools.split(",")]
        if not tools.strip() or any(not item for item in entries):
            add(
                ERROR,
                "bad-tools",
                "'tools' must be a non-empty comma-separated list with no blank entries",
                front.line_of("tools"),
            )
    return findings


# A trigger eval is the only way to find out whether a description actually fires,
# rather than assuming it does because it reads well. The schema is checked on every
# run because it is deterministic and free; the queries themselves are scored by a
# model, which is why that part is a manual workflow rather than a gate.
EVAL_MIN_QUERIES = 16
EVAL_MIN_PER_SIDE = 8


EVAL_ENTRY_KEYS = frozenset({"query", "should_trigger", "expected"})


def _check_eval_file(
    path: Path, subject: Path, own_name: str, repo_root: Path, known: frozenset[str] | None
) -> list[Finding]:
    """Validate one eval set, whoever it belongs to.

    `expected` is optional and only meaningful on a negative: it names the skill or
    subagent that should win that query instead. Without it a negative passes whenever
    anything other than the subject is chosen — including a completely wrong neighbour —
    and the theft between siblings that the negatives exist to catch is invisible.
    """
    findings: list[Finding] = []

    def add(level: str, code: str, message: str, target: Path) -> None:
        findings.append(Finding(level, target.relative_to(repo_root), 1, code, message))

    if not path.exists():
        add(
            WARNING,
            "no-evals",
            f"no eval set at {path.relative_to(repo_root)}, so nothing measures whether "
            "the description triggers",
            subject,
        )
        return findings

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        add(ERROR, "bad-eval-json", f"invalid JSON: {error.msg}", path)
        return findings

    if not isinstance(data, list):
        add(ERROR, "bad-eval-shape", "eval set must be a JSON array of query objects", path)
        return findings

    queries: list[str] = []
    positives = 0
    for index, entry in enumerate(data):
        where = f"entry {index}"
        if not isinstance(entry, dict):
            add(ERROR, "bad-eval-entry", f"{where} is not an object", path)
            continue
        query = entry.get("query")
        trigger = entry.get("should_trigger")
        extra = set(entry) - EVAL_ENTRY_KEYS
        if extra:
            add(
                ERROR,
                "bad-eval-entry",
                f"{where} has unexpected key(s): {', '.join(sorted(extra))}",
                path,
            )
        if not isinstance(query, str) or not query.strip():
            add(ERROR, "bad-eval-entry", f"{where} has no usable 'query'", path)
            continue
        if not isinstance(trigger, bool):
            add(
                ERROR,
                "bad-eval-entry",
                f"{where} 'should_trigger' must be true or false",
                path,
            )
            continue
        if "expected" in entry:
            expected = entry["expected"]
            if not isinstance(expected, str) or not expected.strip():
                add(ERROR, "bad-eval-entry", f"{where} 'expected' must be a name", path)
            elif trigger:
                add(
                    ERROR,
                    "bad-eval-entry",
                    f"{where} names an 'expected' winner but should_trigger is true; "
                    "the winner of a positive is the subject itself",
                    path,
                )
            elif expected == own_name:
                add(
                    ERROR,
                    "bad-eval-entry",
                    f"{where} expects {own_name!r} to win a negative, which contradicts "
                    "should_trigger: false",
                    path,
                )
            elif known is not None and expected not in known:
                add(
                    ERROR,
                    "unknown-expected",
                    f"{where} expects {expected!r}, which is not a skill or subagent in "
                    "this repository — a misspelling here scores as a permanent miss",
                    path,
                )
        queries.append(query.strip())
        positives += trigger

    duplicates = {q for q in queries if queries.count(q) > 1}
    for duplicate in sorted(duplicates):
        add(ERROR, "duplicate-eval-query", f"query appears more than once: {duplicate!r}", path)

    total = len(queries)
    negatives = total - positives
    if total < EVAL_MIN_QUERIES:
        add(
            ERROR,
            "thin-eval-set",
            f"{total} queries; at least {EVAL_MIN_QUERIES} are needed for the result to "
            "mean anything",
            path,
        )
    if total and (positives < EVAL_MIN_PER_SIDE or negatives < EVAL_MIN_PER_SIDE):
        add(
            ERROR,
            "unbalanced-eval-set",
            f"{positives} should-trigger and {negatives} should-not-trigger queries; at "
            f"least {EVAL_MIN_PER_SIDE} of each are needed, and the negatives are what "
            "catch a description that fires on everything",
            path,
        )
    return findings


def check_evals(
    directory: Path, repo_root: Path, known: frozenset[str] | None = None
) -> list[Finding]:
    """Validate a skill's trigger-eval set, if it has one."""
    return _check_eval_file(
        directory / "evals" / "trigger-eval.json",
        directory / "SKILL.md",
        directory.name,
        repo_root,
        known,
    )


def check_agent_evals(
    path: Path, repo_root: Path, known: frozenset[str] | None = None
) -> list[Finding]:
    """Validate a subagent's eval set at agents/evals/<name>.json, if it has one.

    A subagent's description does the same routing job a skill's does, and until this
    existed none of the nine here had anything measuring it.
    """
    return _check_eval_file(
        path.parent / "evals" / f"{path.stem}.json", path, path.stem, repo_root, known
    )


def check_duplicate_names(skills: list[Path], repo_root: Path) -> list[Finding]:
    """Two skill directories may not share a name.

    `name` must equal the directory name, so two directories sharing a name are two
    skills sharing a name: the second silently replaces the first when installing and
    when packaging, and every counter still reports success.
    """
    findings: list[Finding] = []
    seen: dict[str, Path] = {}
    for directory in skills:
        first = seen.get(directory.name)
        if first is None:
            seen[directory.name] = directory
            continue
        findings.append(
            Finding(
                ERROR,
                directory.relative_to(repo_root) / "SKILL.md",
                1,
                "duplicate-skill-name",
                f"another skill already uses the name {directory.name!r} "
                f"({first.relative_to(repo_root)}); one of them would silently replace "
                "the other on install and in dist/",
            )
        )
    return findings


# Slash commands are the third component a plugin can ship, and the one with the
# loosest contract upstream — which is exactly why it needs a local one. A command
# whose frontmatter key is misspelled still installs; it simply loses the behaviour
# the key was for, with no error anywhere. The name is taken from the filename, so
# unlike a skill there is no `name` key to disagree with it.
COMMAND_ALLOWED_KEYS = frozenset(
    {"description", "argument-hint", "allowed-tools", "model", "disable-model-invocation"}
)

COMMAND_NON_DEFINITIONS = frozenset({"README.md", "readme.md"})

# `$ARGUMENTS`, `$ARGUMENTS[N]`, and the `$N` shorthand. Indexing is zero-based —
# `$0` is the first argument — so the old `[1-9]` pattern missed the one placeholder a
# correctly written command is most likely to use. A command that reads an argument and
# does not advertise one is invisible: the picker shows no hint, so the caller types the
# bare name and the command runs against nothing.
COMMAND_ARGUMENT_RE = re.compile(r"\$(?:ARGUMENTS(?:\[\d+\])?\b|\d+(?!\w))")


def find_commands(root: Path) -> list[Path]:
    """Return every slash-command definition under ``root``, sorted by path."""
    if not root.is_dir():
        return []
    return sorted(p for p in root.rglob("*.md") if p.name not in COMMAND_NON_DEFINITIONS)


def check_command(path: Path, repo_root: Path) -> list[Finding]:
    """Validate one slash command."""
    findings: list[Finding] = []
    relative = path.relative_to(repo_root)

    def add(level: str, code: str, message: str, line: int = 1) -> None:
        findings.append(Finding(level, relative, line, code, message))

    text = path.read_text(encoding="utf-8")
    try:
        front = parse(text)
    except FrontmatterError as error:
        add(ERROR, "frontmatter", error.message, error.line)
        return findings

    for key in sorted(front.values):
        if key not in COMMAND_ALLOWED_KEYS:
            add(
                ERROR,
                "unknown-key",
                f"unexpected command frontmatter key {key!r} — allowed keys are "
                + ", ".join(sorted(COMMAND_ALLOWED_KEYS)),
                front.line_of(key),
            )

    # The filename is the invocation, so it has to be typeable and stable.
    if not NAME_RE.match(path.stem) or len(path.stem) > NAME_MAX:
        add(
            ERROR,
            "bad-command-name",
            f"filename {path.stem!r} becomes the slash command, so it must be lowercase "
            f"letters, digits and single hyphens, at most {NAME_MAX} characters",
        )

    description = (front.get("description") or "").strip()
    if not description:
        add(
            ERROR,
            "missing-description",
            "command frontmatter has no usable 'description', so the picker shows nothing",
        )
    else:
        line = front.line_of("description")
        if "<" in description or ">" in description:
            add(ERROR, "angle-brackets", "description cannot contain '<' or '>'", line)
        if len(description) > DESCRIPTION_MAX:
            add(
                ERROR,
                "long-description",
                f"description is {len(description)} characters; the cap is {DESCRIPTION_MAX}",
                line,
            )

    body_lines = text.split("\n")[front.end_line :]
    body = "\n".join(body_lines)
    if not body.strip():
        add(ERROR, "empty-command", "command has frontmatter but no prompt body")

    masked = "\n".join(_mask_fenced_blocks(body_lines))
    if COMMAND_ARGUMENT_RE.search(masked) and not (front.get("argument-hint") or "").strip():
        add(
            WARNING,
            "no-argument-hint",
            "command reads an argument but declares no 'argument-hint', so the caller "
            "is not told what to pass",
        )

    _check_bundled_paths(body_lines, front.end_line + 1, path.parent, add, label=path.name)
    for match in SHOUTING_RE.finditer(masked):
        add(
            WARNING,
            "shouting",
            f"{match.group(0)} in capitals — explaining why a rule matters travels "
            "further than shouting it",
            front.end_line + 1 + masked[: match.start()].count("\n"),
        )
    return findings


def check_eval_conflicts(
    skills: list[Path], repo_root: Path, agents: list[Path] = ()
) -> list[Finding]:
    """No query may be a positive for two skills or subagents at once.

    A query labelled ``should_trigger: true`` in two eval sets is a contradiction the
    harness can never satisfy: whichever skill wins the invocation, the other is scored
    as a miss, so one of the two is permanently and misleadingly below its threshold.

    The reverse — a positive for one skill and a negative for another — is not a
    conflict but the strongest test in the set, because it names the exact sibling the
    description has to beat. It is deliberately left alone.
    """
    findings: list[Finding] = []
    claimed: dict[str, tuple[str, Path]] = {}
    sets = [(d.name, d / "evals" / "trigger-eval.json") for d in skills]
    sets += [(a.stem, a.parent / "evals" / f"{a.stem}.json") for a in agents]
    for owner, path in sets:
        if not path.is_file():
            continue
        try:
            entries = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
            continue  # check_evals reports the malformed file; do not report it twice
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("should_trigger") is not True:
                continue
            query = entry.get("query")
            if not isinstance(query, str):
                continue
            key = " ".join(query.split()).casefold()
            first = claimed.get(key)
            if first is None:
                claimed[key] = (owner, path)
                continue
            if first[0] == owner:
                continue
            findings.append(
                Finding(
                    ERROR,
                    path.relative_to(repo_root),
                    1,
                    "conflicting-eval-query",
                    f"{query!r} is also a positive for {first[0]!r} "
                    f"({first[1].relative_to(repo_root)}); one of the two will always "
                    "score as a miss, so decide which skill owns the query and make it "
                    "a negative in the other",
                )
            )
    return findings
