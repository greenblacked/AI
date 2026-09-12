#!/usr/bin/env python3
"""Export every skill as a self-contained Markdown file any assistant can read.

The skills in this repository are plain procedures. Nothing in them is specific to one
vendor — two files mention Claude at all, and both do it because the fact is about Claude
— but the *packaging* is: a `SKILL.md` with YAML frontmatter, sitting in a plugin with a
manifest, discovered by a marketplace. ChatGPT, Grok and the rest have no marketplace to
read, so the work does not travel, and pasting a `SKILL.md` into one of them hands the
reader frontmatter it cannot use and `references/` pointers it cannot open.

This flattens each skill into one file that stands alone:

- the frontmatter becomes a plain "Use this when" line, which is the only part of it a
  model without a skills runtime can act on
- every `references/*.md` is inlined as a section with its headings demoted to nest, and
  every pointer naming one is rewritten to name that section instead of a path — in the
  reference text as well as in the body, because a reference sending you to a sibling
  reference is as much a dangling pointer for a reader with no filesystem
- `assets/` and `scripts/` are inlined fenced, because a template or a script is a thing
  to copy rather than to read, and a script named in prose is a path a flattened copy
  cannot otherwise provide
- a path inside a fenced block is left exactly as written. It is part of a command, and
  the command needs it; the inlined section is what tells the reader which file to create

Output lands in `dist/portable/`: one file per skill, one per plugin, and an index that
lists every description so a model can choose between them the way a skills runtime
would. CI builds it on every run and uploads the result, so the files exist for someone
with no toolchain; `--check` verifies without writing, for when you only want the gate.

Standard library only, like the validator it imports.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from skillcheck.frontmatter import FrontmatterError, parse  # noqa: E402
from skillcheck.rules import find_plugins, find_skills  # noqa: E402

# Everything a skill can ship and name in prose. `scripts/` is here because a skill
# that hands an agent a script to run is handing it a path, and a path is the one thing
# a flattened copy cannot provide — `git bisect run ./scripts/bisect-probe.sh` reaches a
# reader with no such file.
BUNDLED_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])(?:\./)?"
    r"((?:references|assets)/[A-Za-z0-9_.-]+\.md|scripts/[A-Za-z0-9_.-]+\.[A-Za-z0-9]+)"
)
# How to fence a shipped script, by extension. Anything unlisted is fenced without a
# language rather than guessed at.
SCRIPT_LANGUAGES = {".sh": "bash", ".bash": "bash", ".py": "python", ".js": "javascript"}
# Any fence opener, with its full run of markers: the closing fence has to use the same
# character and be at least as long, or a four-backtick block quoting a three-backtick
# example closes early and everything after it is read as prose.
FENCE_RE = re.compile(r"^(`{3,}|~{3,})")
ATX_RE = re.compile(r"^(#{1,6})(\s+)")


def demote(text: str, levels: int) -> str:
    """Push every heading down ``levels``, leaving fenced code alone.

    A `#` at the start of a line inside a shell block is a comment, not a heading, and
    rewriting it would corrupt a command the reader is meant to run.
    """
    out: list[str] = []
    opening: str | None = None
    for line in text.split("\n"):
        fence = FENCE_RE.match(line.lstrip())
        if fence is not None:
            marker = fence.group(1)
            if opening is None:
                opening = marker
            elif marker[0] == opening[0] and len(marker) >= len(opening):
                opening = None
            out.append(line)
            continue
        match = None if opening is not None else ATX_RE.match(line)
        if match is None:
            out.append(line)
            continue
        hashes = "#" * min(6, len(match.group(1)) + levels)
        out.append(hashes + match.group(2) + line[match.end() :])
    return "\n".join(out)


def title_of(text: str, fallback: str) -> str:
    """A bundled file's own H1, or a title made from its filename."""
    for line in text.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return fallback.replace("-", " ").capitalize()


def strip_frontmatter(text: str) -> str:
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return text.strip()
    for index in range(1, len(lines)):
        if lines[index].strip() in {"---", "..."}:
            return "\n".join(lines[index + 1 :]).strip()
    return text.strip()


def fence_spans(text: str) -> list[bool]:
    """One flag per line: True when the line is inside a fenced code block.

    A path inside a fence is part of a command or a worked example. Rewriting it to
    "the … section below" turns a runnable line into prose — `git bisect run` needs a
    path, and the inlined section is what tells the reader which file to create.
    """
    flags: list[bool] = []
    opening: str | None = None
    for line in text.split("\n"):
        fence = FENCE_RE.match(line.lstrip())
        if fence is not None:
            marker = fence.group(1)
            if opening is None:
                opening = marker
                flags.append(True)
                continue
            if marker[0] == opening[0] and len(marker) >= len(opening):
                opening = None
            flags.append(True)
            continue
        flags.append(opening is not None)
    return flags


