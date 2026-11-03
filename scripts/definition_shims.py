#!/usr/bin/env python3
"""Wrap each subagent and command file as a one-file skill, for the two skill scanners.

Cisco's skill-scanner and NVIDIA's SkillSpector have no agent or command type: each reads
a directory whose `SKILL.md` carries the instructions. A definition is the same thing in
all but its location, so `security.yml` scans it through a shim,
`$OUT/<id>/SKILL.md`, which is a copy of the definition with its frontmatter name made the
id: an agent's `name:` line is replaced in place, and a command, which has none, gets
`name: <id>` inserted as the first line of its frontmatter. Cisco's strict load refuses a
`SKILL.md` without a name (and for a command falls back to a manifest that drops its
`allowed-tools`), and its policy matches a suppression against that name, so it must be
the globally unique id. Both scanners then run their prompt-injection, exfiltration
and obfuscation rules over the definition's instructions and frontmatter. They do not
analyse the tool grant itself, which is only text to them.

`$OUT/map.tsv` holds one `<id>\\t<source path>\\t<added lines>` line per shim. The SkillSpector job
appends those lines to its manifest, and `skill_scan_gate.py` maps a finding in a shim
back to the real file; the third column says how many lines the shim added above the
source's own (0 for an agent, 1 for a command, 4 for a README given a frontmatter block).

The id scheme is a contract, because the Cisco policy suppresses by id:

    agent--<plugin>--<stem>      plugins/<plugin>/agents/<stem>.md
    command--<plugin>--<stem>    plugins/<plugin>/commands/<stem>.md
    command--<plugin>--<folder>--<stem>
                                 plugins/<plugin>/commands/<folder>/<stem>.md
    agent--claude--<stem>        .claude/agents/<stem>.md
    command--claude--<stem>      .claude/commands/<stem>.md (folders as above)

`claude` stands for the repository's own `.claude/` directory, so no plugin may be called
that, and every part is lowercase letters and digits joined by single hyphens, which is
why a double hyphen can only be a separator.

Only `*.md` files count: directly inside `agents/`, and at any depth inside `commands/`,
which is how the validator finds them. A README.md in `commands/` is a command to Claude
Code, which loads every .md there, so it is wrapped even though the validator ignores it,
with its id from the lowercased stem; one without frontmatter is given `name` and
`description` lines so both scanners load it. A README.md in `agents/` is
skipped only while it does not open with frontmatter, which an agent needs to load; one that
does fails the run. `agents/evals/*.json` and `.claude/agents/benchmarks/**`
sit below `agents/` and are not definitions. A file in a covered place whose name breaks
the pattern, a symbolic link, a file that is not regular on disk, or an id used twice fails
the run: a definition that is skipped is a definition nobody scanned.

Standard library only, like the checks it sits beside.
"""

from __future__ import annotations

import argparse
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

PART = r"[a-z0-9]+(?:-[a-z0-9]+)*"
REPO_PREFIX = "claude"
# Where a definition can be at all, whatever it is called. A file matching this that fails
# DEFINITION_RE is refused rather than skipped.
# Agents are found one level deep, as the validator's `find_agents` does; commands at any
# depth, as `find_commands` does, because Claude Code namespaces a command by its folder.
LOCATION_RE = re.compile(
    r"(?:plugins/[^/]+|\.claude)/(?:agents/[^/]+|commands/(?:[^/]+/)*[^/]+)\.md"
)
OWNER = rf"(?:plugins/(?P<plugin>{PART})|(?P<repo>\.claude))"
AGENT_RE = re.compile(rf"{OWNER}/agents/(?P<stem>{PART})\.md")
# Claude Code loads every .md in a commands/ folder as a command, a README.md too, so the
# upper-case spelling is accepted there and the id uses the lowercased stem.
COMMAND_RE = re.compile(rf"{OWNER}/commands/(?P<dirs>(?:{PART}/)*)(?P<stem>{PART}|README)\.md")
# A readme in agents/ is documentation while it has no frontmatter, which list_definitions
# checks rather than assumes: one that opens with frontmatter is refused.
# The validator skips a commands/ readme too; the scan deliberately does not.
README_NAMES = frozenset({"README.md", "readme.md"})
AGENT_LOCATION_RE = re.compile(r"(?:plugins/[^/]+|\.claude)/agents/[^/]+\.md")
# A byte-order mark and blank space may precede the opening line and a loader still reads it.
OPENS_FRONTMATTER_RE = re.compile(rb"(?:\xef\xbb\xbf|\s)*---")
BASE_RE = re.compile(r"[0-9a-f]{40}")
# The mode `git ls-files -s` gives a symbolic link.
SYMLINK_MODE = "120000"


class DefinitionError(ValueError):
    """A definition the scan cannot read safely, or cannot read at all."""


