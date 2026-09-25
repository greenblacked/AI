#!/usr/bin/env python3
"""Export every skill as a self-contained Markdown file any assistant can read.

The skills in this repository are plain procedures. Nothing in them is specific to one
vendor — two files mention Claude at all, and both do it because the fact is about Claude
— but the *packaging* is: a `SKILL.md` with YAML frontmatter, sitting in a plugin with a
manifest, discovered by a marketplace. Chat assistants such as ChatGPT have no skill
loader and no marketplace to read, so the work does not travel there, and pasting a
`SKILL.md` into one of them hands the reader frontmatter it cannot use and `references/`
pointers it cannot open.

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

Output lands in `dist/portable/`: one file per skill, one per plugin, an index that lists
every description so a model can choose between them the way a skills runtime would, and
a `LICENSE` and `NOTICE` copied from the repository root so the release zip carries them
too. CI builds it on every run and uploads the result, so the files exist for someone
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
from skillcheck.rules import BUNDLED_PATH_RE, find_plugins, find_skills  # noqa: E402

# Reusing the validator's own pointer regex, rather than a narrower local copy, is the
# point: the local copy only matched a flat `references/<x>.md`, `assets/<x>.md` or
# `scripts/<x>.<ext>`, so a nested `references/deep/topic.md` or a non-Markdown
# `assets/checklist.txt` was neither inlined nor reported — `--check` said clean while
# the export still pointed at a file the reader could not open. `BUNDLED_PATH_RE` has no
# capturing group, so callers below match on ``match.group(0)``.
BUNDLED_RE = BUNDLED_PATH_RE
# How to fence a shipped script, by extension. Anything unlisted is fenced without a
# language rather than guessed at.
SCRIPT_LANGUAGES = {".sh": "bash", ".bash": "bash", ".py": "python", ".js": "javascript"}
# How to fence a shipped asset, by extension. Unlike a script, an asset with no
# recognised extension still gets a language rather than none: `text` says the block
# was checked rather than guessed at, and every asset used to be fenced as `markdown`
# regardless of its actual extension — a checklist.txt or a config.yaml labelled that
# way reads as a claim about its syntax that is simply wrong.
ASSET_LANGUAGES = {
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".txt": "text",
}
# Any fence opener, with its full run of markers: the closing fence has to use the same
# character and be at least as long, or a four-backtick block quoting a three-backtick
# example closes early and everything after it is read as prose.
FENCE_RE = re.compile(r"^(`{3,}|~{3,})")
ATX_RE = re.compile(r"^(#{1,6})(\s+)")


def _pointer(match: re.Match[str]) -> str:
    """The path a `BUNDLED_RE` match names, normalised to how it appears on disk.

    Unlike the old local regex, `BUNDLED_PATH_RE` has no capturing group excluding a
    leading `./`, so a mention written `./references/x.md` and one written
    `references/x.md` would otherwise become two different dictionary keys for the same
    file — one resolved by the directory walk, the other never matching it, and the
    file inlined or left dangling depending on which form the prose happened to use.

    No trailing-punctuation stripping happens here: `BUNDLED_PATH_RE`'s character class
    cannot end a match on a `.`, `,`, `;` or `:`, so a match is never left holding one —
    `references/x.md.` and `references/x.md,` both already match as `references/x.md`.
    """
    return match.group(0).removeprefix("./")


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


def asset_language_of(relative: str) -> str:
    """The fence language for a shipped asset, by extension, falling back to `text`.

    A script left unfenced when its extension is unknown is a judgement call an author
    can override by naming the extension in `SCRIPT_LANGUAGES`. An asset has no such
    author in the loop — it is whatever the reader's own project needs it to be — so it
    always gets a language, and `text` is the honest one when the extension names
    nothing more specific.
    """
    return ASSET_LANGUAGES.get(Path(relative).suffix, "text")


def drop_title(text: str) -> str:
    """A reference file's own H1, removed: the section heading already carries it, and
    keeping both renders as a title followed immediately by the same title again."""
    stripped = strip_frontmatter(text)
    if stripped.startswith("# "):
        return stripped.split("\n", 1)[1].lstrip("\n") if "\n" in stripped else ""
    return stripped


# The attribution MIT makes a condition of every copy. A flattened skill is the copy
# most likely to leave this repository — pasted into a project in another assistant, or
# a single file forwarded on — and until this line existed it left with no notice at
# all. It sits at the foot of every exported file, below the reference material, so a
# reader who scrolls to the end finds where the text came from and what they may do
# with it. MIT's actual condition is that the copyright notice and the licence text
# travel with the copy, not merely a line saying where it came from, so this names the
# copyright holder in full and points at the LICENSE this export ships alongside it
# rather than asking the reader to keep a sentence.
NOTICE = (
    "---\n"
    "Copyright (c) 2026 Serhii Zolotov (GitHub: greenblacked), "
    "https://github.com/greenblacked/AI. Licensed under the MIT License: the full text "
    "ships as LICENSE with this export and is at "
    "https://github.com/greenblacked/AI/blob/main/LICENSE. Keep the copyright notice "
    "and the licence with any copy."
)


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
            candidate = _pointer(match)
            tail = candidate.rsplit("/", 1)[-1]
            if "." not in tail:
                continue  # a directory mentioned generically, not a pointer to a file
            if candidate not in order:
                order.append(candidate)
                named.append(candidate)
    # Walked recursively and at any extension, matching what the validator itself
    # accepts as a pointer: a nested references/deep/topic.md or a non-Markdown
    # assets/checklist.txt is bundled the same as a flat references/x.md, rather than
    # silently passing through neither inlined nor reported.
    for sub in ("references", "assets", "scripts"):
        base = directory / sub
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
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
        if relative.startswith("references/"):
            titles[relative] = title_of(sources[relative], Path(relative).stem)
        else:
            # A script's or asset's title is the path to create, not its content — the
            # first "# " line of a shell script is a comment, not a heading, and using
            # it as the title silently mistitled the section with unrelated prose.
            titles[relative] = relative

    def rewrite(text: str) -> str:
        def one(match: re.Match[str]) -> str:
            candidate = _pointer(match)
            title = titles.get(candidate)
            return f'the "{title}" section below' if title else match.group(0)

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
            # Rewritten before the heading is attached: a reference's own body can name
            # a sibling pointer, but the heading must not be run through the same
            # rewrite — a script or asset title is now the path itself, and reusing this
            # branch for those would have that path rewritten into a self-referential
            # "the ... section below" the moment it fed back through `BUNDLED_RE`.
            content = rewrite(demote(drop_title(text), 3).strip())
            sections.append(f"### {title}\n\n{content}")
        else:
            # Fenced verbatim, so there is no prose inside to rewrite, and the heading
            # — the file's own path — must stay exactly as written for the same reason.
            language = (
                asset_language_of(relative)
                if relative.startswith("assets/")
                else (language_of(relative))
            )
            sections.append(f"### {title}\n\n```{language}\n{text.rstrip()}\n```")

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
    parts += ["", NOTICE]
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

Several of these now load skills natively and fire them on their own, which beats any
file here: the table in the repository README says which, and how to install for each —
<https://github.com/greenblacked/AI#chatgpt-grok-codex-and-everything-else>

For one that does not, most read `AGENTS.md` from the working directory. Append the
skills you want, or point at them:

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

## Licence

MIT. Copyright (c) 2026 Serhii Zolotov (GitHub: greenblacked),
https://github.com/greenblacked/AI. The full text is in the `LICENSE` file in this
directory and at <https://github.com/greenblacked/AI/blob/main/LICENSE>; `NOTICE` here
adds statements of fact that do not change its terms. Every skill file ends with a short
copy of the same notice — keep the copyright line and the `LICENSE` file with any copy
you make.
"""


