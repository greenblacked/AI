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

Every `*.md` counts, in any case and at any depth below `agents/` or `commands/`, because
Claude Code's loader reads them all: it walks `agents/` recursively, names a nested agent
after its folders, takes any name ending in `.md` whatever its case, and loads a file with
no frontmatter too. The validator looks only one level deep in `agents/`, so it is not the
authority here. Only a depth-one, lowercase `agents/<stem>.md` is a definition the scan can
name, and any other .md below `agents/` fails the run, a README included (its first line
does not matter). A README.md in `commands/` is a command, so it is wrapped even though the
validator ignores it, with its id from the lowercased stem; one without frontmatter is
given `name` and `description` lines so both scanners load it. `agents/evals/*.json` and
`.claude/agents/benchmarks/**` hold no .md, so they are not definitions. A file in a covered
place whose name breaks the pattern, a symbolic link or a submodule (mode 160000)
anywhere in the repository, a file that is not regular on disk, or an id used twice
fails the run: a definition that is skipped is a definition nobody scanned.

The scan can only see the default folders, so the run also fails on a manifest that points
Claude Code anywhere else (`check_manifests`): `agents`, `commands`, `skills` or `hooks` in a
plugin manifest or marketplace entry, or a `source` that is not `./plugins/<plugin>`.

Standard library only, like the checks it sits beside.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from skillcheck.frontmatter import FrontmatterError, parse  # noqa: E402

PART = r"[a-z0-9]+(?:-[a-z0-9]+)*"
REPO_PREFIX = "claude"
# Where a definition can be at all, whatever it is called. A file matching this that fails
# DEFINITION_RE is refused rather than skipped.
# Both kinds are matched at any depth and with `.md` in any case, because Claude Code's
# loader is wider than the validator's `find_agents`: it walks `agents/` recursively (a
# folder becomes part of the agent's name) and takes any file whose lowercased name ends in
# `.md`, with or without frontmatter. A path this matches that is not a depth-one lowercase
# `<stem>.md` is refused rather than skipped.
LOCATION_RE = re.compile(r"(?:plugins/[^/]+|\.claude)/(?:agents|commands)/(?:.*/)?[^/]*(?i:\.md)")
OWNER = rf"(?:plugins/(?P<plugin>{PART})|(?P<repo>\.claude))"
AGENT_RE = re.compile(rf"{OWNER}/agents/(?P<stem>{PART})\.md")
# Claude Code loads every .md in a commands/ folder as a command, a README.md too, so the
# upper-case spelling is accepted there and the id uses the lowercased stem.
COMMAND_RE = re.compile(rf"{OWNER}/commands/(?P<dirs>(?:{PART}/)*)(?P<stem>{PART}|README)\.md")
# The validator skips a commands/ readme; the scan deliberately does not. An agents/ readme
# is no exception: the loader takes it as a subagent whatever it opens with.
README_NAMES = frozenset({"README.md", "readme.md"})
BASE_RE = re.compile(r"[0-9a-f]{40}")
# The mode `git ls-files -s` gives a symbolic link.
SYMLINK_MODE = "120000"
# A submodule entry: a commit, not a file, so there is nothing here to wrap or scan.
GITLINK_MODE = "160000"


class DefinitionError(ValueError):
    """A definition the scan cannot read safely, or cannot read at all."""


def safe(text: str) -> str:
    """A path or name as one inert line: control characters escaped, quotes added."""
    # `##[` is the legacy workflow-command marker the runner honours anywhere in a line, and
    # ascii() leaves it intact, so it is broken the way skill_scan_gate.py's inert() does.
    return ascii(text).replace("##[", "## [")


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
    if agent and match["stem"] == "readme":
        raise DefinitionError(
            f"{safe(path)} is a readme in an agents/ folder, which Claude Code loads as a "
            f"subagent whatever it contains; move the documentation out of agents/"
        )
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
    """Every tracked path in the repository with its git mode."""
    listing = git(repo, "ls-files", "-s", "-z")
    found = {}
    for record in listing.split(b"\0"):
        if not record:
            continue
        meta, _, raw = record.partition(b"\t")
        found[raw.decode("utf-8", "surrogateescape")] = meta.split()[0].decode("ascii")
    return found


# Keys with which a manifest points Claude Code at components outside the default places.
# Claude Code loads them for the plugin (and, on a marketplace entry, appends them to it), so
# a file they name is a definition this script would never enumerate.
COMPONENT_KEYS = ("agents", "commands", "skills", "hooks")
MARKETPLACE = ".claude-plugin/marketplace.json"
SOURCE_RE = re.compile(rf"\./plugins/{PART}")
PLUGIN_MANIFEST_RE = re.compile(rf"plugins/{PART}/\.claude-plugin/plugin\.json")


def load_manifest(repo: Path, path: str) -> dict:
    try:
        data = json.loads(read_regular(repo, path).decode("utf-8"))
    except (ValueError, DefinitionError) as err:
        raise DefinitionError(f"{safe(path)} cannot be read as a JSON manifest: {err}") from err
    if not isinstance(data, dict):
        raise DefinitionError(f"{safe(path)} is not a JSON object")
    return data