def language_of(relative: str) -> str:
    """The fence language for a shipped script, or none when the extension is unknown."""
    return SCRIPT_LANGUAGES.get(Path(relative).suffix, "")


def drop_title(text: str) -> str:
    """A reference file's own H1, removed: the section heading already carries it, and
    keeping both renders as a title followed immediately by the same title again."""
    stripped = strip_frontmatter(text)
    if stripped.startswith("# "):
        return stripped.split("\n", 1)[1].lstrip("\n") if "\n" in stripped else ""
    return stripped


def render_skill(directory: Path) -> tuple[str, str, str, list[str]]:
    """Return (name, description, the self-contained document, unresolved pointers).

    Everything the skill ships is inlined — references as prose with their headings
    demoted to nest, assets and scripts fenced, because a template or a script is a
    thing to copy rather than to read. Pointers are then rewritten to name the section
    instead of the path, in the reference text as well as in the body: a reference file
    that sends you to a sibling reference is as much a dangling pointer, for a reader
    with no filesystem, as one in the body.

    "Unresolved" counts only paths the skill's own body names and this export could not
    inline. Reference files quote paths from the reader's own project —
    `assets/LICENSES.md` in a game they are building — and those are worked examples.
    Failing on them would be a gate that cries wolf, so they are left exactly as written.
    """
    source = (directory / "SKILL.md").read_text(encoding="utf-8")
    values = parse(source).values
    name = values.get("name", directory.name)
    description = " ".join((values.get("description") or "").split())
    body = strip_frontmatter(source)

    # The skill's own H1 becomes the document title, so it is not repeated inside. Two
    # H1s in one file make the bundle read as two documents and break any tool that
    # splits on heading level.
    heading = title_of(body, name)
    if body.startswith("# "):
        body = body.split("\n", 1)[1].lstrip("\n") if "\n" in body else ""

    # Inline in the order the skill first names them, so a reader meets each section
    # where the prose sent them rather than in alphabetical order.
    order: list[str] = []
    named: list[str] = []
    for line, fenced in zip(body.split("\n"), fence_spans(body), strict=True):
        if fenced:
            continue
        for match in BUNDLED_RE.finditer(line):
            if match.group(1) not in order:
                order.append(match.group(1))
                named.append(match.group(1))
    for pattern in ("references/*.md", "assets/*.md", "scripts/*"):
        for path in sorted(directory.glob(pattern)):
            if path.is_file():
                relative = path.relative_to(directory).as_posix()
                if relative not in order:
                    order.append(relative)

    sources: dict[str, str] = {}
    titles: dict[str, str] = {}
    for relative in order:
        path = directory / relative
        if not path.is_file():
            continue  # the validator owns dangling pointers; do not report them twice
        try:
            sources[relative] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue  # a binary asset cannot be inlined as text; leave the pointer be
        titles[relative] = title_of(sources[relative], Path(relative).stem)

    def rewrite(text: str) -> str:
        def one(match: re.Match[str]) -> str:
            title = titles.get(match.group(1))
            return f'the "{title}" section below' if title else match.group(1)

        out = []
        for line, fenced in zip(text.split("\n"), fence_spans(text), strict=True):
            if fenced:
                out.append(line)
                continue
            line = BUNDLED_RE.sub(one, line)
            # A pointer inside backticks reads as a path even after rewriting.
            out.append(re.sub(r'`the "([^"]+)" section below`', r'the "\1" section below', line))
        return "\n".join(out)

    sections: list[str] = []
    for relative in order:
        if relative not in sources:
            continue
        title, text = titles[relative], sources[relative]
        if relative.startswith("references/"):
            sections.append(f"### {title}\n\n{demote(drop_title(text), 3).strip()}")
        else:
            language = "markdown" if relative.startswith("assets/") else language_of(relative)
            sections.append(f"### {title}\n\n```{language}\n{text.rstrip()}\n```")
    sections = [rewrite(section) for section in sections]

    body = rewrite(body)
    unresolved = [relative for relative in named if relative not in titles]

    parts = [
        f"# {heading}",
        "",
        f"**Skill:** `{name}`",
        "",
        f"**Use this when:** {description}",
        "",
        body.strip(),
    ]
    if sections:
        parts += ["", "## Reference material", "", *(s + "\n" for s in sections)]
    return name, description, "\n".join(parts).rstrip() + "\n", unresolved