EXPORT_SENTINEL = ".portable-export"
SENTINEL_TEXT = (
    "This directory was produced by scripts/export_portable.py, which checks for this "
    "file before deleting a directory in its own way. Delete it yourself if you no "
    "longer want the directory recognised as a previous export.\n"
)


def _looks_like_a_previous_export(out: Path) -> bool:
    """Whether ``out`` was, as best this script can tell, produced by this script.

    The sentinel is the primary signal: a one-line file whose content never changes, so
    it survives edits to ``HOW_TO_USE`` that would otherwise make every future export
    refuse to overwrite the one before it purely because the prose in its README had
    since been reworded. The README check is kept alongside it for a directory from
    before the sentinel existed.
    """
    if (out / EXPORT_SENTINEL).is_file():
        return True
    marker = out / "README.md"
    return marker.is_file() and marker.read_text(encoding="utf-8") == HOW_TO_USE


def _unsafe_to_remove(root: Path, out: Path) -> str | None:
    """Why ``out`` must not be handed to ``shutil.rmtree``, or ``None`` if it may be.

    ``--out .`` would otherwise delete the working tree: this is called only when ``out``
    already exists, right before it would be replaced, and the caller was never asked to
    confirm anything more specific than a path. Three things make a directory too
    dangerous to remove outright — being the repository, containing it, or being the
    directory a stray argument most plausibly resolves to when nobody meant one at all —
    and a fourth catches everything else: this export writes a recognisable marker on
    every successful run, so a directory that formed some other way is left alone rather
    than guessed at.
    """
    resolved_root = root.resolve()
    resolved_out = out.resolve()
    if resolved_out == Path.home().resolve():
        return "it is the home directory"
    if resolved_out == resolved_root or resolved_out in resolved_root.parents:
        return "it is the repository root or a directory that contains it"
    if not _looks_like_a_previous_export(resolved_out):
        return (
            f"it does not look like a previous export (no {EXPORT_SENTINEL} and no "
            "README.md matching this script's own marker text) — delete the directory "
            "yourself if you are sure"
        )
    return None


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

    # The export is the copy most likely to leave the repository, so it has to carry the
    # same LICENSE and NOTICE the repository ships rather than only the per-file footer
    # — checked before anything is deleted, so a repository missing either fails without
    # first destroying whatever was at `out`.
    for name in ("LICENSE", "NOTICE"):
        if not (root / name).is_file():
            print(f"::error::no {name} at the repository root ({root})", file=sys.stderr)
            return 2

    if out.exists():
        unsafe = _unsafe_to_remove(root, out)
        if unsafe is not None:
            print(f"refusing to delete {out}: {unsafe}", file=sys.stderr)
            return 2
        shutil.rmtree(out)
    (out / "skills").mkdir(parents=True)
    (out / "plugins").mkdir(parents=True)
    (out / "README.md").write_text(HOW_TO_USE, encoding="utf-8")
    (out / EXPORT_SENTINEL).write_text(SENTINEL_TEXT, encoding="utf-8")
    for name in ("LICENSE", "NOTICE"):
        shutil.copy(root / name, out / name)

    index = ["# Skill index", "", f"{total} procedures across {len(rendered)} groups.", ""]
    for plugin in sorted(rendered):
        index += [f"## {plugin}", ""]
        bodies = []
        for name, description, document in sorted(rendered[plugin]):
            (out / "skills" / f"{name}.md").write_text(document, encoding="utf-8")
            index.append(f"- **{name}** — {description}")
            # Every document ends with the notice. The bundle is one file, so it carries
            # the notice once, at its foot, rather than once per skill it concatenates.
            body = document[: document.rindex(NOTICE)]
            # rstrip first: joining untrimmed documents leaves the blank-line runs
            # markdownlint reports on the bundle.
            bodies.append(demote(body, 1).rstrip())
        index.append("")
        bundle = [f"# {plugin}", "", "\n\n---\n\n".join(bodies), "", NOTICE]
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