def check_manifests(repo: Path) -> None:
    """Refuse every manifest shape that could load a definition the scan does not wrap.

    The four default places are not the only ones Claude Code reads: `agents`, `commands`,
    `skills` and `hooks` in a plugin manifest or a marketplace entry add paths (or inline
    content), and a marketplace `source` can name any directory. Rather than widen the
    globs to follow them, the run fails on a manifest that uses either, so the default
    layout is the only layout there is to scan.
    """
    listing = git(repo, "ls-files", "-z", "--", ":(glob)**/.claude-plugin/**")
    for raw in listing.split(b"\0"):
        path = raw.decode("utf-8", "surrogateescape")
        if path and path != MARKETPLACE and not PLUGIN_MANIFEST_RE.fullmatch(path):
            raise DefinitionError(
                f"{safe(path)} is a manifest in a place the scan does not follow: only "
                f"{MARKETPLACE} and plugins/<plugin>/.claude-plugin/plugin.json are read"
            )
        if path and PLUGIN_MANIFEST_RE.fullmatch(path):
            plugin = load_manifest(repo, path)
            for key in COMPONENT_KEYS:
                if key in plugin:
                    raise DefinitionError(
                        f"{safe(path)} sets `{key}`, which loads components from paths the "
                        f"scan does not enumerate; use the default folders"
                    )
    if not any(
        raw.decode("utf-8", "surrogateescape") == MARKETPLACE for raw in listing.split(b"\0")
    ):
        return
    entries = load_manifest(repo, MARKETPLACE).get("plugins", [])
    if not isinstance(entries, list):
        raise DefinitionError(f"{MARKETPLACE} 'plugins' is not a list")
    for entry in entries:
        if not isinstance(entry, dict):
            raise DefinitionError(f"{MARKETPLACE} has a plugin entry that is not an object")
        source = entry.get("source")
        if not isinstance(source, str) or not SOURCE_RE.fullmatch(source):
            raise DefinitionError(
                f"{MARKETPLACE} entry has source {safe(str(source))}; the scan only reads "
                f"plugins listed as ./plugins/<plugin>"
            )
        for key in COMPONENT_KEYS:
            if key in entry:
                raise DefinitionError(
                    f"{MARKETPLACE} entry sets `{key}`, which loads components from paths "
                    f"the scan does not enumerate; use the default folders"
                )


def list_definitions(repo: Path) -> list[str]:
    """Every tracked subagent and command file, sorted. Raises on one that cannot be read."""
    modes = tracked(repo)
    # Checked over the whole tree and before the manifests are read: a link or submodule
    # standing in for a directory (`.claude-plugin`, an `agents/` subfolder) hides what it
    # points at from every later check, which would then pass on an empty listing.
    for path in sorted(modes):
        if modes[path] == GITLINK_MODE:
            raise DefinitionError(
                f"{safe(path)} is a submodule (gitlink); the scan cannot read what it points at"
            )
        if modes[path] == SYMLINK_MODE:
            raise DefinitionError(f"{safe(path)} is a symbolic link; commit the file itself")
    check_manifests(repo)
    paths = sorted(path for path in modes if LOCATION_RE.fullmatch(path))
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
    shim = wrap_text(ident, path, data)
    confirm_name(ident, path, shim)
    return shim


# Characters YAML treats as line breaks (or that no loader should see in a header) but that
# the repository's parser does not split on. Tab and LF are the ordinary whitespace.
CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x85\u2028\u2029]")


def confirm_name(ident: str, path: str, shim: bytes) -> None:
    """Refuse a shim whose loaded `name` is not its id.

    The rewrite above only sees a plain `name:` line. YAML has other spellings of the
    key (a complex `? name` key, a quoted key) that a loader reads after it and lets win,
    which would let a pull request borrow another shim's Cisco suppression. So the
    result is read back with the repository's own parser, and a quoted or complex key at
    the start of a line is refused outright because that parser may not model them.
    """
    text = shim.decode("utf-8", "replace")
    block = text.split("\n---", 1)[0]
    if CONTROL_RE.search(block):
        raise DefinitionError(
            f"{safe(path)} has a line separator or control character in its frontmatter, "
            f"which YAML reads as a line break the repository's parser does not"
        )
    if re.search(r"(?m)^[?'\"!&*{\[]", block):
        raise DefinitionError(
            f"{safe(path)} has a frontmatter key written as a complex, quoted or "
            f"indicator-led key, "
            f"which could set `name` to something other than its shim id"
        )
    try:
        name = parse(text).get("name")
    except FrontmatterError as err:
        raise DefinitionError(f"{safe(path)} frontmatter does not parse: {err.message}") from err
    if name != ident:
        raise DefinitionError(f"{safe(path)} would load with a `name` other than its shim id")


def wrap_text(ident: str, path: str, data: bytes) -> bytes:
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
        # The one egress for error text: a FrontmatterError message quotes a frontmatter line
        # with repr(), which leaves `##[` intact, so it is broken here as safe() does for paths.
        print(f"definition_shims: {err}".replace("##[", "## ["), file=sys.stderr)
        return 1
    print(f"{len(pairs)} definition(s) wrapped as shims")
    return 0


if __name__ == "__main__":
    sys.exit(main())
