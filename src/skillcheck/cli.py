"""Command-line entry point: validate every skill in the repository.

Output is deliberately dual. Humans get a readable report on stdout; GitHub gets
``::error file=…,line=…`` annotations so failures land on the right line of the pull
request diff, plus a Markdown table in the job summary so the run overview says which
skills were checked rather than only which ones broke.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .frontmatter import FrontmatterError, parse
from .rules import (
    WARNING,
    Finding,
    check_agent,
    check_agent_evals,
    check_command,
    check_duplicate_names,
    check_eval_conflicts,
    check_marketplace,
    check_skill,
    find_agents,
    find_commands,
    find_plugins,
    find_skills,
)


def _annotate(finding: Finding) -> str:
    level = "error" if finding.failed else "warning"
    return (
        f"::{level} file={finding.path},line={finding.line},title={finding.code}::{finding.message}"
    )


def _listing_sizes(plugins: list[Path], skills: list[Path]) -> dict[Path, int]:
    """Characters of description each plugin puts into the skill listing."""
    sizes: dict[Path, int] = {plugin: 0 for plugin in plugins}
    for skill in skills:
        try:
            description = parse((skill / "SKILL.md").read_text(encoding="utf-8")).get(
                "description", ""
            )
        except (OSError, FrontmatterError, UnicodeDecodeError):
            continue  # check_skill has already reported it
        for plugin in plugins:
            if skill.is_relative_to(plugin):
                sizes[plugin] += len(" ".join((description or "").split()))
                break
    return sizes


def _summary(skills: list[Path], findings: list[Finding], root: Path) -> str:
    # Group by the skill directory that contains the finding, not by trimming a
    # "/SKILL.md" suffix: an eval-set finding is reported against
    # `<skill>/evals/trigger-eval.json`, and matching on the suffix silently dropped it,
    # so a skill whose only defect was its eval set rendered as a green tick while the
    # build failed.
    keys = sorted((str(skill.relative_to(root)) for skill in skills), key=len, reverse=True)
    by_skill: dict[str, list[Finding]] = {}
    for finding in findings:
        path = str(finding.path)
        match = next((key for key in keys if path == key or path.startswith(key + "/")), None)
        if match is not None:
            by_skill.setdefault(match, []).append(finding)

    rows = ["| Skill | Result |", "| --- | --- |"]
    for skill in skills:
        key = str(skill.relative_to(root))
        related = by_skill.get(key, [])
        errors = sum(1 for item in related if item.failed)
        warnings = len(related) - errors
        if errors:
            state = f"❌ {errors} error(s)" + (f", {warnings} warning(s)" if warnings else "")
        elif warnings:
            state = f"⚠️ {warnings} warning(s)"
        else:
            state = "✅"
        rows.append(f"| `{key}` | {state} |")

    lines = [f"### Skill validation — {len(skills)} skill(s)", "", *rows]
    detail = [item for item in findings if item.failed or item.level == WARNING]
    if detail:
        lines += ["", "<details><summary>Findings</summary>", ""]
        for item in sorted(detail, key=lambda f: (not f.failed, str(f.path), f.line)):
            mark = "**error**" if item.failed else "warning"
            lines.append(f"- {mark} `{item.path}:{item.line}` `{item.code}` — {item.message}")
        lines += ["", "</details>"]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="skillcheck", description="Validate the skills in this repository."
    )
    parser.add_argument(
        "root", nargs="?", default=".", type=Path, help="repository root (default: .)"
    )
    parser.add_argument(
        "--github",
        action="store_true",
        help="emit GitHub annotations and a job summary (implied when GITHUB_ACTIONS is set)",
    )
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    parser.add_argument(
        "--listing-budget",
        type=int,
        default=None,
        metavar="CHARS",
        help="warn when a plugin's descriptions together exceed this many characters; "
        "Claude Code's default listing budget is about 1%% of the context window, "
        "roughly 8000 for a 200k model",
    )
    parser.add_argument(
        "--skip-marketplace",
        action="store_true",
        help="skip the marketplace cross-check (useful before the manifest exists)",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    plugins = find_plugins(root)
    # Search the whole tree rather than one directory: a skill that has escaped its
    # plugin still has to be found, so that check_marketplace can report it as unowned
    # rather than the run quietly not seeing it.
    skills = find_skills(root)
    if not skills:
        print(f"no SKILL.md found under {root}", file=sys.stderr)
        return 2

    agents = [agent for plugin in plugins for agent in find_agents(plugin / "agents")]
    agents += find_agents(root / "agents")
    # Every name an eval set may point at with `expected`. A misspelling there is a
    # permanent miss, so it is checked against what actually exists.
    known = frozenset(d.name for d in skills) | frozenset(a.stem for a in agents)

    findings: list[Finding] = []
    for skill in skills:
        findings.extend(check_skill(skill, root, known))
    findings.extend(check_duplicate_names(skills, root))
    findings.extend(check_eval_conflicts(skills, root, agents))
    for agent in agents:
        findings.extend(check_agent(agent, root))
        findings.extend(check_agent_evals(agent, root, known))
    # Commands ship two ways: inside a plugin, and in the repository's own
    # `.claude/commands/`, which is where a contributor-facing command belongs.
    commands = [command for plugin in plugins for command in find_commands(plugin / "commands")]
    commands += find_commands(root / ".claude" / "commands")
    for command in commands:
        findings.extend(check_command(command, root))
    if not args.skip_marketplace:
        findings.extend(check_marketplace(root))
    listing = _listing_sizes(plugins, skills)
    if args.listing_budget is not None:
        for plugin, size in listing.items():
            if size > args.listing_budget:
                findings.append(
                    Finding(
                        WARNING,
                        plugin.relative_to(root) / ".claude-plugin" / "plugin.json",
                        1,
                        "listing-over-budget",
                        f"this plugin's skill descriptions total {size:,} characters "
                        f"against a listing budget of {args.listing_budget:,}; the runtime "
                        "drops descriptions of the least-used skills when the listing "
                        "overflows, so they can no longer fire on their own",
                    )
                )

    github = args.github or os.environ.get("GITHUB_ACTIONS") == "true"

    errors = [item for item in findings if item.failed]
    warnings = [item for item in findings if item.level == WARNING]

    for item in sorted(findings, key=lambda f: (not f.failed, str(f.path), f.line)):
        label = "ERROR  " if item.failed else "warning"
        print(f"{label} {item.path}:{item.line} [{item.code}] {item.message}")
        if github:
            print(_annotate(item))

    print(
        f"\n{len(plugins)} plugin(s), {len(skills)} skill(s), {len(agents)} subagent(s) "
        f"and {len(commands)} command(s) checked — {len(errors)} error(s), "
        f"{len(warnings)} warning(s)"
    )
    # Always reported, never a finding on its own: the number is the point. Every
    # description a plugin ships is resident in context for the whole session, and the
    # runtime's listing budget is roughly 1% of the context window.
    total = sum(listing.values())
    per_plugin = ", ".join(f"{p.name} {n:,}" for p, n in listing.items())
    print(f"description characters in the listing: {total:,} ({per_plugin})")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if github and summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(_summary(skills, findings, root))

    if errors:
        return 1
    if warnings and args.strict:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