HOW_TO_USE = """# Portable skills

Every skill in this library, flattened into files that stand alone. No frontmatter to
interpret, no plugin manifest, no `references/` path to follow — each file carries its
own reference material inline, so it works wherever you can paste or upload text.

`index.md` is the router: it lists every skill with the description that decides when the
skill applies. A model given the index knows what is available; give it the individual
file when the situation matches.

## ChatGPT

**A Project** is the closest fit. Create one, upload the `plugins/*.md` bundles you want
as project files, and put this in the project instructions:

> You have a library of procedures in the project files. Before answering, check whether
> one applies — each begins with "Use this when". If one does, follow it rather than
> improvising, and say which you used. If none applies, answer normally.

**A Custom GPT** works the same way: the bundles go in Knowledge, and the text above goes
in Instructions.

For one skill only, paste `skills/<name>.md` into the conversation and say "follow this".

## Grok

Paste the skill you want into the conversation, or put the router text above into custom
instructions with the bundle attached. Grok has no persistent file store in every
surface, so the single-skill files are usually the better unit there.

## Codex, Gemini CLI and other terminal agents

These read `AGENTS.md` from the working directory. Append the skills you want, or point
at them:

```bash
cat dist/portable/plugins/coding.md >> AGENTS.md
```

## Claude Code

You do not need any of this — install the plugins instead, which gives you automatic
triggering rather than a file the model has to be told to read. See the repository
README.

## Regenerating

```bash
make portable
```

Everything under `dist/` is generated and git-ignored. Do not edit these files; edit the
skill and export again.
"""


def export(root: Path, out: Path, check: bool = False) -> int:
    plugins = find_plugins(root)
    if not plugins:
        print(f"no plugins under {root}", file=sys.stderr)
        return 2

    rendered: dict[str, list[tuple[str, str, str]]] = {}
    failures = 0
    for plugin in plugins:
        for directory in find_skills(plugin / "skills"):
            try:
                name, description, document, unresolved = render_skill(directory)
            except (FrontmatterError, OSError, UnicodeDecodeError) as error:
                print(f"::error::{directory.name}: {error}", file=sys.stderr)
                failures += 1
                continue
            # Nothing may leave here still pointing at a file the reader cannot open.
            # This is the whole reason the export is checked rather than trusted: the
            # validator catches a dangling pointer in the repository, and this catches
            # one reintroduced by flattening.
            for relative in unresolved:
                print(f"::error::{name} still points at {relative} after export")
                failures += 1
            rendered.setdefault(plugin.name, []).append((name, description, document))
    if failures:
        return 1

    total = sum(len(s) for s in rendered.values())
    if check:
        print(f"export is clean: {total} skill(s) across {len(rendered)} plugin(s)")
        return 0

    if out.exists():
        shutil.rmtree(out)
    (out / "skills").mkdir(parents=True)
    (out / "plugins").mkdir(parents=True)
    (out / "README.md").write_text(HOW_TO_USE, encoding="utf-8")

    index = ["# Skill index", "", f"{total} procedures across {len(rendered)} groups.", ""]
    for plugin in sorted(rendered):
        index += [f"## {plugin}", ""]
        bundle = [f"# {plugin}", ""]
        for name, description, document in sorted(rendered[plugin]):
            (out / "skills" / f"{name}.md").write_text(document, encoding="utf-8")
            index.append(f"- **{name}** — {description}")
            # rstrip first: each document already ends in a newline, and joining without
            # trimming leaves the blank-line runs markdownlint reports on the bundle.
            bundle += [demote(document, 1).rstrip(), "", "---", ""]
        index.append("")
        (out / "plugins" / f"{plugin}.md").write_text("\n".join(bundle).rstrip() + "\n", "utf-8")
    (out / "index.md").write_text("\n".join(index).rstrip() + "\n", encoding="utf-8")

    print(f"exported {total} skill(s) and {len(rendered)} bundle(s) into {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="export_portable", description=__doc__.split("\n", 1)[0])
    parser.add_argument("root", nargs="?", default=".", type=Path, help="repository root")
    parser.add_argument("--out", type=Path, default=None, help="output directory")
    parser.add_argument(
        "--check", action="store_true", help="verify the export without writing anything"
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    return export(root, args.out or root / "dist" / "portable", args.check)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