def safe(text: str) -> str:
    """A path or name as one inert line: control characters escaped, quotes added."""
    return ascii(text)


def git(repo: Path, *args: str) -> bytes:
    try:
        done = subprocess.run(  # noqa: S603
            ["git", "-C", str(repo), *args],  # noqa: S607 - the runner's git, found on PATH
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as err:
        detail = getattr(err, "stderr", b"") or b""
        message = detail.decode("utf-8", "replace").strip().splitlines()[:1]
        raise DefinitionError(f"git {args[0]} failed: {safe(' '.join(message))}") from err
    return done.stdout


def plugin_names(repo: Path) -> set[str]:
    """Every directory name under `plugins/` that git tracks something in."""
    names = set()
    for raw in git(repo, "ls-files", "-z", "--", "plugins").split(b"\0"):
        parts = raw.decode("utf-8", "surrogateescape").split("/")
        if len(parts) > 2 and parts[0] == "plugins":
            names.add(parts[1])
    return names


def definition_id(path: str, plugins: set[str]) -> str:
    """The shim id for a repository-relative path, or DefinitionError if it is not one."""
    agent = AGENT_RE.fullmatch(path)
    command = None if agent else COMMAND_RE.fullmatch(path)
    match = agent or command
    if not match:
        raise DefinitionError(
            f"{safe(path)} is not a subagent or command file: expected "
            f"plugins/<plugin>/agents/<name>.md, .claude/agents/<name>.md, "
            f"plugins/<plugin>/commands/[<folder>/...]<name>.md or "
            f".claude/commands/[<folder>/...]<name>.md with lowercase hyphenated names"
        )
    if REPO_PREFIX in plugins:
        raise DefinitionError(
            f"a plugin is called {REPO_PREFIX!r}, which the ids of .claude/ definitions use "
            f"as their prefix, so the two could not be told apart"
        )
    owner = match["plugin"] or REPO_PREFIX
    if agent:
        return f"agent--{owner}--{match['stem']}"
    folders = match["dirs"].rstrip("/").split("/") if match["dirs"] else []
    return "--".join(["command", owner, *folders, match["stem"].lower()])


def assign_ids(paths: list[str], plugins: set[str]) -> dict[str, str]:
    """Map id -> path for every path; a repeated id fails rather than overwriting a shim."""
    ids: dict[str, str] = {}
    for path in paths:
        ident = definition_id(path, plugins)
        if ident in ids:
            raise DefinitionError(
                f"more than one definition has the id {ident}: {safe(ids[ident])} and {safe(path)}"
            )
        ids[ident] = path
    return ids


def tracked(repo: Path) -> dict[str, str]:
    """Every tracked path under `plugins/` and `.claude/` with its git mode."""
    listing = git(repo, "ls-files", "-s", "-z", "--", "plugins", ".claude")
    found = {}
    for record in listing.split(b"\0"):
        if not record:
            continue
        meta, _, raw = record.partition(b"\t")
        found[raw.decode("utf-8", "surrogateescape")] = meta.split()[0].decode("ascii")
    return found


def is_agents_readme(path: str) -> bool:
    return bool(AGENT_LOCATION_RE.fullmatch(path)) and path.rsplit("/", 1)[-1] in README_NAMES


def list_definitions(repo: Path) -> list[str]:
    """Every tracked subagent and command file, sorted. Raises on one that cannot be read."""
    modes = tracked(repo)
    located = sorted(path for path in modes if LOCATION_RE.fullmatch(path))
    paths = []
    for path in located:
        if modes[path] == SYMLINK_MODE:
            raise DefinitionError(f"{safe(path)} is a symbolic link; commit the file itself")
        if is_agents_readme(path):
            # Skipped only while it is plainly documentation: one that opens with
            # frontmatter could load as a subagent that neither the validator nor the
            # workflow's count would ever look at.
            if OPENS_FRONTMATTER_RE.match(read_regular(repo, path)):
                raise DefinitionError(
                    f"{safe(path)} opens with frontmatter, so it could load as a subagent; "
                    f"remove the frontmatter or rename the file to a plain agent name"
                )
            continue
        paths.append(path)
    assign_ids(paths, plugin_names(repo))
    return paths


def changed_definitions(repo: Path, base: str) -> list[str]:
    """The definitions a pull request touched: those in `base...HEAD` that still exist."""
    if not BASE_RE.fullmatch(base):
        raise DefinitionError("the base commit is not forty lowercase hex digits")
    merge_base = git(repo, "merge-base", base, "HEAD").decode("ascii").strip()
    diff = git(repo, "diff", "--no-renames", "-z", "--name-only", merge_base, "HEAD")
    changed = {raw.decode("utf-8", "surrogateescape") for raw in diff.split(b"\0") if raw}
    return [path for path in list_definitions(repo) if path in changed]


def shim_text(ident: str, path: str, data: bytes) -> bytes:
    """The shim's bytes: the source, with its frontmatter name made the shim id.

    Cisco's policy matches a suppression's `skills` against the frontmatter `name`, not
    the directory, so a shim has to carry its id there: an agent's own `name:` line is
    replaced in place (same line count), and a command, which has none, gets `name: <id>`
    inserted as the first frontmatter line. Everything else is copied byte for byte.
    """
    if (
        not data.startswith(b"---")
        and path.rsplit("/", 1)[-1] in README_NAMES
        and (ident.startswith("command--"))
    ):
        # A command readme is documentation and may have no frontmatter; both scanners
        # need one to load it, so it is given a minimal block. The gate subtracts the four
        # lines this adds, which build() records in map.tsv.
        return f"---\nname: {ident}\ndescription: {ident}\n---\n".encode("ascii") + data
    if not data.startswith(b"---\n"):
        raise DefinitionError(
            f"{safe(path)} does not open with a `---` frontmatter line (LF), so the name "
            f"line the scanner needs cannot be set"
        )
    end = data.find(b"\n---", 3)
    if end == -1:
        raise DefinitionError(f"{safe(path)} has no closing `---` frontmatter line")
    names = list(re.finditer(rb"(?m)^name[ \t]*:[^\n]*", data[:end]))
    line = f"name: {ident}".encode("ascii")
    if ident.startswith("command--"):
        if names:
            raise DefinitionError(
                f"{safe(path)} already sets `name`; the gate maps line numbers assuming the "
                f"shim adds exactly one line"
            )
        return b"---\n" + line + b"\n" + data[len(b"---\n") :]
    if len(names) != 1:
        raise DefinitionError(
            f"{safe(path)} has {len(names)} `name:` lines in its frontmatter; an agent "
            f"needs exactly one, which the shim replaces with its id"
        )
    match = names[0]
    # Only a CRLF opening line was refused above; a stray carriage return on this line goes.
    return data[: match.start()] + line + data[match.end() :]


def read_regular(repo: Path, path: str) -> bytes:
    target = repo / path
    try:
        mode = target.lstat().st_mode
    except OSError as err:
        raise DefinitionError(
            f"{safe(path)} is tracked but cannot be read: {err.strerror}"
        ) from err
    if not stat.S_ISREG(mode):
        raise DefinitionError(f"{safe(path)} is not a regular file")
    return target.read_bytes()


def build(repo: Path, out: Path, paths: list[str]) -> list[tuple[str, str]]:
    """Write every shim and map.tsv under `out`; return (id, path) pairs sorted by id.

    A map.tsv line is `<id>\\t<path>\\t<lines>`: how many lines the shim adds above the
    source's own, which is how the gate maps a finding back to the right source line.

    Everything is read and checked before anything is written, and `out` has to be new or
    empty, so a refused definition leaves no half-built directory and a shim from an
    earlier run is never scanned as though it were current.
    """
    ids = assign_ids(paths, plugin_names(repo))
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise DefinitionError(f"{safe(str(out))} exists and is not an empty directory")
    sources = {ident: read_regular(repo, path) for ident, path in ids.items()}
    contents = {ident: shim_text(ident, ids[ident], data) for ident, data in sources.items()}
    pairs = sorted(ids.items())
    out.mkdir(parents=True, exist_ok=True)
    try:
        for ident, data in contents.items():
            (out / ident).mkdir()
            (out / ident / "SKILL.md").write_bytes(data)
        added = {
            ident: data.count(b"\n") - sources[ident].count(b"\n")
            for ident, data in contents.items()
        }
        lines = "".join(f"{ident}\t{path}\t{added[ident]}\n" for ident, path in pairs)
        (out / "map.tsv").write_text(lines, encoding="utf-8")
    except OSError:
        shutil.rmtree(out, ignore_errors=True)
        raise
    return pairs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, default=Path("."), help="the checkout to read")
    parser.add_argument("--out", type=Path, required=True, help="a new or empty directory")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--all", action="store_true", help="every definition")
    mode.add_argument(
        "--changed",
        metavar="BASE",
        help="the definitions changed since the merge base with this commit",
    )
    args = parser.parse_args(argv)
    try:
        paths = (
            list_definitions(args.repo)
            if args.all
            else changed_definitions(args.repo, args.changed)
        )
        pairs = build(args.repo, args.out, paths)
    except DefinitionError as err:
        print(f"definition_shims: {err}", file=sys.stderr)
        return 1
    print(f"{len(pairs)} definition(s) wrapped as shims")
    return 0


if __name__ == "__main__":
    sys.exit(main())
