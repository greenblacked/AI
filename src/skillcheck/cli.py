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

from .rules import (
    WARNING,
    Finding,
    check_agent,
    check_duplicate_names,
    check_marketplace,
    check_skill,
    find_agents,
    find_plugins,
    find_skills,
)


def _annotate(finding: Finding) -> str:
    level = "error" if finding.failed else "warning"
    return (
        f"::{level} file={finding.path},line={finding.line},title={finding.code}::{finding.message}"
    )


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

    findings: list[Finding] = []
    for skill in skills:
        findings.extend(check_skill(skill, root))
    findings.extend(check_duplicate_names(skills, root))
    agents = [agent for plugin in plugins for agent in find_agents(plugin / "agents")]
    agents += find_agents(root / "agents")
    for agent in agents:
        findings.extend(check_agent(agent, root))
    if not args.skip_marketplace:
        findings.extend(check_marketplace(root))

    github = args.github or os.environ.get("GITHUB_ACTIONS") == "true"

    errors = [item for item in findings if item.failed]
    warnings = [item for item in findings if item.level == WARNING]

    for item in sorted(findings, key=lambda f: (not f.failed, str(f.path), f.line)):
        label = "ERROR  " if item.failed else "warning"
        print(f"{label} {item.path}:{item.line} [{item.code}] {item.message}")
        if github:
            print(_annotate(item))

    print(
        f"\n{len(plugins)} plugin(s), {len(skills)} skill(s) and {len(agents)} "
        f"subagent(s) checked — {len(errors)} error(s), {len(warnings)} warning(s)"
    )

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
