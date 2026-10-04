#!/usr/bin/env python3
"""Build the static catalogue a Cloudflare Worker serves for one release.

The GitHub Release already attaches one ``.skill`` archive per skill and the portable
bundle. This writes the same two things, plus the marketplace manifest and a single
index, into a directory Wrangler can upload as static assets. It is a download of that
release, not a marketplace Claude Code can install from: the manifest's plugin sources
are paths inside the git repository, and they only resolve there.

The output directory is replaced only when it is already one of these builds. A path
that is the repository, contains it, or is the home directory is refused before
anything is deleted.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import export_portable  # noqa: E402
import package_skills  # noqa: E402

SOURCE_URL = "https://github.com/greenblacked/AI"
SENTINEL = ".catalogue-site"
SENTINEL_TEXT = (
    "This directory was produced by scripts/build_catalogue_site.py. "
    "The deploy deletes a previous build only when this file is present.\n"
)
# A version is a label written into the page and into version.txt. It is never a path.
VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,79}$")


def normalise_version(raw: str) -> str:
    """The version label, or exit. Rejects anything that is not a single token."""
    version = raw.strip()
    if VERSION_RE.fullmatch(version) is None:
        raise SystemExit(
            f"refusing version {raw!r}: use a token such as v1.2.3, pr-abcdef0 or main-abcdef0"
        )
    return version


def unsafe_output(root: Path, output: Path) -> str | None:
    """Why ``output`` must not be replaced, or ``None`` when it may be."""
    resolved_root = root.resolve()
    resolved_out = output.resolve()
    if resolved_out == Path.home().resolve():
        return "it is the home directory"
    if resolved_out == resolved_root or resolved_out in resolved_root.parents:
        return "it is the repository root or a directory that contains it"
    if resolved_out.exists() and not (resolved_out / SENTINEL).is_file():
        return "it is not a previous catalogue site (no .catalogue-site)"
    return None


def _manifest(root: Path) -> dict:
    path = root / ".claude-plugin" / "marketplace.json"
    if not path.is_file():
        raise SystemExit(f"no marketplace manifest at {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"{path} is not JSON: {error}") from error
    if not isinstance(data, dict) or not isinstance(data.get("name"), str) or not data["name"]:
        raise SystemExit(f"{path} has no string name")
    return data


def _ordered_groups(manifest: dict, grouped: dict[str, list[str]]) -> list[tuple[str, list[str]]]:
    """Marketplace order first, then any plugin the manifest does not name."""
    named: list[str] = []
    plugins = manifest.get("plugins")
    if isinstance(plugins, list):
        for plugin in plugins:
            if isinstance(plugin, dict) and isinstance(plugin.get("name"), str):
                named.append(plugin["name"])
    order = [name for name in named if name in grouped]
    order += sorted(set(grouped) - set(order))
    return [(name, sorted(grouped[name])) for name in order]


def _page(title: str, body: str) -> str:
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title)}</title>\n"
        "<style>\n"
        "body{font:18px/1.5 Georgia,serif;max-width:42rem;margin:2rem auto;padding:0 1rem;"
        "color:#1c1915;background:#f7f4ee}\n"
        "a{color:#0b3d4a} h1{font-weight:normal;letter-spacing:-0.02em}\n"
        "code{font-family:ui-monospace,monospace;font-size:0.9em}\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        f"{body}\n"
        "</body>\n"
        "</html>\n"
    )


def render_index(manifest: dict, groups: list[tuple[str, list[str]]], version: str) -> str:
    """The one page. Every value taken from the repository is escaped."""
    name = html.escape(manifest["name"])
    description = manifest.get("description")
    intro = ""
    if isinstance(description, str) and description.strip():
        intro = f"<p>{html.escape(description.strip())}</p>\n"
    sections = []
    for plugin, skills in groups:
        items = "\n".join(
            '<li><a href="skills/{href}">{label}</a></li>'.format(
                href=html.escape(skill, quote=True),
                label=html.escape(skill.removesuffix(".skill")),
            )
            for skill in skills
        )
        sections.append(f"<h2>{html.escape(plugin)}</h2>\n<ul>\n{items}\n</ul>")
    body = (
        f"<h1>{name}</h1>\n"
        f"<p>Release <code>{html.escape(version)}</code>.</p>\n"
        f"{intro}"
        "<p>Install from the git repository. This page is the download of that release: "
        "one <code>.skill</code> archive per skill, and the portable bundle. "
        "The manifest's plugin sources are paths in the repository, so this copy is not "
        "itself something to add as a marketplace.</p>\n"
        "<p>"
        f'<a href="{html.escape(SOURCE_URL, quote=True)}">Source</a>'
        " · "
        f'<a href="{html.escape(SOURCE_URL, quote=True)}/releases">Releases</a>'
        ' · <a href="portable-skills.zip">Portable bundle</a>'
        ' · <a href="marketplace.json">Marketplace manifest</a>'
        "</p>\n" + "\n".join(sections)
    )
    return _page(f"{manifest['name']} {version}", body)


def _robots(noindex: bool) -> str:
    if noindex:
        return "User-agent: *\nDisallow: /\n"
    return "User-agent: *\nAllow: /\n"


def _write_archives(root: Path, skills_dir: Path) -> dict[str, list[str]]:
    skills = package_skills.find_skills(root)
    if not skills:
        raise SystemExit(f"no skills under {root}")
    grouped: dict[str, list[str]] = {}
    for skill in skills:
        archive = package_skills.package(skill, skills_dir, root)
        grouped.setdefault(skill.parent.parent.name, []).append(archive.name)
    return grouped


def _write_portable(root: Path, output: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="catalogue-portable-") as tmp:
        exported = Path(tmp) / "portable"
        code = export_portable.export(root, exported)
        if code != 0:
            raise SystemExit(f"portable export failed ({code})")
        with zipfile.ZipFile(output / "portable-skills.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in sorted(exported.rglob("*")):
                if path.is_file():
                    bundle.write(path, path.relative_to(exported).as_posix())


def build(root: Path, output: Path, version: str, *, noindex: bool = False) -> None:
    """Replace ``output`` with the site for ``version``."""
    version = normalise_version(version)
    manifest = _manifest(root)
    reason = unsafe_output(root, output)
    if reason is not None:
        raise SystemExit(f"refusing to write {output}: {reason}")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    (output / SENTINEL).write_text(SENTINEL_TEXT, encoding="utf-8")
    # Wrangler reads this and does not upload the sentinel. A dotfile with no other
    # purpose should not be part of the site a visitor can fetch.
    (output / ".assetsignore").write_text(f"{SENTINEL}\n", encoding="utf-8")
    skills_dir = output / "skills"
    skills_dir.mkdir()
    grouped = _write_archives(root, skills_dir)
    _write_portable(root, output)
    (output / "marketplace.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (output / "version.txt").write_text(version + "\n", encoding="utf-8")
    (output / "robots.txt").write_text(_robots(noindex), encoding="utf-8")
    groups = _ordered_groups(manifest, grouped)
    (output / "index.html").write_text(render_index(manifest, groups, version), encoding="utf-8")
    (output / "404.html").write_text(
        _page(
            "Not found",
            '<h1>Not found</h1>\n<p><a href="/">Back to the catalogue</a></p>',
        ),
        encoding="utf-8",
    )
    print(f"built {output} for {version}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="build_catalogue_site", description=__doc__.split("\n", 1)[0]
    )
    parser.add_argument(
        "--version", required=True, help="label written into the page and version.txt"
    )
    parser.add_argument(
        "--out", type=Path, default=None, help="output directory (default: dist/site)"
    )
    parser.add_argument(
        "--noindex", action="store_true", help="tell crawlers not to index this build"
    )
    parser.add_argument("root", nargs="?", default=".", type=Path, help="repository root")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    output = args.out if args.out is not None else root / "dist" / "site"
    build(root, output, args.version, noindex=args.noindex)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
